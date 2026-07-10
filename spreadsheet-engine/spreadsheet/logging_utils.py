"""
Logging utilities for the spreadsheet engine.

Provides a configurable logger with sensible defaults and helper functions
for structured logging of recalculation, auditing, and error events.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

_LOGGER_NAME = "spreadsheet"

_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Return the shared spreadsheet logger, creating it on first call."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(_LOGGER_NAME)
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            _logger.addHandler(handler)
            _logger.setLevel(logging.WARNING)
    return _logger


def set_level(level: int | str) -> None:
    """Set the logging level (e.g. logging.DEBUG or 'DEBUG')."""
    logger = get_logger()
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(level)


def configure(verbose: bool = False, quiet: bool = False) -> None:
    """Convenience: configure verbosity based on --verbose / --quiet flags."""
    if quiet:
        set_level(logging.CRITICAL)
    elif verbose:
        set_level(logging.DEBUG)
    else:
        set_level(logging.INFO)


def debug(msg: str, *args) -> None:
    get_logger().debug(msg, *args)


def info(msg: str, *args) -> None:
    get_logger().info(msg, *args)


def warning(msg: str, *args) -> None:
    get_logger().warning(msg, *args)


def error(msg: str, *args) -> None:
    get_logger().error(msg, *args)