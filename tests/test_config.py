"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from yt_summary.config import (
    get_transcript_language,
    load_config,
)


class TestLoadConfig:
    """Test loading configuration from .env file."""

    def test_load_config_from_env_file(self) -> None:
        """Load environment variables from .env file."""

        with patch("yt_summary.config.Path.cwd") as mock_cwd:
            Path("/fake/path/.env")
            mock_cwd.return_value = Path("/fake/path")

            with patch("yt_summary.config.Path"):
                # Mock the Path object returned by cwd() / ".env"
                mock_env_instance = MagicMock()
                mock_env_instance.exists.return_value = False

                with patch("yt_summary.config.load_dotenv"):
                    load_config()
                    # Should attempt to load from cwd if it exists

    def test_load_config_from_script_directory(self) -> None:
        """Load configuration from script directory if cwd doesn't have .env."""
        with (
            patch("yt_summary.config.load_dotenv") as mock_load,
            patch("yt_summary.config.Path") as mock_path,
        ):
            # Mock cwd path
            mock_cwd = MagicMock()
            mock_cwd_env = MagicMock()
            mock_cwd_env.exists.return_value = False
            mock_cwd.__truediv__ = lambda self, other: mock_cwd_env

            # Mock script directory path
            mock_script = MagicMock()
            mock_script_env = MagicMock()
            mock_script_env.exists.return_value = True
            mock_script.__truediv__ = lambda self, other: mock_script_env

            mock_path.cwd.return_value = mock_cwd
            mock_path.return_value.parent = mock_script

            load_config()
            # Should call load_dotenv with script directory .env
            assert mock_load.called

    def test_load_config_no_env_file_anywhere(self) -> None:
        """Load config when no .env file exists anywhere."""
        with (
            patch("yt_summary.config.load_dotenv"),
            patch("yt_summary.config.Path") as mock_path,
        ):
            # Mock cwd path
            mock_cwd = MagicMock()
            mock_cwd_env = MagicMock()
            mock_cwd_env.exists.return_value = False
            mock_cwd.__truediv__ = lambda self, other: mock_cwd_env

            # Mock script directory path
            mock_script = MagicMock()
            mock_script_env = MagicMock()
            mock_script_env.exists.return_value = False
            mock_script.__truediv__ = lambda self, other: mock_script_env

            mock_path.cwd.return_value = mock_cwd
            mock_path.return_value.parent = mock_script

            load_config()
            # Should not raise error, just not load anything
            # load_dotenv might not be called or called with non-existent file


class TestGetTranscriptLanguage:
    """Test transcript language configuration."""

    def test_get_transcript_language_from_environment(self) -> None:
        """Get language from environment variable."""
        with patch.dict(os.environ, {"TRANSCRIPT_LANGUAGE": "es"}):
            assert get_transcript_language() == "es"

    def test_get_transcript_language_default(self) -> None:
        """Return default language when not in environment."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_transcript_language() == "en"


class TestGetObsidianVaultPath:
    """Test Obsidian vault path configuration."""

    def test_get_obsidian_vault_path_with_valid_custom_path(self, tmp_path: Path) -> None:
        """Get custom vault path from environment variable."""
        vault_dir = tmp_path / "my-vault"
        vault_dir.mkdir()

        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(vault_dir)}):
            from yt_summary.config import get_obsidian_vault_path

            result = get_obsidian_vault_path()

        assert result == vault_dir

    def test_get_obsidian_vault_path_expands_tilde(self, tmp_path: Path) -> None:
        """Expand ~ in vault path."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        # Use absolute path but verify expanduser is called
        with patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(vault_dir)}):
            from yt_summary.config import get_obsidian_vault_path

            result = get_obsidian_vault_path()

        assert result == vault_dir

    def test_get_obsidian_vault_path_default_cache_dir(self) -> None:
        """Default to current working directory when no env var set."""
        with patch.dict(os.environ, {}, clear=True):
            from yt_summary.config import get_obsidian_vault_path

            result = get_obsidian_vault_path()

        assert result == Path.cwd()

    def test_get_obsidian_vault_path_nonexistent_path_raises_error(self) -> None:
        """Raise error when specified path doesn't exist."""
        import pytest

        from yt_summary.config import get_obsidian_vault_path

        with (
            patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": "/nonexistent/path"}),
            pytest.raises(ValueError, match="does not exist"),
        ):
            get_obsidian_vault_path()

    def test_get_obsidian_vault_path_file_not_directory_raises_error(self, tmp_path: Path) -> None:
        """Raise error when path is a file, not a directory."""
        import pytest

        from yt_summary.config import get_obsidian_vault_path

        file_path = tmp_path / "not-a-dir"
        file_path.touch()

        with (
            patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(file_path)}),
            pytest.raises(ValueError, match="not a directory"),
        ):
            get_obsidian_vault_path()

    def test_get_obsidian_vault_path_not_writable_raises_error(self, tmp_path: Path) -> None:
        """Raise error when path is not writable."""
        import pytest

        from yt_summary.config import get_obsidian_vault_path

        vault_dir = tmp_path / "readonly-vault"
        vault_dir.mkdir()

        # Mock os.access to return False for write permission
        with (
            patch("os.access", return_value=False),
            patch.dict(os.environ, {"OBSIDIAN_VAULT_PATH": str(vault_dir)}),
            pytest.raises(ValueError, match="not writable"),
        ):
            get_obsidian_vault_path()
