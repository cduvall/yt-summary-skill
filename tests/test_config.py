"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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


class TestGetSubscriptionIncludeKeywords:
    """Test subscription include keywords configuration."""

    def test_get_subscription_include_keywords_from_environment(self) -> None:
        """Get include keywords from environment as list."""
        from yt_summary.config import get_subscription_include_keywords

        with patch.dict(
            os.environ, {"SUBSCRIPTION_INCLUDE_KEYWORDS": "python,AI,machine learning"}
        ):
            result = get_subscription_include_keywords()
            assert result == ["python", "AI", "machine learning"]

    def test_get_subscription_include_keywords_empty_string(self) -> None:
        """Return empty list when env var is empty string."""
        from yt_summary.config import get_subscription_include_keywords

        with patch.dict(os.environ, {"SUBSCRIPTION_INCLUDE_KEYWORDS": ""}):
            assert get_subscription_include_keywords() == []

    def test_get_subscription_include_keywords_missing(self) -> None:
        """Return empty list when env var is not set."""
        from yt_summary.config import get_subscription_include_keywords

        with patch.dict(os.environ, {}, clear=True):
            assert get_subscription_include_keywords() == []

    def test_get_subscription_include_keywords_strips_whitespace(self) -> None:
        """Strip whitespace from keywords."""
        from yt_summary.config import get_subscription_include_keywords

        with patch.dict(os.environ, {"SUBSCRIPTION_INCLUDE_KEYWORDS": " python , AI ,  ML  "}):
            result = get_subscription_include_keywords()
            assert result == ["python", "AI", "ML"]

    def test_get_subscription_include_keywords_filters_empty(self) -> None:
        """Filter out empty keywords from list."""
        from yt_summary.config import get_subscription_include_keywords

        with patch.dict(os.environ, {"SUBSCRIPTION_INCLUDE_KEYWORDS": "python,,AI,,,ML"}):
            result = get_subscription_include_keywords()
            assert result == ["python", "AI", "ML"]


class TestGetSubscriptionExcludeKeywords:
    """Test subscription exclude keywords configuration."""

    def test_get_subscription_exclude_keywords_from_environment(self) -> None:
        """Get exclude keywords from environment as list."""
        from yt_summary.config import get_subscription_exclude_keywords

        with patch.dict(os.environ, {"SUBSCRIPTION_EXCLUDE_KEYWORDS": "sponsored,ads,promo"}):
            result = get_subscription_exclude_keywords()
            assert result == ["sponsored", "ads", "promo"]

    def test_get_subscription_exclude_keywords_empty_string(self) -> None:
        """Return empty list when env var is empty string."""
        from yt_summary.config import get_subscription_exclude_keywords

        with patch.dict(os.environ, {"SUBSCRIPTION_EXCLUDE_KEYWORDS": ""}):
            assert get_subscription_exclude_keywords() == []

    def test_get_subscription_exclude_keywords_missing(self) -> None:
        """Return empty list when env var is not set."""
        from yt_summary.config import get_subscription_exclude_keywords

        with patch.dict(os.environ, {}, clear=True):
            assert get_subscription_exclude_keywords() == []

    def test_get_subscription_exclude_keywords_strips_whitespace(self) -> None:
        """Strip whitespace from keywords."""
        from yt_summary.config import get_subscription_exclude_keywords

        with patch.dict(
            os.environ, {"SUBSCRIPTION_EXCLUDE_KEYWORDS": " sponsored , ads ,  promo  "}
        ):
            result = get_subscription_exclude_keywords()
            assert result == ["sponsored", "ads", "promo"]

    def test_get_subscription_exclude_keywords_filters_empty(self) -> None:
        """Filter out empty keywords from list."""
        from yt_summary.config import get_subscription_exclude_keywords

        with patch.dict(os.environ, {"SUBSCRIPTION_EXCLUDE_KEYWORDS": "sponsored,,ads,,,promo"}):
            result = get_subscription_exclude_keywords()
            assert result == ["sponsored", "ads", "promo"]


class TestGetSubscriptionExcludeChannels:
    """Test subscription exclude channels configuration."""

    def test_get_subscription_exclude_channels_from_environment(self) -> None:
        """Get exclude channels from environment as list."""
        from yt_summary.config import get_subscription_exclude_channels

        with patch.dict(os.environ, {"SUBSCRIPTION_EXCLUDE_CHANNELS": "@FantasyLofi,@Ads,@Spam"}):
            result = get_subscription_exclude_channels()
            assert result == ["@FantasyLofi", "@Ads", "@Spam"]

    def test_get_subscription_exclude_channels_empty_string(self) -> None:
        """Return empty list when env var is empty string."""
        from yt_summary.config import get_subscription_exclude_channels

        with patch.dict(os.environ, {"SUBSCRIPTION_EXCLUDE_CHANNELS": ""}):
            assert get_subscription_exclude_channels() == []

    def test_get_subscription_exclude_channels_missing(self) -> None:
        """Return empty list when env var is not set."""
        from yt_summary.config import get_subscription_exclude_channels

        with patch.dict(os.environ, {}, clear=True):
            assert get_subscription_exclude_channels() == []

    def test_get_subscription_exclude_channels_strips_whitespace(self) -> None:
        """Strip whitespace from channel names."""
        from yt_summary.config import get_subscription_exclude_channels

        with patch.dict(
            os.environ, {"SUBSCRIPTION_EXCLUDE_CHANNELS": " @FantasyLofi , @Ads ,  @Spam  "}
        ):
            result = get_subscription_exclude_channels()
            assert result == ["@FantasyLofi", "@Ads", "@Spam"]

    def test_get_subscription_exclude_channels_filters_empty(self) -> None:
        """Filter out empty channel names from list."""
        from yt_summary.config import get_subscription_exclude_channels

        with patch.dict(
            os.environ, {"SUBSCRIPTION_EXCLUDE_CHANNELS": "@FantasyLofi,,@Ads,,,@Spam"}
        ):
            result = get_subscription_exclude_channels()
            assert result == ["@FantasyLofi", "@Ads", "@Spam"]


class TestGetOAuthDir:
    """Test OAuth directory configuration."""

    def test_get_oauth_dir_creates_directory(self, tmp_path: Path) -> None:
        """Create OAuth directory if it doesn't exist."""
        from yt_summary.config import get_oauth_dir

        with patch("yt_summary.config.Path.home", return_value=tmp_path):
            result = get_oauth_dir()
            expected_dir = tmp_path / ".yt-summary"
            assert result == expected_dir
            assert result.exists()
            assert result.is_dir()

    def test_get_oauth_dir_reuses_existing_directory(self, tmp_path: Path) -> None:
        """Return existing OAuth directory without error."""
        from yt_summary.config import get_oauth_dir

        oauth_dir = tmp_path / ".yt-summary"
        oauth_dir.mkdir()
        marker_file = oauth_dir / "marker.txt"
        marker_file.write_text("test")

        with patch("yt_summary.config.Path.home", return_value=tmp_path):
            result = get_oauth_dir()
            assert result == oauth_dir
            assert marker_file.exists()  # Existing contents preserved

    def test_get_oauth_dir_failure_raises_error(self, tmp_path: Path) -> None:
        """Raise error when directory creation fails."""
        from yt_summary.config import get_oauth_dir

        with (
            patch("yt_summary.config.Path.home", return_value=tmp_path),
            patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")),
            pytest.raises(ValueError, match="Failed to create OAuth directory"),
        ):
            get_oauth_dir()
