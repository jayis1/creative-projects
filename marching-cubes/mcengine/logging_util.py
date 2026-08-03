"""Logging utilities for mcengine.

Provides a configured logger that can be used across all modules with
consistent formatting.  Supports both console and file logging.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOGGER_NAME = "mcengine"
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get the shared mcengine logger instance."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(_LOGGER_NAME)
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            _logger.addHandler(handler)
            _logger.setLevel(logging.WARNING)
    return _logger


def set_log_level(level) -> None:
    """Set the log level. Accepts a string ('DEBUG', 'INFO', etc.) or int."""
    logger = get_logger()
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logger.setLevel(level)


def add_file_handler(path: str, level=None) -> None:
    """Add a file handler to the logger."""
    logger = get_logger()
    fh = logging.FileHandler(path)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    )
    if level is not None:
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        fh.setLevel(level)
    logger.addHandler(fh)


def log_progress(current: int, total: int, message: str = "", interval: int = 1000) -> None:
    """Log a progress message at DEBUG level if interval is reached."""
    logger = get_logger()
    if logger.isEnabledFor(logging.DEBUG) and current % interval == 0:
        pct = 100.0 * current / total if total > 0 else 0.0
        logger.debug(f"Progress: {current}/{total} ({pct:.1f}%) {message}")