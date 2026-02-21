"""Logging configuration for CLI environments."""

import logging
import sys


def setup_logging() -> None:
    """
    Configure root logger for CLI output.

    Uses human-readable format. All log output goes to stderr.

    This function is idempotent and safe to call multiple times.
    """
    root_logger = logging.getLogger()

    # Skip if already configured
    if root_logger.handlers:
        return

    # Set log level
    root_logger.setLevel(logging.INFO)

    # Create stderr handler with human-readable format
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
