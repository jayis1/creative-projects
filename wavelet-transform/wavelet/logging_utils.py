"""
Structured logging for the wavelet-transform toolkit.

Provides a pre-configured logger that writes to stderr with configurable
verbosity.  All modules use ``get_logger()`` to obtain a logger so the
verbosity can be controlled centrally.
"""

from __future__ import annotations

import logging
import sys

__all__ = ["get_logger", "set_log_level", "set_verbose"]

_LOGGER_NAME = "wavelet"
_initialized = False


def _init_logger() -> logging.Logger:
    """Create and configure the package logger (called once)."""
    global _initialized
    logger = logging.getLogger(_LOGGER_NAME)
    if _initialized:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    _initialized = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger for the wavelet package.

    If ``name`` is given, returns a child logger (e.g. ``wavelet.dwt``).
    """
    _init_logger()
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def set_log_level(level: int | str) -> None:
    """Set the log level for the wavelet package.

    Accepts either an integer (e.g. logging.DEBUG) or a string
    (e.g. "DEBUG", "INFO", "WARNING").
    """
    logger = _init_logger()
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logger.setLevel(level)


def set_verbose(verbose: bool = True) -> None:
    """Enable or disable verbose (DEBUG-level) logging."""
    set_log_level(logging.DEBUG if verbose else logging.WARNING)