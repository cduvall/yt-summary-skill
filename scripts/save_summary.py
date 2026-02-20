"""Save a video summary to cache.

CLI: cat /tmp/yt_summary_summary.txt | python scripts/save_summary.py

Reads video metadata and transcript from /tmp/yt_summary_fetch.json (written by
fetch_transcript.py). Reads summary text from stdin. Cleans up both temp files.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from yt_summary import cache  # noqa: E402
from yt_summary.config import load_config  # noqa: E402

FETCH_TMP = Path("/tmp/yt_summary_fetch.json")


def main() -> None:
    load_config()

    if not FETCH_TMP.exists():
        print(f"Error: temp file not found: {FETCH_TMP}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(FETCH_TMP.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {FETCH_TMP}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        FETCH_TMP.unlink(missing_ok=True)

    summary = sys.stdin.read().strip()

    video_id = data.get("video_id", "")
    title = data.get("title", "")
    channel = data.get("channel", "")
    full_text = data.get("transcript", "") or ""

    if not video_id:
        print("Error: missing video_id in fetch temp file", file=sys.stderr)
        sys.exit(1)

    try:
        cache.save_to_cache(video_id, full_text, summary, title, channel)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Saved.")


if __name__ == "__main__":
    main()
