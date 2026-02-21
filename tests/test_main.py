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


class TestMainPlaylistRouting:
    """Test that main() routes playlist URLs and IDs to process_playlist."""

    @patch("main.load_config")
    @patch("main.process_playlist", return_value=0)
    @patch("main.is_playlist_url", return_value=True)
    def test_playlist_url_routes_to_process_playlist(
        self, mock_is_url, mock_process, mock_load_config
    ) -> None:
        with patch.object(
            sys,
            "argv",
            ["main.py", "https://www.youtube.com/playlist?list=PLddiDRMhpXFL"],
        ):
            result = main()

        assert result == 0
        mock_process.assert_called_once()

    @patch("main.load_config")
    @patch("main.process_playlist", return_value=0)
    @patch("main.is_playlist_url", return_value=False)
    @patch("main.is_playlist_id", return_value=True)
    def test_playlist_id_routes_to_process_playlist(
        self, mock_is_id, mock_is_url, mock_process, mock_load_config
    ) -> None:
        with patch.object(sys, "argv", ["main.py", "PLddiDRMhpXFLnSXGVRYBRfZalDCKkiqME"]):
            result = main()

        assert result == 0
        mock_process.assert_called_once()

    @patch("main.load_config")
    @patch("main.summarize_video", return_value=0)
    @patch("main.is_playlist_url", return_value=False)
    @patch("main.is_playlist_id", return_value=False)
    def test_non_playlist_falls_through_to_summarize_video(
        self, mock_is_id, mock_is_url, mock_summarize, mock_load_config
    ) -> None:
        with patch.object(sys, "argv", ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]):
            result = main()

        assert result == 0
        mock_summarize.assert_called_once()


class TestProcessPlaylist:
    """Test process_playlist() function."""

    def _make_playlist_info(self, video_ids: list):
        from yt_summary.playlist import PlaylistInfo

        return PlaylistInfo(
            playlist_id="PLddiDRMhpXFL",
            playlist_title="Test Playlist",
            video_ids=video_ids,
        )

    @patch("main.load_config")
    @patch("main.fetch_playlist_info")
    @patch("main.load_cache")
    def test_process_playlist_skips_cached_videos(
        self, mock_cache, mock_fetch_info, mock_load_config
    ) -> None:
        from main import process_playlist

        mock_fetch_info.return_value = self._make_playlist_info(["vid11111111"])
        mock_cache.return_value = {"full_text": "already cached", "title": "T", "channel": "C"}

        result = process_playlist("https://www.youtube.com/playlist?list=PLddiDRMhpXFL", None)

        assert result == 0

    @patch("main.load_config")
    @patch("main.fetch_playlist_info")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_video_metadata", side_effect=Exception("meta fail"))
    @patch("main.fetch_transcript", side_effect=Exception("transcript fail"))
    def test_process_playlist_all_failures_returns_1(
        self, mock_transcript, mock_meta, mock_cache, mock_fetch_info, mock_load_config
    ) -> None:
        from main import process_playlist

        mock_fetch_info.return_value = self._make_playlist_info(["vid11111111"])

        result = process_playlist("https://www.youtube.com/playlist?list=PLddiDRMhpXFL", None)

        assert result == 1

    @patch("main.load_config")
    @patch("main.fetch_playlist_info")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_video_metadata", return_value={"title": "Title A", "channel": "Chan"})
    @patch("main.fetch_transcript", return_value="Transcript text")
    @patch("main.save_to_cache")
    def test_process_playlist_all_success_returns_0(
        self,
        mock_save,
        mock_transcript,
        mock_meta,
        mock_cache,
        mock_fetch_info,
        mock_load_config,
    ) -> None:
        from main import process_playlist

        mock_fetch_info.return_value = self._make_playlist_info(["vid11111111", "vid22222222"])

        result = process_playlist("https://www.youtube.com/playlist?list=PLddiDRMhpXFL", None)

        assert result == 0
        assert mock_save.call_count == 2

    @patch("main.load_config")
    @patch("main.fetch_playlist_info")
    @patch("main.load_cache", return_value=None)
    @patch("main.fetch_video_metadata", return_value={"title": "Title A", "channel": "Chan"})
    @patch("main.fetch_transcript")
    @patch("main.save_to_cache")
    def test_process_playlist_mixed_success_failure_returns_0(
        self,
        mock_save,
        mock_transcript,
        mock_meta,
        mock_cache,
        mock_fetch_info,
        mock_load_config,
    ) -> None:
        from main import process_playlist
        from yt_summary.transcript import TranscriptError

        mock_fetch_info.return_value = self._make_playlist_info(["vid11111111", "vid22222222"])
        # First video succeeds, second fails
        mock_transcript.side_effect = ["Transcript text", TranscriptError("No captions")]

        result = process_playlist("https://www.youtube.com/playlist?list=PLddiDRMhpXFL", None)

        assert result == 0
        assert mock_save.call_count == 1

    @patch("main.load_config")
    @patch("main.fetch_playlist_info")
    def test_process_playlist_fetch_error_returns_1(
        self, mock_fetch_info, mock_load_config
    ) -> None:
        from main import process_playlist
        from yt_summary.playlist import PlaylistError

        mock_fetch_info.side_effect = PlaylistError("Could not fetch", playlist_id="PLxxx")

        result = process_playlist("PLddiDRMhpXFLnSXGVRYBRfZalDCKkiqME", None)

        assert result == 1

    @patch("main.load_config")
    @patch("main.fetch_playlist_info")
    def test_process_playlist_saves_playlist_metadata(
        self, mock_fetch_info, mock_load_config
    ) -> None:
        from unittest.mock import patch as _patch

        from main import process_playlist

        mock_fetch_info.return_value = self._make_playlist_info(["vid11111111"])

        with (
            _patch("main.load_cache", return_value=None),
            _patch(
                "main.fetch_video_metadata",
                return_value={"title": "Video Title", "channel": "My Channel"},
            ),
            _patch("main.fetch_transcript", return_value="Full transcript"),
            _patch("main.save_to_cache") as mock_save,
        ):
            result = process_playlist("https://www.youtube.com/playlist?list=PLddiDRMhpXFL", None)

        assert result == 0
        _, kwargs = mock_save.call_args
        assert kwargs.get("playlist_id") == "PLddiDRMhpXFL"
        assert kwargs.get("playlist_title") == "Test Playlist"
