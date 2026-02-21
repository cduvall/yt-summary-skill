"""Tests for main CLI application."""

import sys
from unittest.mock import patch

from main import main


class TestMain:
    """Test main CLI application."""

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    def test_main_success(self, mock_fetch, mock_save, mock_cache, mock_load_config) -> None:
        """Successfully run CLI with valid inputs."""
        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        mock_fetch.assert_called_once()
        mock_save.assert_called()

    @patch("main.load_config")
    def test_main_invalid_url(self, mock_load_config) -> None:
        """Exit with error for invalid URL."""
        with patch.object(sys, "argv", ["main.py", "not-a-url"]):
            result = main()

        assert result == 1

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_transcript")
    def test_main_transcript_fetch_error(self, mock_fetch, mock_cache, mock_load_config) -> None:
        """Exit with error when transcript fetch fails."""
        from yt_summary.transcript import TranscriptError

        mock_fetch.side_effect = TranscriptError("No captions available")

        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 1

    @patch("main.setup_logging")
    @patch("main.load_config")
    @patch("main.load_cache")
    @patch("main.fetch_transcript")
    def test_main_with_cached_transcript(
        self, mock_fetch, mock_cache, mock_load_config, mock_setup_logging, capsys, caplog
    ) -> None:
        """Skip fetch when transcript already cached."""
        import logging

        caplog.set_level(logging.INFO)
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "cached summary text",
        }

        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        mock_fetch.assert_not_called()
        captured = capsys.readouterr()
        assert "Transcript cached." in captured.out
        assert "Transcript already cached for" in caplog.text

    @patch("main.load_config")
    @patch("main.load_cache")
    def test_main_with_bare_video_id(self, mock_cache, mock_load_config, capsys) -> None:
        """Accept a bare video ID instead of a full URL."""
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "cached summary",
        }

        with patch.object(sys, "argv", ["main.py", "dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        mock_cache.assert_called_once_with("dQw4w9WgXcQ")

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    def test_main_bare_video_id_full_flow(
        self, mock_fetch, mock_save, mock_cache, mock_load_config
    ) -> None:
        """Bare video ID triggers full fetch+cache flow (no prior cache)."""
        with patch.object(sys, "argv", ["main.py", "dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        mock_fetch.assert_called_once_with("dQw4w9WgXcQ", language_code="en")
        mock_save.assert_called()

    @patch("main.load_config")
    @patch("main.load_cache")
    def test_main_bare_video_id_with_hyphens_underscores(
        self, mock_cache, mock_load_config, capsys
    ) -> None:
        """Bare video ID containing hyphens and underscores is accepted."""
        mock_cache.return_value = {
            "video_id": "aB1-_cD2-eF",
            "full_text": "cached transcript",
            "summary": "cached summary",
        }

        with patch.object(sys, "argv", ["main.py", "aB1-_cD2-eF"]):
            result = main()

        assert result == 0
        mock_cache.assert_called_once_with("aB1-_cD2-eF")

    @patch("main.load_config")
    def test_main_invalid_bare_id_too_short(self, mock_load_config, caplog) -> None:
        """Short string that is neither a valid URL nor a valid bare ID returns error."""
        with patch.object(sys, "argv", ["main.py", "abc123"]):
            result = main()

        assert result == 1
        assert "Invalid YouTube URL or video ID" in caplog.text

    @patch("main.load_config")
    def test_main_invalid_bare_id_with_dots(self, mock_load_config, caplog) -> None:
        """11-char string with invalid chars (dots) is rejected."""
        with patch.object(sys, "argv", ["main.py", "abc.def.ghi"]):
            result = main()

        assert result == 1
        assert "Invalid YouTube URL or video ID" in caplog.text

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    def test_main_with_language_option(
        self, mock_fetch, mock_save, mock_cache, mock_load_config
    ) -> None:
        """CLI accepts language option."""
        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "--lang",
                "es",
            ],
        ):
            result = main()

        assert result == 0
        mock_fetch.assert_called_once_with("dQw4w9WgXcQ", language_code="es")

    @patch("main.setup_logging")
    @patch("main.load_config")
    @patch("main.load_cache")
    @patch("main.fetch_transcript")
    def test_main_uses_cached_transcript(
        self, mock_fetch, mock_cache, mock_load_config, mock_setup_logging, caplog
    ) -> None:
        """Use cached transcript without fetching from YouTube."""
        import logging

        caplog.set_level(logging.INFO)
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "",
        }

        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        mock_fetch.assert_not_called()
        assert "Transcript already cached for" in caplog.text

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_transcript")
    def test_main_generic_exception(self, mock_fetch, mock_cache, mock_load_config) -> None:
        """Exit with error for unexpected exceptions."""
        mock_fetch.side_effect = RuntimeError("Unexpected error")

        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 1


class TestParseArgs:
    """Test argument parsing."""

    def test_parse_args_with_url_only(self) -> None:
        """Parse arguments with only URL."""
        from main import parse_args

        args = parse_args(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        assert args.url_or_id == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert args.lang is None

    def test_parse_args_with_bare_video_id(self) -> None:
        """Parse arguments with bare video ID."""
        from main import parse_args

        args = parse_args(["dQw4w9WgXcQ"])
        assert args.url_or_id == "dQw4w9WgXcQ"

    def test_parse_args_with_lang_option(self) -> None:
        """Parse arguments with language option."""
        from main import parse_args

        args = parse_args(["https://youtu.be/abc123", "--lang", "es"])
        assert args.lang == "es"

    def test_parse_args_with_explicit_args_list(self) -> None:
        """Parse args from explicit list without using sys.argv."""
        from main import parse_args

        args = parse_args(["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "--lang", "es"])
        assert args.url_or_id == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert args.lang == "es"

    def test_parse_args_with_bare_id_and_lang(self) -> None:
        """Parse bare video ID with lang option."""
        from main import parse_args

        args = parse_args(["dQw4w9WgXcQ", "--lang", "en"])
        assert args.url_or_id == "dQw4w9WgXcQ"
        assert args.lang == "en"


class TestPrintError:
    """Test error printing."""

    def test_print_error_writes_to_stderr(self, caplog) -> None:
        """Print error message to logger."""
        from main import print_error

        print_error("Test error message")
        assert "Test error message" in caplog.text

    @patch("main.load_config")
    @patch("main.is_legacy_filename", return_value=True)
    @patch("main.load_cache")
    @patch(
        "main.fetch_video_metadata",
        return_value={"title": "Amazing Tutorial", "channel": "Tech Channel"},
    )
    @patch("main.save_to_cache")
    def test_main_renames_legacy_cache_file(
        self, mock_save, mock_fetch_metadata, mock_cache, mock_is_legacy, mock_load_config
    ) -> None:
        """Rename legacy cache file when metadata is fetched."""
        # Simulate cached transcript but legacy filename
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "cached summary",
        }

        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        # Should fetch metadata
        mock_fetch_metadata.assert_called_once_with("dQw4w9WgXcQ")
        # Should save to rename the file
        assert mock_save.call_count >= 1
        # Check that save was called with the title and channel
        save_calls = [
            call
            for call in mock_save.call_args_list
            if call[1].get("title") == "Amazing Tutorial"
            and call[1].get("channel") == "Tech Channel"
        ]
        assert len(save_calls) > 0

    @patch("main.load_config")
    @patch("main.is_legacy_filename", return_value=False)
    @patch("main.load_cache")
    @patch("main.fetch_video_metadata")
    def test_main_does_not_rename_new_format_cache(
        self, mock_fetch_metadata, mock_cache, mock_is_legacy, mock_load_config, capsys
    ) -> None:
        """Do not fetch metadata when cache already has new format filename."""
        # Simulate cached with title and channel already in filename
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "cached summary",
            "title": "Amazing Tutorial",
            "channel": "Tech Channel",
        }

        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        # Should NOT fetch metadata since file already has new format
        mock_fetch_metadata.assert_not_called()
        captured = capsys.readouterr()
        assert "Transcript cached." in captured.out
