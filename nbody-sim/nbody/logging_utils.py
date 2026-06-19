"""Structured logging utilities for nbody-sim.

Provides a pre-configured logger with sensible defaults, a compact
formatter, and convenience functions so callers don't need to set up
``logging.basicConfig`` every time.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

# Module-level logger — configured once, used everywhere.
_logger: Optional[logging.Logger] = None


class _CompactFormatter(logging.Formatter):
    """One-line formatter: LEVEL [time] message."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(levelname)s [%(asctime)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )


def get_logger(name: str = "nbody") -> logging.Logger:
    """Return the configured nbody logger.

    The first call configures the handler and format; subsequent calls
    return the same logger.
    """
    global _logger
    if _logger is not None:
        child = logging.getLogger(name)
        if not child.handlers and _logger.handlers:
            child.handlers = _logger.handlers
            child.level = _logger.level
        return child
    _logger = logging.getLogger("nbody")
    _logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_CompactFormatter())
    _logger.addHandler(handler)
    _logger.propagate = False
    return _logger


def set_level(level: int | str) -> None:
    """Set the logging level (e.g. logging.DEBUG)."""
    logger = get_logger()
    logger.setLevel(level)
    for h in logger.handlers:
        h.setLevel(level)


__all__ = ["get_logger", "set_level"]