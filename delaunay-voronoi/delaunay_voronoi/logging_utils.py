"""
Structured logging for the delaunay-voronoi toolkit.

Provides a pre-configured logger that respects the ``LOG_LEVEL``
environment variable and the :class:`Config.log_level` setting.
Use :func:`get_logger` to obtain a module-level logger.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

_LOGGER_NAME = "delaunay_voronoi"
_configured: bool = False


def configure_logging(level: str = "INFO",
                      stream=None,
                      fmt: Optional[str] = None) -> logging.Logger:
    """Configure the package logger.

    Parameters
    ----------
    level : logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    stream : output stream (defaults to stderr).
    fmt : custom format string.
    """
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    if stream is None:
        stream = sys.stderr
    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    _configured = True
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger under the package namespace.

    Respects ``LOG_LEVEL`` env var if set.
    """
    global _configured
    if not _configured:
        level = os.environ.get("LOG_LEVEL", "INFO")
        configure_logging(level)
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)