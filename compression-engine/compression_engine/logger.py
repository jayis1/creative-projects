"""Structured logging for the compression engine.

Provides a configured logger with consistent formatting and optional
file output for debugging compression operations.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

_LOGGER_NAME = "compression_engine"

# Module-level logger
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get the compression engine logger.

    Returns:
        Configured logger instance.
    """
    global _logger
    if _logger is None:
        _logger = logging.getLogger(_LOGGER_NAME)
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            _logger.addHandler(handler)
            _logger.setLevel(logging.WARNING)
    return _logger


def configure_logging(
    level: str = "WARNING",
    format_str: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """Configure the compression engine logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format_str: Custom format string for log messages.
        filename: Optional file path for log output.
    """
    logger = get_logger()
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))

    # Clear existing handlers
    logger.handlers.clear()

    fmt = format_str or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    if filename:
        handler = logging.FileHandler(filename)
    else:
        handler = logging.StreamHandler(sys.stderr)

    handler.setFormatter(formatter)
    logger.addHandler(handler)