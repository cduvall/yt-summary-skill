"""Batch processing of YouTube subscription videos."""

import logging
from datetime import datetime, timedelta, timezone

from yt_summary.cache import load_cache, save_to_cache
from yt_summary.config import get_oauth_dir
from yt_summary.filter import keyword_filter
from yt_summary.transcript import TranscriptError, fetch_transcript
from yt_summary.youtube_api import (
    YouTubeAPIError,
    get_credentials,
    get_recent_videos,
    get_subscribed_channels,
    get_video_durations,
)

logger = logging.getLogger(__name__)


def run_subscriptions(
    days: int,
    include_keywords: list[str],
    exclude_keywords: list[str],
    lang: str,
    dry_run: bool,
    max_videos: int,
    *,
    exclude_channels: list[str] | None = None,
) -> int:
    """
    Run batch subscription processing workflow.

    Args:
        days: Fetch videos from last N days
        include_keywords: Keyword inclusion filter list
        exclude_keywords: Keyword exclusion filter list
        lang: Transcript language code
        dry_run: If True, only print filtered videos without processing
        max_videos: Maximum number of videos to process (safety cap)
        exclude_channels: Channel names to exclude from processing

    Returns:
        Exit code (0 for success, 1 for error)
    """
    exclude_channels = exclude_channels or []
    try:
        # Step 1: Get OAuth credentials
        logger.info("Authenticating with YouTube...")
        oauth_dir = get_oauth_dir()
        credentials = get_credentials(oauth_dir)

        # Step 2: Fetch subscribed channels
        logger.info("Fetching subscribed channels...")
        channels = get_subscribed_channels(credentials)
        logger.info("Found %d subscribed channels", len(channels))

        # Step 2b: Exclude channels by name
        if exclude_channels:
            before_count = len(channels)
            excluded_set_lower = {name.lower() for name in exclude_channels}
            matched_lower: set[str] = set()
            for ch in channels:
                if ch["title"].lower() in excluded_set_lower:
                    logger.info("Skipping %s (excluded)", ch["title"])
                    matched_lower.add(ch["title"].lower())
            channels = [ch for ch in channels if ch["title"].lower() not in excluded_set_lower]
            excluded_count = before_count - len(channels)
            if excluded_count > 0:
                logger.info("Excluded %d channels by name", excluded_count)
            for name in exclude_channels:
                if name.lower() not in matched_lower:
                    logger.warning('exclude channel "%s" not found in subscriptions', name)

        # Step 3: Fetch recent videos from all channels
        since = datetime.now(timezone.utc) - timedelta(days=days)
        logger.info("Fetching videos from last %d days...", days)

        all_videos = []
        for channel in channels:
            try:
                videos = get_recent_videos(credentials, channel["channel_id"], since)
                all_videos.extend(videos)
            except YouTubeAPIError as e:
                logger.warning("Failed to fetch videos from %s: %s", channel["title"], e)
                continue

        logger.info("Found %d total videos", len(all_videos))

        # Step 4: Deduplicate by video_id
        seen_ids = set()
        unique_videos = []
        for video in all_videos:
            if video["video_id"] not in seen_ids:
                seen_ids.add(video["video_id"])
                unique_videos.append(video)

        if len(unique_videos) < len(all_videos):
            logger.info("Deduplicated to %d unique videos", len(unique_videos))

        # Step 5: Skip videos already cached with transcripts
        uncached_videos = []
        for video in unique_videos:
            cached = load_cache(video["video_id"])
            if cached and cached.get("full_text"):
                continue  # Already have a transcript
            uncached_videos.append(video)

        skipped_count = len(unique_videos) - len(uncached_videos)
        if skipped_count > 0:
            logger.info("Skipped %d videos already cached", skipped_count)

        # Step 5b: Filter out YouTube Shorts (<= 60 seconds)
        if uncached_videos:
            durations = get_video_durations(credentials, [v["video_id"] for v in uncached_videos])
            non_shorts = []
            for video in uncached_videos:
                duration = durations.get(video["video_id"])
                if duration is not None and duration <= 60:
                    logger.info(
                        "  Skipping Short: [%s] %s (%ds)",
                        video["channel"],
                        video["title"],
                        duration,
                    )
                else:
                    non_shorts.append(video)
            shorts_count = len(uncached_videos) - len(non_shorts)
            if shorts_count > 0:
                logger.info("Filtered %d Shorts", shorts_count)
            uncached_videos = non_shorts

        # Step 6: Apply keyword filter
        if include_keywords or exclude_keywords:
            filtered_videos, reasons = keyword_filter(
                uncached_videos, include_keywords, exclude_keywords
            )
            filtered_ids = {v["video_id"] for v in filtered_videos}
            removed = [v for v in uncached_videos if v["video_id"] not in filtered_ids]
            for v in removed:
                logger.info(
                    "  Keyword filter removed: [%s] %s (reason: %s)",
                    v["channel"],
                    v["title"],
                    reasons.get(v["video_id"], "unknown"),
                )
            if removed:
                logger.info("Keyword filter removed %d videos", len(removed))
            uncached_videos = filtered_videos

        logger.info("Filtered to %d videos to process", len(uncached_videos))

        # Step 8: Dry run - print list and exit
        if dry_run:
            logger.info("DRY RUN - Videos that would be processed:")
            for video in uncached_videos:
                published_str = video["published_at"].strftime("%Y-%m-%d")
                logger.info(
                    "[%s] %s | Published: %s | ID: %s",
                    video["channel"],
                    video["title"],
                    published_str,
                    video["video_id"],
                )
            return 0

        # Step 9: Process each video
        if not uncached_videos:
            logger.info("No videos to process.")
            return 0

        logger.info("Fetching and caching transcripts...")

        processed = 0
        no_transcript = 0
        errors = 0

        for i, video in enumerate(uncached_videos, 1):
            if processed >= max_videos:
                break

            video_id = video["video_id"]
            title = video["title"]
            channel = video["channel"]

            logger.info("[%d] %s - %s", i, channel, title)

            try:
                transcript = fetch_transcript(video_id, language_code=lang)
                logger.info("  Fetched transcript (%d chars)", len(transcript))

                save_to_cache(video_id, transcript, "", title=title, channel=channel)
                logger.info("  Cached transcript")

                processed += 1

            except TranscriptError as e:
                logger.warning(str(e))
                no_transcript += 1
                continue
            except Exception as e:
                logger.warning("Unexpected error: %s: %s", type(e).__name__, e)
                errors += 1
                continue

        # Step 10: Print summary
        logger.info(
            "Processed %d videos (%d already cached, %d no transcript, %d error(s))",
            processed,
            skipped_count,
            no_transcript,
            errors,
        )

        return 0

    except YouTubeAPIError as e:
        logger.error(str(e))
        return 1
    except Exception:
        logger.exception("Unexpected error")
        return 1
