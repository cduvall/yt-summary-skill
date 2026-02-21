"""Fetch transcripts for all videos in a YouTube playlist and output JSON to stdout.

CLI: python scripts/fetch_playlist.py <playlist_url_or_id>

Outputs JSON with playlist_id, playlist_title, vault_path, and a videos array.
Each video entry includes video_id, title, channel, url, cache_file, cached_summary,
and needs_summary. Videos that fail to fetch include an error field.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from yt_summary import cache, metadata, playlist, transcript, youtube_utils  # noqa: E402
from yt_summary.config import (  # noqa: E402
    get_obsidian_vault_path,
    get_transcript_language,
    load_config,
)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/fetch_playlist.py <playlist_url_or_id>", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]
    load_config()

    # Determine playlist ID
    if youtube_utils.is_playlist_id(arg):
        playlist_id = arg
    else:
        playlist_id = youtube_utils.extract_playlist_id(arg)
        if not playlist_id:
            print(f"Error: could not extract playlist ID from: {arg}", file=sys.stderr)
            sys.exit(1)

    vault_path = str(get_obsidian_vault_path())

    # Fetch playlist metadata and video IDs
    print(f"Fetching playlist info for: {playlist_id}", file=sys.stderr)
    try:
        playlist_info = playlist.fetch_playlist_info(playlist_id)
    except playlist.PlaylistError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Playlist: {playlist_info.playlist_title} ({len(playlist_info.video_ids)} videos)",
        file=sys.stderr,
    )

    language_code = get_transcript_language()
    videos = []

    for i, video_id in enumerate(playlist_info.video_ids, 1):
        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"[{i}/{len(playlist_info.video_ids)}] Processing {video_id}", file=sys.stderr)

        # Check cache
        cached = cache.load_cache(video_id)

        if cached and cached.get("summary"):
            # Full cache hit -- has summary already
            cache_file = cache._find_cache_file(video_id)
            videos.append(
                {
                    "video_id": video_id,
                    "title": cached.get("title", ""),
                    "channel": cached.get("channel", ""),
                    "url": url,
                    "cache_file": str(cache_file) if cache_file else None,
                    "cached_summary": cached["summary"],
                    "needs_summary": False,
                }
            )
            continue

        if cached and cached.get("full_text"):
            # Transcript cached but not yet summarized
            cache_file = cache._find_cache_file(video_id)
            videos.append(
                {
                    "video_id": video_id,
                    "title": cached.get("title", ""),
                    "channel": cached.get("channel", ""),
                    "url": url,
                    "cache_file": str(cache_file) if cache_file else None,
                    "cached_summary": None,
                    "needs_summary": True,
                }
            )
            continue

        # Nothing cached -- fetch transcript and metadata
        try:
            full_text = transcript.fetch_transcript(video_id, language_code)
        except transcript.TranscriptError as e:
            print(f"  Error fetching transcript for {video_id}: {e}", file=sys.stderr)
            videos.append(
                {
                    "video_id": video_id,
                    "title": "",
                    "channel": "",
                    "url": url,
                    "cache_file": None,
                    "cached_summary": None,
                    "needs_summary": False,
                    "error": str(e),
                }
            )
            continue

        try:
            meta = metadata.fetch_video_metadata(video_id)
        except metadata.MetadataError as e:
            print(f"  Error fetching metadata for {video_id}: {e}", file=sys.stderr)
            videos.append(
                {
                    "video_id": video_id,
                    "title": "",
                    "channel": "",
                    "url": url,
                    "cache_file": None,
                    "cached_summary": None,
                    "needs_summary": False,
                    "error": str(e),
                }
            )
            continue

        title = meta["title"]
        channel = meta["channel"]

        cache.save_to_cache(
            video_id,
            full_text,
            title=title,
            channel=channel,
            playlist_id=playlist_info.playlist_id,
            playlist_title=playlist_info.playlist_title,
        )

        cache_file = cache._find_cache_file(video_id)
        videos.append(
            {
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "url": url,
                "cache_file": str(cache_file) if cache_file else None,
                "cached_summary": None,
                "needs_summary": True,
            }
        )

    result = {
        "playlist_id": playlist_info.playlist_id,
        "playlist_title": playlist_info.playlist_title,
        "vault_path": vault_path,
        "videos": videos,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
