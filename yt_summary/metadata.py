"""Fetch YouTube video metadata (title, etc.) without API key."""

import os
import re

import yt_dlp


class MetadataError(Exception):
    """Exception raised when metadata cannot be fetched."""

    def __init__(self, message: str, video_id: str = "") -> None:
        """Initialize MetadataError with optional video ID."""
        self.message = message
        self.video_id = video_id
        super().__init__(message)


def sanitize_filename(title: str) -> str:
    """
    Sanitize video title for use in filename.

    Removes or replaces characters that are invalid in filenames.

    Args:
        title: Raw video title

    Returns:
        Sanitized title safe for filenames
    """
    # Replace invalid filename characters with space
    sanitized = re.sub(r'[<>:"/\\|?*]', " ", title)
    # Replace multiple spaces with single space
    sanitized = re.sub(r"\s+", " ", sanitized)
    # Trim whitespace and limit length
    sanitized = sanitized.strip()[:200]
    return sanitized


def fetch_video_metadata(video_id: str) -> dict[str, str]:
    """
    Fetch metadata for a YouTube video using yt-dlp.

    Args:
        video_id: YouTube video ID

    Returns:
        Dictionary with 'title' and 'channel' keys (both sanitized for filenames)

    Raises:
        MetadataError: If metadata cannot be fetched
    """
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Configure yt-dlp to only fetch metadata, no download
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "format": "best",
            "ignore_no_formats_error": True,
        }

        cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
        if cookies_file and os.path.isfile(cookies_file):
            ydl_opts["cookiefile"] = cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title")
            # Try multiple fields for channel name
            channel = info.get("uploader") or info.get("channel") or info.get("uploader_id") or ""

        if not title:
            raise MetadataError(f"Could not fetch title for video {video_id}", video_id=video_id)

        return {
            "title": sanitize_filename(title),
            "channel": sanitize_filename(channel) if channel else "",
        }
    except Exception as e:
        raise MetadataError(
            f"Could not fetch metadata for video {video_id}: {str(e)}", video_id=video_id
        ) from e
