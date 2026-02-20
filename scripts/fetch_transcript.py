"""Fetch transcript for a YouTube video and output JSON to stdout.

CLI: python scripts/fetch_transcript.py <url_or_video_id>

Outputs JSON with video_id, title, channel, url, transcript, cached_summary.
If a cached summary exists, sets cached_summary and transcript=null.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from yt_summary import cache, metadata, transcript, youtube_utils  # noqa: E402
from yt_summary.config import get_transcript_language, load_config  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/fetch_transcript.py <url_or_video_id>", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]
    load_config()

    # Determine video ID
    if len(arg) == 11 and "/" not in arg and "." not in arg:
        video_id = arg
    else:
        video_id = youtube_utils.extract_video_id(arg)
        if not video_id:
            print(f"Error: could not extract video ID from: {arg}", file=sys.stderr)
            sys.exit(1)

    url = f"https://www.youtube.com/watch?v={video_id}"

    # Check cache
    cached = cache.load_cache(video_id)

    if cached and cached.get("summary"):
        # Full cache hit — return cached summary, no transcript needed
        result = {
            "video_id": video_id,
            "title": cached.get("title", ""),
            "channel": cached.get("channel", ""),
            "url": url,
            "transcript": None,
            "cached_summary": cached["summary"],
        }
        print(json.dumps(result))
        return

    if cached and cached.get("full_text"):
        # Transcript cached but not yet summarized
        full_text = cached["full_text"]
        title = cached.get("title", "")
        channel = cached.get("channel", "")
    else:
        # Nothing cached — fetch transcript and metadata
        language_code = get_transcript_language()
        try:
            full_text = transcript.fetch_transcript(video_id, language_code)
        except transcript.TranscriptError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            meta = metadata.fetch_video_metadata(video_id)
        except metadata.MetadataError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        title = meta["title"]
        channel = meta["channel"]

        # Save transcript to cache immediately
        cache.save_to_cache(video_id, full_text, title=title, channel=channel)

    result = {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "url": url,
        "transcript": full_text,
        "cached_summary": None,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
