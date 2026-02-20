"""YouTube URL parsing and validation utilities."""

import re


def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from various URL formats.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID&t=...

    Args:
        url: YouTube URL string

    Returns:
        Video ID if valid URL, None otherwise
    """
    # Pattern for youtube.com/watch?v=...
    match = re.search(
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/watch\?.*&v=)([a-zA-Z0-9_-]{11})", url
    )
    if match:
        return match.group(1)
    return None


def is_video_id(value: str) -> bool:
    """Check if a string is a bare YouTube video ID (11 chars, valid characters)."""
    return bool(re.fullmatch(r"[a-zA-Z0-9_-]{11}", value))


def is_valid_youtube_url(url: str) -> bool:
    """
    Check if a URL is a valid YouTube URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid YouTube URL, False otherwise
    """
    return extract_video_id(url) is not None
