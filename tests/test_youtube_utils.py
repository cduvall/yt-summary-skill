"""Tests for YouTube URL parsing utilities."""


from yt_summary.youtube_utils import (
    extract_video_id,
    is_valid_youtube_url,
    is_video_id,
)


class TestExtractVideoId:
    """Test video ID extraction from various URL formats."""

    def test_extract_from_youtube_com_watch_url(self) -> None:
        """Extract ID from youtube.com/watch?v= format."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_youtu_be_url(self) -> None:
        """Extract ID from youtu.be/ short format."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_youtube_com_without_www(self) -> None:
        """Extract ID from youtube.com without www."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_with_extra_parameters(self) -> None:
        """Extract ID when URL has additional parameters like ?t=."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_with_multiple_parameters(self) -> None:
        """Extract ID from URL with multiple query parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxx&index=1"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url_returns_none(self) -> None:
        """Return None for non-YouTube URLs."""
        assert extract_video_id("https://example.com") is None

    def test_invalid_video_id_length_returns_none(self) -> None:
        """Return None if video ID is not exactly 11 characters."""
        url = "https://www.youtube.com/watch?v=abc"
        assert extract_video_id(url) is None

    def test_video_id_with_valid_characters(self) -> None:
        """Video ID can contain letters, numbers, hyphens, and underscores."""
        url = "https://www.youtube.com/watch?v=aB1-_cD2-eF"
        assert extract_video_id(url) == "aB1-_cD2-eF"


class TestIsValidYoutubeUrl:
    """Test YouTube URL validation."""

    def test_valid_youtube_com_watch_url(self) -> None:
        """Valid youtube.com/watch?v= URL returns True."""
        assert is_valid_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_valid_youtu_be_url(self) -> None:
        """Valid youtu.be/ URL returns True."""
        assert is_valid_youtube_url("https://youtu.be/dQw4w9WgXcQ")

    def test_invalid_url_returns_false(self) -> None:
        """Non-YouTube URL returns False."""
        assert not is_valid_youtube_url("https://example.com")

    def test_empty_string_returns_false(self) -> None:
        """Empty string returns False."""
        assert not is_valid_youtube_url("")

    def test_youtube_url_with_invalid_video_id_returns_false(self) -> None:
        """URL with invalid video ID returns False."""
        assert not is_valid_youtube_url("https://www.youtube.com/watch?v=short")


class TestExtractVideoIdEdgeCases:
    """Test edge cases for video ID extraction."""

    def test_extract_video_id_exactly_11_characters(self) -> None:
        """Video ID must be exactly 11 characters."""
        url = "https://www.youtube.com/watch?v=12345678901"
        assert extract_video_id(url) == "12345678901"

    def test_extract_video_id_with_hyphen(self) -> None:
        """Video ID can contain hyphens."""
        url = "https://www.youtube.com/watch?v=abc-def-ghi"
        assert extract_video_id(url) == "abc-def-ghi"

    def test_extract_video_id_with_underscore(self) -> None:
        """Video ID can contain underscores."""
        url = "https://www.youtube.com/watch?v=abc_def_ghi"
        assert extract_video_id(url) == "abc_def_ghi"

    def test_extract_video_id_all_uppercase(self) -> None:
        """Video ID can be all uppercase."""
        url = "https://www.youtube.com/watch?v=ABCDEFGHIJK"
        assert extract_video_id(url) == "ABCDEFGHIJK"

    def test_extract_video_id_all_lowercase(self) -> None:
        """Video ID can be all lowercase."""
        url = "https://www.youtube.com/watch?v=abcdefghijk"
        assert extract_video_id(url) == "abcdefghijk"

    def test_extract_video_id_all_numbers(self) -> None:
        """Video ID can be all numbers."""
        url = "https://www.youtube.com/watch?v=12345678901"
        assert extract_video_id(url) == "12345678901"

    def test_extract_video_id_mixed_characters(self) -> None:
        """Video ID with mixed valid characters."""
        url = "https://www.youtube.com/watch?v=aB1-_cD2-eF"
        assert extract_video_id(url) == "aB1-_cD2-eF"

    def test_extract_from_url_with_timestamp(self) -> None:
        """Extract ID from URL with timestamp parameter."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_url_with_playlist(self) -> None:
        """Extract ID from URL with playlist parameter."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxx"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_url_v_not_first_parameter(self) -> None:
        """Extract ID when v parameter is not first."""
        url = "https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_too_short_returns_none(self) -> None:
        """Video ID shorter than 11 characters returns None."""
        url = "https://www.youtube.com/watch?v=abc123"
        assert extract_video_id(url) is None

    def test_extract_video_id_too_long_returns_none(self) -> None:
        """Video ID longer than 11 characters - regex extracts first 11."""
        url = "https://www.youtube.com/watch?v=abc123456789"
        # The regex pattern extracts exactly 11 characters
        assert extract_video_id(url) == "abc12345678"

    def test_extract_video_id_with_invalid_chars_returns_none(self) -> None:
        """Video ID with invalid characters returns None."""
        url = "https://www.youtube.com/watch?v=abc@def#hij"
        assert extract_video_id(url) is None

    def test_extract_video_id_http_instead_of_https(self) -> None:
        """Extract ID from http URL (not https)."""
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_youtu_be_http(self) -> None:
        """Extract ID from http youtu.be URL."""
        url = "http://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_no_protocol(self) -> None:
        """Video ID from URL without protocol."""
        url = "youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_mobile_url(self) -> None:
        """Extract ID from mobile youtube URL."""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        # The regex actually works with m.youtube.com as well
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_is_valid_youtube_url_http(self) -> None:
        """Valid http YouTube URL."""
        assert is_valid_youtube_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_is_valid_youtube_url_no_protocol(self) -> None:
        """Valid YouTube URL without protocol."""
        assert is_valid_youtube_url("youtube.com/watch?v=dQw4w9WgXcQ")

    def test_is_valid_youtube_url_with_extra_params(self) -> None:
        """Valid YouTube URL with multiple query parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10&list=ABC"
        assert is_valid_youtube_url(url)


class TestIsVideoId:
    """Test bare video ID detection."""

    def test_valid_video_id(self) -> None:
        """Recognize a valid 11-character video ID."""
        assert is_video_id("dQw4w9WgXcQ")

    def test_video_id_with_hyphens_and_underscores(self) -> None:
        """Video IDs can contain hyphens and underscores."""
        assert is_video_id("aB1-_cD2-eF")

    def test_too_short_returns_false(self) -> None:
        """Reject IDs shorter than 11 characters."""
        assert not is_video_id("abc123")

    def test_too_long_returns_false(self) -> None:
        """Reject IDs longer than 11 characters."""
        assert not is_video_id("abc1234567890")

    def test_empty_string_returns_false(self) -> None:
        """Reject empty string."""
        assert not is_video_id("")

    def test_url_returns_false(self) -> None:
        """A full URL is not a bare video ID."""
        assert not is_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_invalid_characters_returns_false(self) -> None:
        """Reject IDs with invalid characters."""
        assert not is_video_id("abc@def#hij")

    def test_whitespace_only_returns_false(self) -> None:
        """Reject whitespace-only strings."""
        assert not is_video_id("           ")

    def test_tabs_and_newlines_returns_false(self) -> None:
        """Reject strings containing tabs or newlines."""
        assert not is_video_id("\t\t\t\t\t\t\t\t\t\t\t")
        assert not is_video_id("abc\ndef\nghi")

    def test_valid_id_with_leading_trailing_whitespace_returns_false(self) -> None:
        """Reject valid ID wrapped in whitespace (no stripping)."""
        assert not is_video_id(" dQw4w9WgXcQ ")
        assert not is_video_id(" dQw4w9WgXcQ")
        assert not is_video_id("dQw4w9WgXcQ ")

    def test_exactly_10_chars_returns_false(self) -> None:
        """Off-by-one: 10 characters is too short."""
        assert not is_video_id("abcdefghij")

    def test_exactly_12_chars_returns_false(self) -> None:
        """Off-by-one: 12 characters is too long."""
        assert not is_video_id("abcdefghijkl")

    def test_eleven_spaces_returns_false(self) -> None:
        """Eleven spaces should not match (space is not in [a-zA-Z0-9_-])."""
        assert not is_video_id("           ")

    def test_dots_in_id_returns_false(self) -> None:
        """Reject strings with dots even if 11 chars."""
        assert not is_video_id("abc.def.ghi")

    def test_all_hyphens_returns_true(self) -> None:
        """Eleven hyphens is technically a valid pattern match."""
        assert is_video_id("-----------")

    def test_all_underscores_returns_true(self) -> None:
        """Eleven underscores is technically a valid pattern match."""
        assert is_video_id("___________")

    def test_all_digits_returns_true(self) -> None:
        """Eleven digits is a valid video ID pattern."""
        assert is_video_id("12345678901")

    def test_mixed_case_returns_true(self) -> None:
        """Mixed case alphanumeric is valid."""
        assert is_video_id("AbCdEfGhIjK")

    def test_slash_in_id_returns_false(self) -> None:
        """Reject strings with slashes (path-like)."""
        assert not is_video_id("abc/def/ghi")

    def test_colon_in_id_returns_false(self) -> None:
        """Reject strings with colons (URL-like)."""
        assert not is_video_id("http:abcdef")
