"""File-based caching for video transcripts and summaries."""

import json
from pathlib import Path

from yt_summary.config import get_obsidian_vault_path
from yt_summary.markdown import generate_markdown, parse_markdown

__all__ = ["load_cache", "save_to_cache", "is_legacy_filename"]


def _get_cache_dir() -> Path:
    """Get the cache directory path from configuration."""
    return get_obsidian_vault_path()


def _find_cache_file(video_id: str) -> Path | None:
    """
    Find cache file for a video ID.

    Searches recursively for:
    1. New format: {title} [{video_id}].md (in channel subdirectories)
    2. Old format: {video_id} – {title}.md (flat or in subdirectories)
    3. Legacy JSON: {video_id}.json

    Args:
        video_id: YouTube video ID

    Returns:
        Path to cache file if found, None otherwise
    """
    cache_dir = _get_cache_dir()
    if not cache_dir.exists():
        return None

    # Search recursively for new format: files ending with [{video_id}].md
    # Note: Can't use glob with literal brackets, so search all .md files and filter
    pattern_suffix = f"[{video_id}].md"
    for cache_file in cache_dir.rglob("*.md"):
        if cache_file.name.endswith(pattern_suffix):
            return cache_file

    # Fall back to old format: files starting with video_id
    for cache_file in cache_dir.rglob(f"{video_id}*.md"):
        return cache_file

    # Fall back to legacy JSON format
    for cache_file in cache_dir.rglob(f"{video_id}*.json"):
        return cache_file

    return None


def _local_is_legacy_filename(video_id: str) -> bool:
    """
    Check if cached file uses legacy format (old filename or flat structure).

    Args:
        video_id: YouTube video ID

    Returns:
        True if cache file exists and uses legacy format, False otherwise
    """
    cache_file = _find_cache_file(video_id)
    if not cache_file:
        return False

    # JSON files are always legacy
    if cache_file.suffix == ".json":
        return True

    # Old markdown format: {video_id} – {title}.md
    if cache_file.name.startswith(f"{video_id} –"):
        return True

    # Legacy markdown format: exactly {video_id}.md
    if cache_file.name == f"{video_id}.md":
        return True

    # Check if file is outside Summaries/ subdirectory
    cache_dir = _get_cache_dir()
    summaries_dir = cache_dir / "Summaries"
    try:
        cache_file.relative_to(summaries_dir)
    except ValueError:
        return True

    # Check if file is in flat structure (not in channel subdirectory)
    if cache_file.parent == summaries_dir:
        return True

    return False


def is_legacy_filename(video_id: str) -> bool:
    """
    Check if cached file uses legacy format.

    Args:
        video_id: YouTube video ID

    Returns:
        True if cache file exists and uses legacy format, False otherwise
    """
    return _local_is_legacy_filename(video_id)


def _local_load_cache(video_id: str) -> dict | None:
    """Load cached data for a video from local filesystem.

    Supports markdown (.md) and JSON (.json) formats.
    Automatically migrates JSON files to markdown on load.

    Args:
        video_id: YouTube video ID

    Returns:
        Dictionary with video_id, title, channel, full_text, and summary, or None if not cached
    """
    cache_file = _find_cache_file(video_id)
    if not cache_file or not cache_file.exists():
        return None

    # Handle JSON format (legacy - convert to markdown)
    if cache_file.suffix == ".json":
        json_data = json.loads(cache_file.read_text())

        # Extract data from JSON
        video_id = json_data.get("video_id", video_id)
        title = json_data.get("title", "")
        channel = json_data.get("channel", "")  # May not exist in old files
        full_text = json_data.get("full_text", "")
        summary = json_data.get("summary", "")

        # Convert to markdown and save
        if full_text or summary:
            save_to_cache(video_id, full_text, summary, title, channel)

        # Delete old JSON file
        cache_file.unlink()

        # Add channel to result if it wasn't in JSON
        if "channel" not in json_data:
            json_data["channel"] = ""
        return json_data

    # Handle markdown format
    markdown_content = cache_file.read_text()
    return parse_markdown(markdown_content)


def load_cache(video_id: str) -> dict | None:
    """Load cached data for a video if it exists.

    Args:
        video_id: YouTube video ID

    Returns:
        Dictionary with video_id, title, channel, full_text, and summary, or None if not cached
    """
    return _local_load_cache(video_id)


def _ensure_daily_review(cache_dir: Path) -> None:
    """Create Daily Review.md Dataview note if it doesn't exist.

    Args:
        cache_dir: Root cache/vault directory
    """
    review_file = cache_dir / "Daily Review.md"
    if review_file.exists():
        return

    content = """---
---
# Daily Review

```dataview
TABLE title, channel, cached_at
FROM "Summaries"
WHERE read != true
SORT cached_at DESC
```
"""
    review_file.write_text(content)


def _ensure_starred_review(cache_dir: Path) -> None:
    """Create Starred.md Dataview note if it doesn't exist.

    Args:
        cache_dir: Root cache/vault directory
    """
    starred_file = cache_dir / "Starred.md"
    if starred_file.exists():
        return

    content = """---
---
# Starred

```dataview
TABLE title, channel, cached_at
FROM "Summaries"
WHERE starred = true
SORT cached_at DESC
```
"""
    starred_file.write_text(content)


def _local_save_to_cache(
    video_id: str,
    full_text: str,
    summary: str = "",
    title: str = "",
    channel: str = "",
    playlist_id: str = "",
    playlist_title: str = "",
) -> None:
    """
    Save video data to local cache as markdown in Summaries subdirectory.

    Args:
        video_id: YouTube video ID
        full_text: Video transcript
        summary: Video summary (optional)
        title: Video title for filename (optional)
        channel: Channel name for subdirectory (optional)
        playlist_id: YouTube playlist ID (optional)
        playlist_title: Playlist title (optional)
    """
    cache_dir = _get_cache_dir()
    cache_dir.mkdir(exist_ok=True, parents=True)

    # Ensure Daily Review.md exists at vault root
    _ensure_daily_review(cache_dir)
    _ensure_starred_review(cache_dir)

    # All summaries go into Summaries/ subfolder
    summaries_dir = cache_dir / "Summaries"
    summaries_dir.mkdir(exist_ok=True, parents=True)

    # Determine target directory (with channel subfolder if provided)
    if channel:
        from yt_summary.metadata import sanitize_filename

        channel_dir = summaries_dir / sanitize_filename(channel)
        channel_dir.mkdir(exist_ok=True, parents=True)
        target_dir = channel_dir
    else:
        target_dir = summaries_dir

    # Determine filename - new format: {title} [{video_id}].md
    if title:
        from yt_summary.metadata import sanitize_filename

        sanitized_title = sanitize_filename(title)
        filename = f"{sanitized_title} [{video_id}].md"
    else:
        filename = f"[{video_id}].md"

    cache_file = target_dir / filename

    # Check if we need to rename/move an existing file
    existing_file = _find_cache_file(video_id)
    if existing_file and existing_file != cache_file:
        # Load existing data before moving
        if existing_file.suffix == ".json":
            existing_data = json.loads(existing_file.read_text())
        else:
            existing_data = parse_markdown(existing_file.read_text())
        existing_file.unlink()
    else:
        existing_data = {}

    # Merge data (only update with non-empty values)
    data = {
        "video_id": video_id,
        "full_text": full_text,
        "summary": summary,
        "title": title,
        "channel": channel,
        "playlist_id": playlist_id,
        "playlist_title": playlist_title,
    }

    existing_data.update({k: v for k, v in data.items() if v})

    # Ensure required fields
    final_video_id = existing_data.get("video_id", video_id)
    final_title = existing_data.get("title", title or "")
    final_channel = existing_data.get("channel", channel or "")
    final_playlist_id = existing_data.get("playlist_id", playlist_id or "")
    final_playlist_title = existing_data.get("playlist_title", playlist_title or "")
    final_full_text = existing_data.get("full_text", "")
    final_summary = existing_data.get("summary", "")

    # Generate markdown content
    markdown_content = generate_markdown(
        final_video_id,
        final_title,
        final_full_text,
        final_summary,
        final_channel,
        playlist_id=final_playlist_id,
        playlist_title=final_playlist_title,
    )

    # Write to file
    cache_file.write_text(markdown_content)


def save_to_cache(
    video_id: str,
    full_text: str,
    summary: str = "",
    title: str = "",
    channel: str = "",
    playlist_id: str = "",
    playlist_title: str = "",
) -> None:
    """
    Save video data to cache.

    Args:
        video_id: YouTube video ID
        full_text: Video transcript
        summary: Video summary (optional)
        title: Video title for filename (optional)
        channel: Channel name for subdirectory (optional)
        playlist_id: YouTube playlist ID (optional)
        playlist_title: Playlist title (optional)
    """
    _local_save_to_cache(video_id, full_text, summary, title, channel, playlist_id, playlist_title)
