"""Structured logging configuration for Cloud Run and CLI environments."""

import json
import logging
import os
import sys


class CloudJsonFormatter(logging.Formatter):
    """
    JSON formatter for Cloud Logging compatibility.

    Outputs log records as structured JSON with a 'severity' field that Cloud
    Logging recognizes. Maps Python log levels to Cloud Logging severity levels.
    """

    # Map Python log levels to Cloud Logging severity levels
    SEVERITY_MAP = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON with severity field."""
        severity = self.SEVERITY_MAP.get(record.levelno, "INFO")

        log_obj = {
            "severity": severity,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging() -> None:
    """
    Configure root logger for structured logging.

    Uses JSON formatter when LOG_FORMAT=json (Cloud Run), otherwise uses
    human-readable format for CLI. All log output goes to stderr.

    This function is idempotent and safe to call multiple times.
    """
    log_format = os.getenv("LOG_FORMAT", "text")
    root_logger = logging.getLogger()

    # Skip if already configured
    if root_logger.handlers:
        return

    # Set log level
    root_logger.setLevel(logging.INFO)

    # Create stderr handler
    handler = logging.StreamHandler(sys.stderr)

    # Choose formatter based on environment
    if log_format == "json":
        handler.setFormatter(CloudJsonFormatter())
    else:
        # Human-readable format for CLI
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)
