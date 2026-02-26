"""Save a video summary to cache.

CLI: python scripts/save_summary.py <video_id> < /tmp/yt_summary_summary.txt

Reads existing video metadata from the cache using the video_id argument.
Reads summary text from stdin. Updates the cache file with the summary.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from yt_summary import cache  # noqa: E402
from yt_summary.config import load_config  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/save_summary.py <video_id>", file=sys.stderr)
        sys.exit(1)

    video_id = sys.argv[1]
    load_config()

    cached = cache.load_cache(video_id)
    if not cached:
        print(f"Error: no cached data found for video_id: {video_id}", file=sys.stderr)
        sys.exit(1)

    summary = sys.stdin.read().strip()

    title = cached.get("title", "")
    channel = cached.get("channel", "")
    full_text = cached.get("full_text", "") or ""

    try:
        cache.save_to_cache(video_id, full_text, summary, title, channel)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Saved.")


if __name__ == "__main__":
    main()
