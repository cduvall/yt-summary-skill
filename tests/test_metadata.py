"""Tests for metadata fetching and filename sanitization."""

from unittest.mock import Mock, patch

import pytest

from yt_summary.metadata import (
    MetadataError,
    fetch_video_metadata,
    sanitize_filename,
)


class TestSanitizeFilename:
    """Test filename sanitization with various inputs."""

    def test_sanitize_basic_title(self) -> None:
        """Sanitize a simple, valid title."""
        result = sanitize_filename("How to Code in Python")
        assert result == "How to Code in Python"

    def test_sanitize_removes_invalid_characters(self) -> None:
        """Remove characters invalid in filenames."""
        result = sanitize_filename('Video: "Title" <Part 1> [2024]')
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result
        assert result == "Video Title Part 1 [2024]"

    def test_sanitize_removes_path_separators(self) -> None:
        """Remove forward and backward slashes."""
        result = sanitize_filename("Parent/Child\\Grandchild")
        assert "/" not in result
        assert "\\" not in result
        assert result == "Parent Child Grandchild"

    def test_sanitize_removes_windows_reserved(self) -> None:
        """Remove Windows reserved characters."""
        result = sanitize_filename("File|Name?With*Colon:")
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result
        assert ":" not in result
        assert result == "File Name With Colon"

    def test_sanitize_collapses_multiple_spaces(self) -> None:
        """Replace multiple spaces with single space."""
        result = sanitize_filename("Title    with     many      spaces")
        assert result == "Title with many spaces"

    def test_sanitize_trims_whitespace(self) -> None:
        """Trim leading and trailing whitespace."""
        result = sanitize_filename("   Title with spaces   ")
        assert result == "Title with spaces"

    def test_sanitize_limits_length(self) -> None:
        """Limit filename to 200 characters."""
        long_title = "A" * 300
        result = sanitize_filename(long_title)
        assert len(result) == 200

    def test_sanitize_preserves_unicode(self) -> None:
        """Preserve unicode characters."""
        result = sanitize_filename("世界 Hello Мир")
        assert result == "世界 Hello Мир"

    def test_sanitize_preserves_emoji(self) -> None:
        """Preserve emoji characters."""
        result = sanitize_filename("Tutorial 🎉 Part 1 🚀")
        assert result == "Tutorial 🎉 Part 1 🚀"

    def test_sanitize_empty_string(self) -> None:
        """Handle empty string."""
        result = sanitize_filename("")
        assert result == ""

    def test_sanitize_only_invalid_characters(self) -> None:
        """Handle string with only invalid characters."""
        result = sanitize_filename('<>:"/\\|?*')
        assert result == ""

    def test_sanitize_mixed_valid_invalid(self) -> None:
        """Handle mix of valid and invalid characters."""
        result = sanitize_filename("Valid<Invalid>Valid")
        assert result == "Valid Invalid Valid"

    def test_sanitize_preserves_hyphens_underscores(self) -> None:
        """Preserve hyphens and underscores."""
        result = sanitize_filename("My-Video_Title-2024")
        assert result == "My-Video_Title-2024"

    def test_sanitize_preserves_parentheses_brackets(self) -> None:
        """Preserve parentheses and square brackets."""
        result = sanitize_filename("Title (Part 1) [HD]")
        assert result == "Title (Part 1) [HD]"

    def test_sanitize_trims_after_replacement(self) -> None:
        """Trim whitespace after replacing invalid chars."""
        result = sanitize_filename("<Leading and trailing>")
        assert result == "Leading and trailing"

    def test_sanitize_very_long_unicode_title(self) -> None:
        """Handle very long title with unicode."""
        long_unicode = "世界" * 150  # 300 characters
        result = sanitize_filename(long_unicode)
        assert len(result) == 200

    def test_sanitize_newlines_and_tabs(self) -> None:
        """Replace newlines and tabs with spaces."""
        result = sanitize_filename("Title\nwith\nnewlines\tand\ttabs")
        assert result == "Title with newlines and tabs"


class TestFetchVideoMetadata:
    """Test fetching video metadata (title and channel)."""

    def test_fetch_video_metadata_success(self) -> None:
        """Fetch both title and channel successfully."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {
                "title": "Amazing Python Tutorial",
                "uploader": "Tech Channel",
            }
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert result["title"] == "Amazing Python Tutorial"
        assert result["channel"] == "Tech Channel"

    def test_fetch_video_metadata_uses_uploader_field(self) -> None:
        """Fetch channel from uploader field."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {
                "title": "Test Video",
                "uploader": "Primary Channel",
            }
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert result["channel"] == "Primary Channel"

    def test_fetch_video_metadata_fallback_to_channel_field(self) -> None:
        """Fall back to channel field if uploader is missing."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {
                "title": "Test Video",
                "channel": "Fallback Channel",
            }
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert result["channel"] == "Fallback Channel"

    def test_fetch_video_metadata_fallback_to_uploader_id(self) -> None:
        """Fall back to uploader_id if uploader and channel are missing."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {
                "title": "Test Video",
                "uploader_id": "channel_id_123",
            }
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert result["channel"] == "channel_id_123"

    def test_fetch_video_metadata_missing_channel(self) -> None:
        """Return empty channel when no channel field is available."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {"title": "Test Video"}
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert result["channel"] == ""

    def test_fetch_video_metadata_sanitizes_title(self) -> None:
        """Sanitize title in returned metadata."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {
                "title": 'Tutorial: "Part 1" <HD>',
                "uploader": "Tech Channel",
            }
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert '"' not in result["title"]
        assert "<" not in result["title"]
        assert ">" not in result["title"]
        assert result["title"] == "Tutorial Part 1 HD"

    def test_fetch_video_metadata_sanitizes_channel(self) -> None:
        """Sanitize channel name in returned metadata."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {
                "title": "Test Video",
                "uploader": 'Channel: "Official" <HD>',
            }
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert '"' not in result["channel"]
        assert "<" not in result["channel"]
        assert ">" not in result["channel"]
        assert result["channel"] == "Channel Official HD"

    def test_fetch_video_metadata_empty_title_raises(self) -> None:
        """Raise MetadataError when title is empty."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {"title": ""}
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            with pytest.raises(MetadataError) as exc_info:
                fetch_video_metadata("abc123")

        assert "Could not fetch title for video abc123" in str(exc_info.value)
        assert exc_info.value.video_id == "abc123"

    def test_fetch_video_metadata_none_title_raises(self) -> None:
        """Raise MetadataError when title is None."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {"title": None}
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            with pytest.raises(MetadataError) as exc_info:
                fetch_video_metadata("abc123")

        assert "Could not fetch title for video abc123" in str(exc_info.value)
        assert exc_info.value.video_id == "abc123"

    def test_fetch_video_metadata_yt_dlp_exception(self) -> None:
        """Raise MetadataError when yt-dlp raises exception."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.side_effect = Exception("Network error")
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            with pytest.raises(MetadataError) as exc_info:
                fetch_video_metadata("abc123")

        assert "Could not fetch metadata for video abc123" in str(exc_info.value)
        assert "Network error" in str(exc_info.value)
        assert exc_info.value.video_id == "abc123"

    def test_fetch_video_metadata_unicode_title_and_channel(self) -> None:
        """Handle unicode characters in title and channel."""
        with patch("yt_summary.metadata.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = Mock()
            mock_ydl.extract_info.return_value = {
                "title": "世界 Hello Мир 🌍",
                "uploader": "日本語チャンネル",
            }
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            result = fetch_video_metadata("abc123")

        assert result["title"] == "世界 Hello Мир 🌍"
        assert result["channel"] == "日本語チャンネル"
