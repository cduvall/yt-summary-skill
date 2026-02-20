"""YouTube Video Summarizer CLI application."""

import argparse
import logging
import sys

from yt_summary.cache import is_legacy_filename, load_cache, save_to_cache
from yt_summary.config import (
    get_subscription_exclude_channels,
    get_subscription_exclude_keywords,
    get_subscription_include_keywords,
    get_transcript_language,
    load_config,
)
from yt_summary.logging import setup_logging
from yt_summary.metadata import MetadataError, fetch_video_metadata
from yt_summary.subscriptions import run_subscriptions
from yt_summary.transcript import TranscriptError, fetch_transcript
from yt_summary.youtube_utils import extract_video_id, is_video_id

logger = logging.getLogger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments with subparser support and backward compatibility."""
    # Backward compatibility check: if first arg isn't a known subcommand, treat as summarize
    argv = list(sys.argv[1:]) if args is None else list(args)
    if argv and argv[0] not in ["summarize", "subscriptions", "-h", "--help"]:
        # Insert 'summarize' subcommand for backward compatibility
        argv.insert(0, "summarize")

    parser = argparse.ArgumentParser(description="Fetch and cache YouTube transcripts")

    subparsers = parser.add_subparsers(dest="command", help="Command to run", required=True)

    # Summarize subcommand
    summarize_parser = subparsers.add_parser(
        "summarize", help="Fetch and cache a YouTube transcript"
    )
    summarize_parser.add_argument("url_or_id", help="YouTube video URL or video ID")
    summarize_parser.add_argument("--lang", help="Transcript language code (default: from config)")

    # Subscriptions subcommand
    subscriptions_parser = subparsers.add_parser(
        "subscriptions", help="Process recent videos from YouTube subscriptions"
    )
    subscriptions_parser.add_argument(
        "--days", type=int, default=7, help="Fetch videos from last N days (default: 7)"
    )
    subscriptions_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview filtered videos without processing",
    )
    subscriptions_parser.add_argument(
        "--include-keywords", help="Comma-separated keyword inclusion list"
    )
    subscriptions_parser.add_argument(
        "--exclude-keywords", help="Comma-separated keyword exclusion list"
    )
    subscriptions_parser.add_argument(
        "--exclude-channels", help="Comma-separated channel names to exclude"
    )
    subscriptions_parser.add_argument(
        "--max-videos",
        type=int,
        default=50,
        help="Maximum number of videos to process (default: 50)",
    )
    subscriptions_parser.add_argument(
        "--lang", help="Transcript language code (default: from config)"
    )

    return parser.parse_args(argv)


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


def main() -> int:
    """Run the YouTube video summarizer CLI."""
    setup_logging()
    load_config()
    args = parse_args()

    # Route to appropriate subcommand
    if args.command == "summarize":
        return summarize_video(args.url_or_id, args.lang)

    elif args.command == "subscriptions":
        # Parse keyword lists from CLI or fall back to config
        if args.include_keywords:
            include_keywords = [k.strip() for k in args.include_keywords.split(",")]
        else:
            include_keywords = get_subscription_include_keywords()

        if args.exclude_keywords:
            exclude_keywords = [k.strip() for k in args.exclude_keywords.split(",")]
        else:
            exclude_keywords = get_subscription_exclude_keywords()

        if args.exclude_channels:
            exclude_channels = [c.strip() for c in args.exclude_channels.split(",")]
        else:
            exclude_channels = get_subscription_exclude_channels()

        lang = args.lang or get_transcript_language()

        return run_subscriptions(
            days=args.days,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
            exclude_channels=exclude_channels,
            lang=lang,
            dry_run=args.dry_run,
            max_videos=args.max_videos,
        )

    else:
        print_error("Unknown command: %s" % args.command)
        return 1


if __name__ == "__main__":
    sys.exit(main())
