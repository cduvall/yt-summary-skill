"""Transcript fetching and processing from YouTube videos."""

import html
import logging
import os
import re
import time
import urllib.request

import yt_dlp

logger = logging.getLogger(__name__)


class TranscriptError(Exception):
    """Exception raised when transcript cannot be fetched."""

    def __init__(self, message: str, video_id: str = "") -> None:
        """Initialize TranscriptError with optional video ID."""
        self.message = message
        self.video_id = video_id
        super().__init__(message)


class _PermanentError(Exception):
    """Internal exception for non-retryable errors."""

    pass


_MAX_RETRIES = 3
_BASE_DELAY = 2.0


def _parse_webvtt(content: str) -> str:
    """
    Parse WebVTT subtitle content to plain text.

    Strips WEBVTT header, timestamps, sequence numbers, HTML tags,
    and deduplicates consecutive identical lines.

    Args:
        content: Raw WebVTT content

    Returns:
        Plain text transcript
    """
    lines = content.splitlines()
    text_lines = []

    # Skip WEBVTT header and metadata
    in_cue = False
    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip WEBVTT header
        if line.startswith("WEBVTT"):
            continue

        # Skip timestamp lines (e.g., "00:00:00.000 --> 00:00:02.000")
        if re.match(r"\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+", line):
            in_cue = True
            continue

        # Skip sequence numbers (pure digits)
        if line.isdigit():
            continue

        # Skip cue settings (lines starting with NOTE, STYLE, etc.)
        if line.startswith(("NOTE", "STYLE", "REGION")):
            continue

        # This is actual subtitle text
        if in_cue:
            # Strip HTML/WebVTT tags
            text = re.sub(r"<[^>]+>", "", line)
            # HTML unescape entities
            text = html.unescape(text)
            text = text.strip()
            if text:
                text_lines.append(text)

    # Deduplicate consecutive identical lines (common in auto-captions)
    deduplicated = []
    for line in text_lines:
        if not deduplicated or deduplicated[-1] != line:
            deduplicated.append(line)

    return "\n".join(deduplicated)


def _find_subtitle_url(subs_dict: dict, language_code: str) -> str | None:
    """
    Find VTT subtitle URL for a specific language.

    Args:
        subs_dict: Dictionary of subtitle entries (from yt-dlp)
        language_code: Language code to search for (e.g., 'en')

    Returns:
        VTT subtitle URL, or None if not found
    """
    if language_code not in subs_dict:
        return None

    formats = subs_dict[language_code]
    for fmt in formats:
        if fmt.get("ext") == "vtt":
            return fmt.get("url")

    return None


def _find_any_subtitle_url(subs_dict: dict) -> str | None:
    """
    Find any available VTT subtitle URL (first match).

    Args:
        subs_dict: Dictionary of subtitle entries (from yt-dlp)

    Returns:
        VTT subtitle URL, or None if none found
    """
    for formats in subs_dict.values():
        for fmt in formats:
            if fmt.get("ext") == "vtt":
                return fmt.get("url")

    return None


def _extract_subtitles(url: str, video_id: str, language_code: str) -> str:
    """
    Extract and parse subtitles using yt-dlp.

    Priority: manual subs in preferred language > auto-captions in preferred language
              > any manual > any auto

    Args:
        url: YouTube video URL
        video_id: Video ID (for error messages)
        language_code: Preferred language code (e.g., 'en')

    Returns:
        Parsed plain text transcript

    Raises:
        _PermanentError: If no subtitles are available at all
        yt_dlp.utils.DownloadError: For other yt-dlp failures
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "format": "best",
        "ignore_no_formats_error": True,
    }

    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies_file and os.path.isfile(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
        logger.debug(
            "Using cookies file: %s (%d bytes)", cookies_file, os.path.getsize(cookies_file)
        )
    else:
        logger.debug("No cookies file (YOUTUBE_COOKIES_FILE=%r)", cookies_file)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    manual_subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}
    logger.debug(
        "Subtitles for %s: manual=%s, auto=%s",
        video_id,
        list(manual_subs.keys()),
        list(auto_subs.keys())[:5],
    )

    # Priority 1: Manual subs in preferred language
    vtt_url = _find_subtitle_url(manual_subs, language_code)

    # Priority 2: Auto-captions in preferred language
    if not vtt_url:
        vtt_url = _find_subtitle_url(auto_subs, language_code)

    # Priority 3: Any manual subtitle
    if not vtt_url:
        vtt_url = _find_any_subtitle_url(manual_subs)

    # Priority 4: Any auto-caption
    if not vtt_url:
        vtt_url = _find_any_subtitle_url(auto_subs)

    if not vtt_url:
        raise _PermanentError("No subtitles found for video %s" % video_id)

    # Fetch VTT content
    with urllib.request.urlopen(vtt_url) as response:
        vtt_content = response.read().decode("utf-8")

    return _parse_webvtt(vtt_content)


def _is_permanent_error(e: Exception) -> bool:
    """
    Classify whether an error is permanent (non-retryable).

    Args:
        e: Exception raised during transcript fetch

    Returns:
        True if error is permanent, False if transient
    """
    if isinstance(e, _PermanentError):
        return True

    if isinstance(e, yt_dlp.utils.DownloadError):
        error_msg = str(e).lower()
        permanent_patterns = [
            "video unavailable",
            "private video",
            "sign in to confirm your age",
            "this video is not available",
            "this video has been removed",
        ]
        return any(pattern in error_msg for pattern in permanent_patterns)

    return False


def _fetch_with_retry(video_id: str, language_code: str) -> str:
    """
    Fetch transcript with retry logic for transient errors.

    Args:
        video_id: YouTube video ID
        language_code: Language code (e.g., 'en')

    Returns:
        Transcript text

    Raises:
        Permanent errors immediately (no retry)
        Transient errors after max retries exhausted
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    for attempt in range(_MAX_RETRIES):
        try:
            return _extract_subtitles(url, video_id, language_code)
        except Exception as e:
            if _is_permanent_error(e):
                raise

            if attempt < _MAX_RETRIES - 1:
                delay = _BASE_DELAY * (2**attempt)
                logger.warning(
                    "Retry %d/%d: %s for %s, retrying in %.0fs...",
                    attempt + 1,
                    _MAX_RETRIES - 1,
                    type(e).__name__,
                    video_id,
                    delay,
                )
                time.sleep(delay)
            else:
                raise

    # Unreachable, but makes type checker happy
    raise RuntimeError("Retry logic exhausted")


def _error_message(e: Exception) -> str:
    """
    Map exception types to user-friendly error messages.

    Args:
        e: Exception raised during transcript fetch

    Returns:
        User-friendly error message string
    """
    if isinstance(e, _PermanentError):
        return "No subtitles available for this video"

    if isinstance(e, yt_dlp.utils.DownloadError):
        error_msg = str(e).lower()
        if "video unavailable" in error_msg or "not available" in error_msg:
            return "The video is no longer available"
        elif "private video" in error_msg:
            return "The video is private"
        elif "sign in to confirm your age" in error_msg or "age" in error_msg:
            return "The video is age-restricted"
        elif "429" in error_msg or "rate" in error_msg:
            return "YouTube is rate limiting requests"
        else:
            return f"Failed to download video info: {str(e)}"

    return f"{type(e).__name__}: {str(e)}"


def fetch_transcript(video_id: str, language_code: str = "en") -> str:
    """
    Fetch transcript for a YouTube video.

    Args:
        video_id: YouTube video ID
        language_code: Language code (e.g., 'en' for English)

    Returns:
        Transcript text as a single string

    Raises:
        TranscriptError: If no transcript is available
    """
    try:
        full_text = _fetch_with_retry(video_id, language_code)
    except Exception as e:
        raise TranscriptError(
            f"Could not fetch transcript for video {video_id}. {_error_message(e)}",
            video_id=video_id,
        ) from e

    if not full_text.strip():
        raise TranscriptError(f"Transcript for video {video_id} is empty", video_id=video_id)

    return full_text
