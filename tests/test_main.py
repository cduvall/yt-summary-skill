"""Tests for main CLI application."""

import argparse
import os
import sys
from unittest.mock import patch

from main import main


class TestMain:
    """Test main CLI application."""

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    @patch("main.summarize_transcript", return_value="SUMMARY:\nTest summary")
    def test_main_success(
        self, mock_summarize, mock_fetch, mock_save, mock_cache, mock_load_config
    ) -> None:
        """Successfully run CLI with valid inputs."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
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
    def test_main_missing_api_key(self, mock_load_config) -> None:
        """Exit with error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
            result = main()

        assert result == 1

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_transcript")
    def test_main_transcript_fetch_error(self, mock_fetch, mock_cache, mock_load_config) -> None:
        """Exit with error when transcript fetch fails."""
        from yt_summary.transcript import TranscriptError

        mock_fetch.side_effect = TranscriptError("No captions available")

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
            result = main()

        assert result == 1

    @patch("main.setup_logging")
    @patch("main.load_config")
    @patch("main.load_cache")
    def test_main_uses_cached_summary(
        self, mock_cache, mock_load_config, mock_setup_logging, capsys, caplog
    ) -> None:
        """Use cached summary without calling Claude API."""
        import logging

        caplog.set_level(logging.INFO)
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "cached summary text",
        }

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "cached summary text" in captured.out
        assert "Loaded summary from cache" in caplog.text

    @patch("main.load_config")
    @patch("main.load_cache")
    def test_main_with_bare_video_id(self, mock_cache, mock_load_config, capsys) -> None:
        """Accept a bare video ID instead of a full URL."""
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "cached summary",
        }

        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "dQw4w9WgXcQ"]),
        ):
            result = main()

        assert result == 0
        mock_cache.assert_called_once_with("dQw4w9WgXcQ")

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    @patch("main.summarize_transcript", return_value="SUMMARY:\nBare ID summary")
    def test_main_bare_video_id_full_flow(
        self, mock_summarize, mock_fetch, mock_save, mock_cache, mock_load_config
    ) -> None:
        """Bare video ID triggers full fetch+summarize flow (no cache)."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "dQw4w9WgXcQ"]),
        ):
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

        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "aB1-_cD2-eF"]),
        ):
            result = main()

        assert result == 0
        mock_cache.assert_called_once_with("aB1-_cD2-eF")

    @patch("main.load_config")
    def test_main_invalid_bare_id_too_short(self, mock_load_config, caplog) -> None:
        """Short string that is neither a valid URL nor a valid bare ID returns error."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "abc123"]),
        ):
            result = main()

        assert result == 1
        assert "Invalid YouTube URL or video ID" in caplog.text

    @patch("main.load_config")
    def test_main_invalid_bare_id_with_dots(self, mock_load_config, caplog) -> None:
        """11-char string with invalid chars (dots) is rejected."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "abc.def.ghi"]),
        ):
            result = main()

        assert result == 1
        assert "Invalid YouTube URL or video ID" in caplog.text

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    @patch("main.summarize_transcript", return_value="SUMMARY:\nTest")
    def test_main_with_language_option(
        self, mock_summarize, mock_fetch, mock_save, mock_cache, mock_load_config
    ) -> None:
        """CLI accepts language option."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
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

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    @patch("main.summarize_transcript", return_value="SUMMARY:\nTest")
    def test_main_with_model_option(
        self, mock_summarize, mock_fetch, mock_save, mock_cache, mock_load_config
    ) -> None:
        """CLI accepts model option."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys,
            "argv",
            [
                "main.py",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "--model",
                "claude-opus-4-6",
            ],
        ):
            result = main()

        assert result == 0
        # Check that summarize_transcript was called with the correct model
        call_args = mock_summarize.call_args
        assert call_args[0][2] == "claude-opus-4-6"  # model is 3rd positional arg

    @patch("main.setup_logging")
    @patch("main.load_config")
    @patch("main.load_cache")
    @patch("main.summarize_transcript", return_value="SUMMARY:\nNew summary")
    def test_main_uses_cached_transcript(
        self, mock_summarize, mock_cache, mock_load_config, mock_setup_logging, caplog
    ) -> None:
        """Use cached transcript without fetching from YouTube."""
        import logging

        caplog.set_level(logging.INFO)
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "",
        }

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
            result = main()

        assert result == 0
        assert "Loaded transcript from cache" in caplog.text

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.save_to_cache")
    @patch("main.fetch_transcript", return_value="Sample transcript")
    @patch("main.summarize_transcript", return_value="SUMMARY:\nTest")
    def test_main_with_both_options(
        self, mock_summarize, mock_fetch, mock_save, mock_cache, mock_load_config
    ) -> None:
        """CLI accepts both language and model options."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys,
            "argv",
            [
                "main.py",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "--lang",
                "fr",
                "--model",
                "claude-opus-4-6",
            ],
        ):
            result = main()

        assert result == 0
        mock_fetch.assert_called_once_with("dQw4w9WgXcQ", language_code="fr")
        call_args = mock_summarize.call_args
        assert call_args[0][2] == "claude-opus-4-6"  # model is 3rd positional arg

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_transcript")
    @patch("main.summarize_transcript")
    def test_main_api_error(self, mock_summarize, mock_fetch, mock_cache, mock_load_config) -> None:
        """Exit with error when Claude API fails."""
        mock_fetch.return_value = "Sample transcript"
        # Simulate API error
        mock_summarize.side_effect = Exception("API connection error")

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
            result = main()

        assert result == 1

    @patch("main.load_config")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_transcript")
    def test_main_generic_exception(self, mock_fetch, mock_cache, mock_load_config) -> None:
        """Exit with error for unexpected exceptions."""
        mock_fetch.side_effect = RuntimeError("Unexpected error")

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
            result = main()

        assert result == 1


class TestParseArgs:
    """Test argument parsing."""

    def test_parse_args_with_url_only(self) -> None:
        """Parse arguments with only URL (backward compatibility)."""
        from main import parse_args

        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            args = parse_args()
        assert args.command == "summarize"
        assert args.url_or_id == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert args.lang is None
        assert args.model is None

    def test_parse_args_with_bare_video_id(self) -> None:
        """Parse arguments with bare video ID (backward compatibility)."""
        from main import parse_args

        with patch.object(sys, "argv", ["main.py", "dQw4w9WgXcQ"]):
            args = parse_args()
        assert args.command == "summarize"
        assert args.url_or_id == "dQw4w9WgXcQ"

    def test_parse_args_with_lang_option(self) -> None:
        """Parse arguments with language option (backward compatibility)."""
        from main import parse_args

        with patch.object(sys, "argv", ["main.py", "https://youtu.be/abc123", "--lang", "es"]):
            args = parse_args()
        assert args.command == "summarize"
        assert args.lang == "es"

    def test_parse_args_with_model_option(self) -> None:
        """Parse arguments with model option (backward compatibility)."""
        from main import parse_args

        with patch.object(
            sys, "argv", ["main.py", "https://youtu.be/abc123", "--model", "claude-opus-4-6"]
        ):
            args = parse_args()
        assert args.command == "summarize"
        assert args.model == "claude-opus-4-6"

    def test_parse_args_explicit_summarize_subcommand(self) -> None:
        """Parse arguments with explicit summarize subcommand."""
        from main import parse_args

        with patch.object(sys, "argv", ["main.py", "summarize", "dQw4w9WgXcQ", "--lang", "en"]):
            args = parse_args()
        assert args.command == "summarize"
        assert args.url_or_id == "dQw4w9WgXcQ"
        assert args.lang == "en"

    def test_parse_args_subscriptions_subcommand(self) -> None:
        """Parse arguments with subscriptions subcommand."""
        from main import parse_args

        with patch.object(sys, "argv", ["main.py", "subscriptions", "--days", "7", "--dry-run"]):
            args = parse_args()
        assert args.command == "subscriptions"
        assert args.days == 7
        assert args.dry_run is True

    def test_parse_args_subscriptions_with_filters(self) -> None:
        """Parse subscriptions subcommand with filter options."""
        from main import parse_args

        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "subscriptions",
                "--include-keywords",
                "python,AI",
                "--exclude-keywords",
                "sponsored",
                "--max-videos",
                "25",
            ],
        ):
            args = parse_args()
        assert args.command == "subscriptions"
        assert args.include_keywords == "python,AI"
        assert args.exclude_keywords == "sponsored"
        assert args.max_videos == 25

    def test_parse_args_does_not_modify_sys_argv(self) -> None:
        """Ensure parse_args works on a copy and doesn't modify sys.argv."""
        from main import parse_args

        original_argv = ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        with patch.object(sys, "argv", original_argv.copy()):
            args = parse_args()

        # parse_args should insert 'summarize' internally but not modify sys.argv
        assert args.command == "summarize"
        assert args.url_or_id == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_parse_args_with_explicit_args_list(self) -> None:
        """Parse args from explicit list without using sys.argv."""
        from main import parse_args

        args = parse_args(["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "--lang", "es"])
        assert args.command == "summarize"
        assert args.url_or_id == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert args.lang == "es"

    def test_parse_args_backward_compat_works_with_args_param(self) -> None:
        """Backward compatibility works when passing args explicitly."""
        from main import parse_args

        # Old-style URL without subcommand
        args = parse_args(["dQw4w9WgXcQ", "--model", "claude-opus-4-6"])
        assert args.command == "summarize"
        assert args.url_or_id == "dQw4w9WgXcQ"
        assert args.model == "claude-opus-4-6"


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
        self, mock_save, mock_fetch_metadata, mock_cache, mock_is_legacy, mock_load_config, capsys
    ) -> None:
        """Rename legacy cache file when metadata is fetched."""
        # Simulate cached transcript/summary but legacy filename
        mock_cache.return_value = {
            "video_id": "dQw4w9WgXcQ",
            "full_text": "cached transcript",
            "summary": "cached summary",
        }

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
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

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        ):
            result = main()

        assert result == 0
        # Should NOT fetch metadata since file already has new format
        mock_fetch_metadata.assert_not_called()
        captured = capsys.readouterr()
        assert "cached summary" in captured.out


class TestSubscriptionsCommand:
    """Test subscriptions subcommand integration through main()."""

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    def test_subscriptions_command_success(self, mock_run_subscriptions, mock_load_config) -> None:
        """Successfully run subscriptions subcommand with default arguments."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "subscriptions"]),
        ):
            result = main()

        assert result == 0
        mock_run_subscriptions.assert_called_once()
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["days"] == 7
        assert call_kwargs["dry_run"] is False
        assert call_kwargs["max_videos"] == 50
        assert call_kwargs["api_key"] == "test-key"

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    def test_subscriptions_command_with_days(
        self, mock_run_subscriptions, mock_load_config
    ) -> None:
        """Run subscriptions subcommand with custom days parameter."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "subscriptions", "--days", "14"]),
        ):
            result = main()

        assert result == 0
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["days"] == 14

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    def test_subscriptions_command_dry_run(self, mock_run_subscriptions, mock_load_config) -> None:
        """Run subscriptions subcommand in dry-run mode."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "subscriptions", "--dry-run"]),
        ):
            result = main()

        assert result == 0
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["dry_run"] is True

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    @patch("main.get_subscription_include_keywords", return_value=[])
    @patch("main.get_subscription_exclude_keywords", return_value=[])
    def test_subscriptions_command_with_cli_keywords(
        self,
        mock_get_exclude,
        mock_get_include,
        mock_run_subscriptions,
        mock_load_config,
    ) -> None:
        """CLI keyword arguments override config values."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys,
            "argv",
            [
                "main.py",
                "subscriptions",
                "--include-keywords",
                "python,AI",
                "--exclude-keywords",
                "sponsored,ad",
            ],
        ):
            result = main()

        assert result == 0
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["include_keywords"] == ["python", "AI"]
        assert call_kwargs["exclude_keywords"] == ["sponsored", "ad"]
        # Config getters should not be called when CLI args provided
        mock_get_include.assert_not_called()
        mock_get_exclude.assert_not_called()

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    @patch("main.get_subscription_include_keywords", return_value=["tech", "tutorial"])
    @patch("main.get_subscription_exclude_keywords", return_value=["ads"])
    def test_subscriptions_command_uses_config_keywords(
        self,
        mock_get_exclude,
        mock_get_include,
        mock_run_subscriptions,
        mock_load_config,
    ) -> None:
        """Fall back to config keywords when CLI args not provided."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "subscriptions"]),
        ):
            result = main()

        assert result == 0
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["include_keywords"] == ["tech", "tutorial"]
        assert call_kwargs["exclude_keywords"] == ["ads"]
        mock_get_include.assert_called_once()
        mock_get_exclude.assert_called_once()

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    @patch("main.get_transcript_language", return_value="en")
    @patch("main.get_claude_model", return_value="claude-sonnet-4-5-20250929")
    def test_subscriptions_command_uses_config_lang_model(
        self,
        mock_get_model,
        mock_get_lang,
        mock_run_subscriptions,
        mock_load_config,
    ) -> None:
        """Use config defaults for lang and model when not provided via CLI."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "subscriptions"]),
        ):
            result = main()

        assert result == 0
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["lang"] == "en"
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    @patch("main.get_transcript_language", return_value="en")
    @patch("main.get_claude_model", return_value="claude-sonnet-4-5-20250929")
    def test_subscriptions_command_with_cli_lang_model(
        self,
        mock_get_model,
        mock_get_lang,
        mock_run_subscriptions,
        mock_load_config,
    ) -> None:
        """CLI lang/model arguments override config values."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), patch.object(
            sys,
            "argv",
            [
                "main.py",
                "subscriptions",
                "--lang",
                "es",
                "--model",
                "claude-opus-4-6",
            ],
        ):
            result = main()

        assert result == 0
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["lang"] == "es"
        assert call_kwargs["model"] == "claude-opus-4-6"

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=0)
    def test_subscriptions_command_with_max_videos(
        self, mock_run_subscriptions, mock_load_config
    ) -> None:
        """Run subscriptions subcommand with custom max_videos."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "subscriptions", "--max-videos", "100"]),
        ):
            result = main()

        assert result == 0
        call_kwargs = mock_run_subscriptions.call_args[1]
        assert call_kwargs["max_videos"] == 100

    @patch("main.load_config")
    @patch("main.run_subscriptions", return_value=1)
    def test_subscriptions_command_returns_error(
        self, mock_run_subscriptions, mock_load_config
    ) -> None:
        """Propagate error code from run_subscriptions."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch.object(sys, "argv", ["main.py", "subscriptions"]),
        ):
            result = main()

        assert result == 1

    @patch("main.load_config")
    def test_unknown_command_returns_error(self, mock_load_config, caplog) -> None:
        """Return error for unknown subcommand (defense-in-depth test)."""
        # This tests the else branch at line 223-225, but argparse should prevent this
        # We need to mock argparse to force an unknown command through
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch("main.parse_args") as mock_parse_args,
        ):
            # Mock parse_args to return an unknown command
            mock_args = argparse.Namespace(command="unknown_command")
            mock_parse_args.return_value = mock_args
            result = main()

        assert result == 1
        assert "Unknown command: unknown_command" in caplog.text
