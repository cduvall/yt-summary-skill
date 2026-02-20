"""Tests for transcript fetching."""

import io
from unittest.mock import MagicMock, Mock, patch

import pytest
import yt_dlp.utils

from yt_summary.transcript import (
    TranscriptError,
    _error_message,
    _extract_subtitles,
    _find_any_subtitle_url,
    _find_subtitle_url,
    _is_permanent_error,
    _parse_webvtt,
    _PermanentError,
    fetch_transcript,
)


class TestParseWebVTT:
    """Test WebVTT parsing to plain text."""

    def test_basic_webvtt_parsing(self) -> None:
        """Parse basic WebVTT with header, timestamps, and text."""
        content = """WEBVTT

1
00:00:00.000 --> 00:00:02.000
Hello world

2
00:00:02.000 --> 00:00:04.000
This is a test
"""
        result = _parse_webvtt(content)
        assert result == "Hello world\nThis is a test"

    def test_html_entity_unescaping(self) -> None:
        """Unescape HTML entities in WebVTT content."""
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000
It&#39;s working &amp; that&#39;s &quot;great&quot;
"""
        result = _parse_webvtt(content)
        assert result == "It's working & that's \"great\""

    def test_html_tag_stripping(self) -> None:
        """Strip HTML and WebVTT tags from content."""
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000
<c>Hello</c> <c.colorCCCCCC>world</c.colorCCCCCC>

00:00:02.000 --> 00:00:04.000
<b>Bold text</b> and <i>italic</i>
"""
        result = _parse_webvtt(content)
        assert result == "Hello world\nBold text and italic"

    def test_consecutive_duplicate_deduplication(self) -> None:
        """Deduplicate consecutive identical lines."""
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.000
Hello world

00:00:04.000 --> 00:00:06.000
Different text
"""
        result = _parse_webvtt(content)
        assert result == "Hello world\nDifferent text"

    def test_empty_content_returns_empty_string(self) -> None:
        """Return empty string for empty content."""
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000

00:00:02.000 --> 00:00:04.000

"""
        result = _parse_webvtt(content)
        assert result == ""

    def test_unicode_content(self) -> None:
        """Handle unicode content correctly."""
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello 世界

00:00:02.000 --> 00:00:04.000
🌍 Привет мир
"""
        result = _parse_webvtt(content)
        assert result == "Hello 世界\n🌍 Привет мир"
        assert "世界" in result
        assert "Привет" in result

    def test_note_style_region_blocks_skipped(self) -> None:
        """Skip NOTE, STYLE, and REGION blocks."""
        content = """WEBVTT

NOTE This is a comment

STYLE
::cue {
  background-image: linear-gradient(to bottom, dimgray, lightgray);
}

REGION
id:fred
width:40%

00:00:00.000 --> 00:00:02.000
Actual content
"""
        result = _parse_webvtt(content)
        assert result == "Actual content"

    def test_sequence_numbers_skipped(self) -> None:
        """Skip sequence numbers (pure digit lines)."""
        content = """WEBVTT

1
00:00:00.000 --> 00:00:02.000
First line

2
00:00:02.000 --> 00:00:04.000
Second line

123
00:00:04.000 --> 00:00:06.000
Third line
"""
        result = _parse_webvtt(content)
        assert result == "First line\nSecond line\nThird line"


class TestFindSubtitleURL:
    """Test finding subtitle URLs from yt-dlp subtitle dictionaries."""

    def test_finds_vtt_url_for_language(self) -> None:
        """Find VTT URL for a specific language."""
        subs_dict = {
            "en": [
                {"ext": "json3", "url": "https://example.com/en.json3"},
                {"ext": "vtt", "url": "https://example.com/en.vtt"},
            ],
            "es": [
                {"ext": "vtt", "url": "https://example.com/es.vtt"},
            ],
        }
        result = _find_subtitle_url(subs_dict, "en")
        assert result == "https://example.com/en.vtt"

    def test_returns_none_when_language_not_present(self) -> None:
        """Return None when language is not present."""
        subs_dict = {
            "en": [
                {"ext": "vtt", "url": "https://example.com/en.vtt"},
            ],
        }
        result = _find_subtitle_url(subs_dict, "ja")
        assert result is None

    def test_returns_none_when_no_vtt_format(self) -> None:
        """Return None when no VTT format is available."""
        subs_dict = {
            "en": [
                {"ext": "json3", "url": "https://example.com/en.json3"},
                {"ext": "srv1", "url": "https://example.com/en.srv1"},
            ],
        }
        result = _find_subtitle_url(subs_dict, "en")
        assert result is None


class TestFindAnySubtitleURL:
    """Test finding any available subtitle URL."""

    def test_returns_first_available_vtt(self) -> None:
        """Return first available VTT URL."""
        subs_dict = {
            "en": [
                {"ext": "json3", "url": "https://example.com/en.json3"},
            ],
            "es": [
                {"ext": "vtt", "url": "https://example.com/es.vtt"},
            ],
            "ja": [
                {"ext": "vtt", "url": "https://example.com/ja.vtt"},
            ],
        }
        result = _find_any_subtitle_url(subs_dict)
        assert result == "https://example.com/es.vtt"

    def test_returns_none_when_no_vtt_available(self) -> None:
        """Return None when no VTT format is available."""
        subs_dict = {
            "en": [
                {"ext": "json3", "url": "https://example.com/en.json3"},
            ],
            "es": [
                {"ext": "srv1", "url": "https://example.com/es.srv1"},
            ],
        }
        result = _find_any_subtitle_url(subs_dict)
        assert result is None


class TestExtractSubtitles:
    """Test subtitle extraction with yt-dlp."""

    @patch("yt_summary.transcript.urllib.request.urlopen")
    @patch("yt_summary.transcript.yt_dlp.YoutubeDL")
    def test_priority_manual_subs_preferred_language(self, mock_ydl_cls, mock_urlopen) -> None:
        """Prefer manual subtitles in the preferred language."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "subtitles": {
                "en": [{"ext": "vtt", "url": "https://example.com/manual_en.vtt"}],
            },
            "automatic_captions": {
                "en": [{"ext": "vtt", "url": "https://example.com/auto_en.vtt"}],
            },
        }
        mock_ydl_cls.return_value = mock_ydl

        mock_response = MagicMock()
        mock_response.__enter__ = Mock(
            return_value=io.BytesIO(b"WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nManual subtitle")
        )
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = _extract_subtitles("https://youtube.com/watch?v=test", "test", "en")
        assert "Manual subtitle" in result
        mock_urlopen.assert_called_once_with("https://example.com/manual_en.vtt")

    @patch("yt_summary.transcript.urllib.request.urlopen")
    @patch("yt_summary.transcript.yt_dlp.YoutubeDL")
    def test_priority_auto_captions_when_no_manual(self, mock_ydl_cls, mock_urlopen) -> None:
        """Fall back to auto-captions in preferred language when no manual subs."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "subtitles": {},
            "automatic_captions": {
                "en": [{"ext": "vtt", "url": "https://example.com/auto_en.vtt"}],
            },
        }
        mock_ydl_cls.return_value = mock_ydl

        mock_response = MagicMock()
        mock_response.__enter__ = Mock(
            return_value=io.BytesIO(b"WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nAuto caption")
        )
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = _extract_subtitles("https://youtube.com/watch?v=test", "test", "en")
        assert "Auto caption" in result

    @patch("yt_summary.transcript.urllib.request.urlopen")
    @patch("yt_summary.transcript.yt_dlp.YoutubeDL")
    def test_priority_any_manual_subtitle(self, mock_ydl_cls, mock_urlopen) -> None:
        """Fall back to any manual subtitle if preferred language not available."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "subtitles": {
                "es": [{"ext": "vtt", "url": "https://example.com/manual_es.vtt"}],
            },
            "automatic_captions": {
                "en": [{"ext": "vtt", "url": "https://example.com/auto_en.vtt"}],
            },
        }
        mock_ydl_cls.return_value = mock_ydl

        mock_response = MagicMock()
        mock_response.__enter__ = Mock(
            return_value=io.BytesIO(b"WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nSpanish manual")
        )
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = _extract_subtitles("https://youtube.com/watch?v=test", "test", "en")
        assert "Spanish manual" in result

    @patch("yt_summary.transcript.urllib.request.urlopen")
    @patch("yt_summary.transcript.yt_dlp.YoutubeDL")
    def test_priority_any_auto_caption(self, mock_ydl_cls, mock_urlopen) -> None:
        """Fall back to any auto-caption as last resort."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "subtitles": {},
            "automatic_captions": {
                "ja": [{"ext": "vtt", "url": "https://example.com/auto_ja.vtt"}],
            },
        }
        mock_ydl_cls.return_value = mock_ydl

        mock_response = MagicMock()
        mock_response.__enter__ = Mock(
            return_value=io.BytesIO(b"WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nJapanese auto")
        )
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = _extract_subtitles("https://youtube.com/watch?v=test", "test", "en")
        assert "Japanese auto" in result

    @patch("yt_summary.transcript.yt_dlp.YoutubeDL")
    def test_no_subtitles_raises_permanent_error(self, mock_ydl_cls) -> None:
        """Raise _PermanentError when no subtitles are available."""
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = Mock(return_value=mock_ydl)
        mock_ydl.__exit__ = Mock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "subtitles": {},
            "automatic_captions": {},
        }
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(_PermanentError, match="No subtitles found"):
            _extract_subtitles("https://youtube.com/watch?v=test", "test", "en")


class TestErrorClassification:
    """Test error classification for permanent vs transient errors."""

    def test_permanent_error_is_permanent(self) -> None:
        """_PermanentError is classified as permanent."""
        assert _is_permanent_error(_PermanentError("No subs")) is True

    def test_download_error_video_unavailable_is_permanent(self) -> None:
        """DownloadError with 'video unavailable' is permanent."""
        error = yt_dlp.utils.DownloadError("ERROR: Video unavailable")
        assert _is_permanent_error(error) is True

    def test_download_error_private_video_is_permanent(self) -> None:
        """DownloadError with 'private video' is permanent."""
        error = yt_dlp.utils.DownloadError("ERROR: This is a private video")
        assert _is_permanent_error(error) is True

    def test_download_error_age_restricted_is_permanent(self) -> None:
        """DownloadError with age restriction is permanent."""
        error = yt_dlp.utils.DownloadError("ERROR: Sign in to confirm your age")
        assert _is_permanent_error(error) is True

    def test_download_error_removed_video_is_permanent(self) -> None:
        """DownloadError with 'video has been removed' is permanent."""
        error = yt_dlp.utils.DownloadError("ERROR: This video has been removed")
        assert _is_permanent_error(error) is True

    def test_download_error_generic_is_transient(self) -> None:
        """DownloadError with generic message is transient."""
        error = yt_dlp.utils.DownloadError("ERROR: Connection timeout")
        assert _is_permanent_error(error) is False

    def test_generic_exception_is_transient(self) -> None:
        """Generic exceptions are transient."""
        assert _is_permanent_error(ValueError("Some error")) is False


class TestErrorMessage:
    """Test user-friendly error message mapping."""

    def test_permanent_error_message(self) -> None:
        """_PermanentError maps to 'No subtitles available'."""
        error = _PermanentError("No subs")
        assert _error_message(error) == "No subtitles available for this video"

    def test_video_unavailable_message(self) -> None:
        """Video unavailable error maps to friendly message."""
        error = yt_dlp.utils.DownloadError("ERROR: Video unavailable")
        assert _error_message(error) == "The video is no longer available"

    def test_private_video_message(self) -> None:
        """Private video error maps to friendly message."""
        error = yt_dlp.utils.DownloadError("ERROR: This is a private video")
        assert _error_message(error) == "The video is private"

    def test_age_restricted_message(self) -> None:
        """Age restriction error maps to friendly message."""
        error = yt_dlp.utils.DownloadError("ERROR: Sign in to confirm your age")
        assert _error_message(error) == "The video is age-restricted"

    def test_rate_limit_message(self) -> None:
        """Rate limit error maps to friendly message."""
        error = yt_dlp.utils.DownloadError("ERROR: HTTP Error 429")
        assert _error_message(error) == "YouTube is rate limiting requests"

    def test_generic_download_error_message(self) -> None:
        """Generic download error includes original message."""
        error = yt_dlp.utils.DownloadError("ERROR: Connection failed")
        message = _error_message(error)
        assert message.startswith("Failed to download video info:")
        assert "Connection failed" in message

    def test_generic_exception_message(self) -> None:
        """Generic exceptions show type and message."""
        error = ValueError("Invalid parameter")
        message = _error_message(error)
        assert message == "ValueError: Invalid parameter"


class TestFetchWithRetry:
    """Test retry logic for transient failures."""

    @patch("yt_summary.transcript._extract_subtitles")
    def test_success_on_first_attempt(self, mock_extract) -> None:
        """Return transcript on first successful attempt."""
        mock_extract.return_value = "Transcript text"
        from yt_summary.transcript import _fetch_with_retry

        result = _fetch_with_retry("test_video", "en")
        assert result == "Transcript text"
        assert mock_extract.call_count == 1

    @patch("yt_summary.transcript.time.sleep")
    @patch("yt_summary.transcript._extract_subtitles")
    def test_transient_error_then_success(self, mock_extract, mock_sleep) -> None:
        """Retry on transient error and succeed."""
        mock_extract.side_effect = [
            yt_dlp.utils.DownloadError("Connection timeout"),
            "Success after retry",
        ]
        from yt_summary.transcript import _fetch_with_retry

        result = _fetch_with_retry("test_video", "en")
        assert result == "Success after retry"
        assert mock_extract.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("yt_summary.transcript.time.sleep")
    @patch("yt_summary.transcript._extract_subtitles")
    def test_all_retries_exhausted(self, mock_extract, mock_sleep) -> None:
        """Raise exception when all retries are exhausted."""
        mock_extract.side_effect = yt_dlp.utils.DownloadError("Connection timeout")
        from yt_summary.transcript import _fetch_with_retry

        with pytest.raises(yt_dlp.utils.DownloadError):
            _fetch_with_retry("test_video", "en")
        assert mock_extract.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("yt_summary.transcript._extract_subtitles")
    def test_permanent_error_no_retry(self, mock_extract) -> None:
        """Do not retry on permanent errors."""
        mock_extract.side_effect = _PermanentError("No subtitles")
        from yt_summary.transcript import _fetch_with_retry

        with pytest.raises(_PermanentError):
            _fetch_with_retry("test_video", "en")
        assert mock_extract.call_count == 1

    @patch("yt_summary.transcript._extract_subtitles")
    def test_permanent_download_error_no_retry(self, mock_extract) -> None:
        """Do not retry on permanent DownloadError."""
        mock_extract.side_effect = yt_dlp.utils.DownloadError("Video unavailable")
        from yt_summary.transcript import _fetch_with_retry

        with pytest.raises(yt_dlp.utils.DownloadError):
            _fetch_with_retry("test_video", "en")
        assert mock_extract.call_count == 1

    @patch("yt_summary.transcript.time.sleep")
    @patch("yt_summary.transcript._extract_subtitles")
    def test_exponential_backoff_delays(self, mock_extract, mock_sleep) -> None:
        """Use exponential backoff delays (2.0s, 4.0s)."""
        mock_extract.side_effect = yt_dlp.utils.DownloadError("Connection timeout")
        from yt_summary.transcript import _fetch_with_retry

        with pytest.raises(yt_dlp.utils.DownloadError):
            _fetch_with_retry("test_video", "en")

        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

    @patch("yt_summary.transcript.time.sleep")
    @patch("yt_summary.transcript._extract_subtitles")
    def test_retry_messages_logged_to_stderr(self, mock_extract, mock_sleep, caplog) -> None:
        """Log retry attempts to logger."""
        mock_extract.side_effect = yt_dlp.utils.DownloadError("Connection timeout")
        from yt_summary.transcript import _fetch_with_retry

        with pytest.raises(yt_dlp.utils.DownloadError):
            _fetch_with_retry("test_video", "en")

        assert "Retry 1/" in caplog.text
        assert "Retry 2/" in caplog.text
        assert "test_video" in caplog.text


class TestFetchTranscript:
    """Test the public fetch_transcript API."""

    @patch("yt_summary.transcript._fetch_with_retry")
    def test_success_returns_transcript(self, mock_fetch) -> None:
        """Return transcript text on success."""
        mock_fetch.return_value = "Full transcript text"
        result = fetch_transcript("test_video", "en")
        assert result == "Full transcript text"
        mock_fetch.assert_called_once_with("test_video", "en")

    @patch("yt_summary.transcript._fetch_with_retry")
    def test_empty_transcript_raises_error(self, mock_fetch) -> None:
        """Raise TranscriptError when transcript is empty."""
        mock_fetch.return_value = "   \n  \n  "
        with pytest.raises(TranscriptError, match="empty"):
            fetch_transcript("test_video", "en")

    @patch("yt_summary.transcript._fetch_with_retry")
    def test_exception_wrapped_in_transcript_error(self, mock_fetch) -> None:
        """Wrap exceptions in TranscriptError with video_id."""
        mock_fetch.side_effect = yt_dlp.utils.DownloadError("Video unavailable")
        with pytest.raises(TranscriptError) as exc_info:
            fetch_transcript("test_video_123", "en")

        assert exc_info.value.video_id == "test_video_123"
        assert "test_video_123" in str(exc_info.value)
        assert "no longer available" in str(exc_info.value).lower()

    @patch("yt_summary.transcript._fetch_with_retry")
    def test_default_language_is_english(self, mock_fetch) -> None:
        """Default language is 'en' when not specified."""
        mock_fetch.return_value = "Transcript"
        fetch_transcript("test_video")
        mock_fetch.assert_called_once_with("test_video", "en")


class TestTranscriptError:
    """Test TranscriptError exception."""

    def test_transcript_error_with_video_id(self) -> None:
        """TranscriptError stores video ID."""
        error = TranscriptError("Test message", video_id="abc123")
        assert error.message == "Test message"
        assert error.video_id == "abc123"
        assert str(error) == "Test message"

    def test_transcript_error_without_video_id(self) -> None:
        """TranscriptError works without video ID."""
        error = TranscriptError("Test message")
        assert error.message == "Test message"
        assert error.video_id == ""
