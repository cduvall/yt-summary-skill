"""Save a video summary to cache by reading JSON from stdin.

CLI: echo '<json>' | python scripts/save_summary.py

Reads JSON with fields: video_id, title, channel, url, transcript, summary.
Calls cache.save_to_cache() with the provided data.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from yt_summary import cache  # noqa: E402
from yt_summary.config import load_config  # noqa: E402


def main() -> None:
    load_config()

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    video_id = data.get("video_id", "")
    title = data.get("title", "")
    channel = data.get("channel", "")
    full_text = data.get("transcript", "") or ""
    summary = data.get("summary", "") or ""

    if not video_id:
        print("Error: missing required field: video_id", file=sys.stderr)
        sys.exit(1)

    try:
        cache.save_to_cache(video_id, full_text, summary, title, channel)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Saved.")


if __name__ == "__main__":
    main()
