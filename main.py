"""YouTube Video Summarizer CLI application."""

import argparse
import logging
import sys

from yt_summary.cache import is_legacy_filename, load_cache, save_to_cache
from yt_summary.config import (
    get_transcript_language,
    load_config,
)
from yt_summary.logging import setup_logging
from yt_summary.metadata import MetadataError, fetch_video_metadata
from yt_summary.playlist import PlaylistError, fetch_playlist_info
from yt_summary.transcript import TranscriptError, fetch_transcript
from yt_summary.youtube_utils import (
    extract_video_id,
    is_playlist_id,
    is_playlist_url,
    is_video_id,
)

logger = logging.getLogger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Fetch and cache YouTube transcripts")
    parser.add_argument("url_or_id", help="YouTube video URL or video ID")
    parser.add_argument("--lang", help="Transcript language code (default: from config)")
    return parser.parse_args(args)


def print_error(message: str) -> None:
    """Log error message."""
    logger.error(message)


def summarize_video(url_or_id: str, lang: str | None) -> int:
    """Fetch and cache the transcript for a YouTube video.

    Args:
        url_or_id: YouTube URL or video ID
        lang: Transcript language code (None = use config default)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Resolve video ID from URL or bare ID
    if is_video_id(url_or_id):
        video_id = url_or_id
    else:
        video_id = extract_video_id(url_or_id)
        if not video_id:
            print_error("Invalid YouTube URL or video ID: %s" % url_or_id)
            return 1

    lang_code = lang or get_transcript_language()

    try:
        # Check cache
        cached = load_cache(video_id)
        full_text = cached.get("full_text") if cached else None
        cached_title = cached.get("title") if cached else None
        cached_channel = cached.get("channel") if cached else None

        title = cached_title
        channel = cached_channel
        needs_metadata = (not title or not channel) and not full_text
        needs_reorganize = cached and is_legacy_filename(video_id)

        if needs_metadata or needs_reorganize:
            try:
                metadata = fetch_video_metadata(video_id)
                title = metadata["title"]
                channel = metadata["channel"]
                logger.info("Fetched video metadata: %s by %s", title, channel or "Unknown")
                if cached and is_legacy_filename(video_id):
                    save_to_cache(
                        video_id,
                        full_text or "",
                        cached.get("summary", "") if cached else "",
                        title=title,
                        channel=channel,
                    )
                    logger.info("Reorganized cache file with channel subdirectory")
            except MetadataError as e:
                logger.warning(e.message)
                title = cached_title or ""
                channel = cached_channel or ""

        if full_text:
            logger.info("Transcript already cached for %s", video_id)
        else:
            full_text = fetch_transcript(video_id, language_code=lang_code)
            save_to_cache(video_id, full_text, "", title=title, channel=channel)
            logger.info("Fetched and cached transcript for %s", video_id)

        print("Transcript cached. Use the yt-summary skill to summarize.")
        return 0

    except TranscriptError as e:
        print_error(str(e))
        return 1
    except Exception as e:
        print_error(f"{type(e).__name__}: {e}")
        return 1


def process_playlist(url_or_id: str, lang: str | None) -> int:
    """Fetch and cache transcripts for all videos in a YouTube playlist.

    Args:
        url_or_id: YouTube playlist URL or playlist ID
        lang: Transcript language code (None = use config default)

    Returns:
        Exit code (0 if at least one video succeeded, 1 if all failed)
    """
    try:
        playlist_info = fetch_playlist_info(url_or_id)
    except PlaylistError as e:
        print_error(str(e))
        return 1

    logger.info(
        "Playlist: %s (%d videos)", playlist_info.playlist_title, len(playlist_info.video_ids)
    )

    if not playlist_info.video_ids:
        print_error("Playlist is empty")
        return 1

    lang_code = lang or get_transcript_language()
    succeeded = 0
    failed = 0

    for i, video_id in enumerate(playlist_info.video_ids, 1):
        logger.info("[%d/%d] Processing %s", i, len(playlist_info.video_ids), video_id)

        try:
            # Check cache
            cached = load_cache(video_id)
            if cached and cached.get("full_text"):
                logger.info("  Already cached, skipping")
                succeeded += 1
                continue

            # Fetch metadata
            try:
                metadata = fetch_video_metadata(video_id)
                title = metadata["title"]
                channel = metadata["channel"]
            except MetadataError as e:
                logger.warning("  %s", e.message)
                title = ""
                channel = ""

            # Fetch transcript
            full_text = fetch_transcript(video_id, language_code=lang_code)

            # Save to cache with playlist metadata
            save_to_cache(
                video_id,
                full_text,
                "",
                title=title,
                channel=channel,
                playlist_id=playlist_info.playlist_id,
                playlist_title=playlist_info.playlist_title,
            )
            logger.info("  Cached transcript for %s", title or video_id)
            succeeded += 1

        except TranscriptError as e:
            logger.warning("  Failed: %s", str(e))
            failed += 1
        except Exception as e:
            logger.warning("  Failed: %s: %s", type(e).__name__, e)
            failed += 1

    logger.info("Playlist complete: %d succeeded, %d failed", succeeded, failed)

    if succeeded > 0:
        print(f"Playlist cached ({succeeded} videos). Use the yt-summary skill to summarize.")
        return 0
    else:
        print_error("All videos in the playlist failed")
        return 1


def main() -> int:
    """Run the YouTube video summarizer CLI."""
    setup_logging()
    load_config()
    args = parse_args()

    # Detect playlist input
    if is_playlist_url(args.url_or_id) or is_playlist_id(args.url_or_id):
        return process_playlist(args.url_or_id, args.lang)

    return summarize_video(args.url_or_id, args.lang)


if __name__ == "__main__":
    sys.exit(main())
