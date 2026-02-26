"""Configuration management for the application."""

import os
from pathlib import Path

from dotenv import load_dotenv


def load_config() -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Try loading from the script's directory
        script_dir = Path(__file__).parent
        env_file = script_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)


def get_transcript_language() -> str:
    """Get the transcript language preference from environment, with default fallback."""
    return os.getenv("TRANSCRIPT_LANGUAGE", "en")


def get_obsidian_vault_path() -> Path:
    """Get the Obsidian vault path from environment, with fallback to cache/ directory.

    Returns:
        Path: The directory path for storing markdown cache files

    Raises:
        ValueError: If the specified path doesn't exist or isn't writable
    """
    vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH")

    if vault_path_str:
        # User specified a custom vault path
        vault_path = Path(vault_path_str).expanduser().resolve()

        # Validate path exists
        if not vault_path.exists():
            raise ValueError(
                f"Obsidian vault path does not exist: {vault_path}\n"
                "Please create the directory or update OBSIDIAN_VAULT_PATH in .env"
            )

        # Validate path is a directory
        if not vault_path.is_dir():
            raise ValueError(
                f"Obsidian vault path is not a directory: {vault_path}\n"
                "Please specify a valid directory path in OBSIDIAN_VAULT_PATH"
            )

        # Validate path is writable
        if not os.access(vault_path, os.W_OK):
            raise ValueError(
                f"Obsidian vault path is not writable: {vault_path}\n"
                "Please check directory permissions"
            )

        return vault_path
    else:
        # Fall back to current working directory
        return Path.cwd()
