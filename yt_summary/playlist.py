"""Fetch YouTube playlist metadata without downloading videos."""

import os
from dataclasses import dataclass

import yt_dlp

from yt_summary.metadata import sanitize_filename
from yt_summary.youtube_utils import extract_playlist_id, is_playlist_id


class PlaylistError(Exception):
    """Exception raised when playlist info cannot be fetched."""

    def __init__(self, message: str, playlist_id: str = "") -> None:
        """Initialize PlaylistError with optional playlist ID."""
        self.message = message
        self.playlist_id = playlist_id
        super().__init__(message)


@dataclass
class PlaylistInfo:
    """Metadata for a YouTube playlist."""

    playlist_id: str
    playlist_title: str
    video_ids: list[str]


def fetch_playlist_info(playlist_id_or_url: str) -> PlaylistInfo:
    """
    Fetch metadata for a YouTube playlist using yt-dlp.

    Accepts either a bare playlist ID or a full playlist URL.

    Args:
        playlist_id_or_url: YouTube playlist ID or URL

    Returns:
        PlaylistInfo with playlist_id, playlist_title, and video_ids

    Raises:
        PlaylistError: If playlist info cannot be fetched
    """
    try:
        if is_playlist_id(playlist_id_or_url):
            playlist_id = playlist_id_or_url
            url = f"https://www.youtube.com/playlist?list={playlist_id}"
        else:
            playlist_id = extract_playlist_id(playlist_id_or_url) or ""
            url = playlist_id_or_url

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
        }

        cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
        if cookies_file and os.path.isfile(cookies_file):
            ydl_opts["cookiefile"] = cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        raw_title = info.get("title", "")
        video_ids = [entry["id"] for entry in info.get("entries", []) if entry.get("id")]

        return PlaylistInfo(
            playlist_id=playlist_id,
            playlist_title=sanitize_filename(raw_title) if raw_title else "",
            video_ids=video_ids,
        )
    except Exception as e:
        raise PlaylistError(
            f"Could not fetch playlist info for {playlist_id_or_url}: {str(e)}",
            playlist_id=playlist_id_or_url,
        ) from e
