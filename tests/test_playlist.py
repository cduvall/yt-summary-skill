"""Tests for playlist fetching utilities."""

from unittest.mock import MagicMock, patch

import pytest

from yt_summary.playlist import PlaylistError, PlaylistInfo, fetch_playlist_info


class TestPlaylistError:
    """Test PlaylistError exception."""

    def test_exception_with_message_and_playlist_id(self) -> None:
        err = PlaylistError("Something failed", playlist_id="PLddiDRMhpXFL")
        assert str(err) == "Something failed"
        assert err.message == "Something failed"
        assert err.playlist_id == "PLddiDRMhpXFL"

    def test_exception_with_message_only(self) -> None:
        err = PlaylistError("Something failed")
        assert str(err) == "Something failed"
        assert err.message == "Something failed"
        assert err.playlist_id == ""


class TestFetchPlaylistInfo:
    """Test fetch_playlist_info with mocked yt-dlp."""

    def _make_ydl_mock(self, title: str, entry_ids: list) -> MagicMock:
        entries = [{"id": vid_id} for vid_id in entry_ids]
        info = {"title": title, "entries": entries}
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = info
        return mock_ydl

    @patch("yt_summary.playlist.yt_dlp.YoutubeDL")
    def test_successful_fetch_with_playlist_url(self, mock_ydl_cls: MagicMock) -> None:
        mock_ydl_cls.return_value = self._make_ydl_mock(
            "My Playlist", ["abc12345678", "def12345678"]
        )

        result = fetch_playlist_info(
            "https://www.youtube.com/playlist?list=PLddiDRMhpXFLnSXGVRYBRfZalDCKkiqME"
        )

        assert isinstance(result, PlaylistInfo)
        assert result.playlist_id == "PLddiDRMhpXFLnSXGVRYBRfZalDCKkiqME"
        assert result.playlist_title == "My Playlist"
        assert result.video_ids == ["abc12345678", "def12345678"]

    @patch("yt_summary.playlist.yt_dlp.YoutubeDL")
    def test_successful_fetch_with_bare_playlist_id(self, mock_ydl_cls: MagicMock) -> None:
        mock_ydl_cls.return_value = self._make_ydl_mock("Tech Talks", ["vid11111111"])

        result = fetch_playlist_info("PLddiDRMhpXFLnSXGVRYBRfZalDCKkiqME")

        assert result.playlist_id == "PLddiDRMhpXFLnSXGVRYBRfZalDCKkiqME"
        assert result.video_ids == ["vid11111111"]
        # ydl should have been called with the constructed URL
        call_url = mock_ydl_cls.return_value.extract_info.call_args[0][0]
        assert "PLddiDRMhpXFLnSXGVRYBRfZalDCKkiqME" in call_url

    @patch("yt_summary.playlist.yt_dlp.YoutubeDL")
    def test_yt_dlp_error_raises_playlist_error(self, mock_ydl_cls: MagicMock) -> None:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Network error")
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(PlaylistError) as exc_info:
            fetch_playlist_info("https://www.youtube.com/playlist?list=PLddiDRMhpXFL")

        assert "Network error" in str(exc_info.value)
        assert exc_info.value.playlist_id != "" or "PLddiDRMhpXFL" in str(exc_info.value)

    @patch("yt_summary.playlist.yt_dlp.YoutubeDL")
    def test_empty_entries_list(self, mock_ydl_cls: MagicMock) -> None:
        mock_ydl_cls.return_value = self._make_ydl_mock("Empty Playlist", [])

        result = fetch_playlist_info("https://www.youtube.com/playlist?list=PLddiDRMhpXFL")

        assert result.video_ids == []
