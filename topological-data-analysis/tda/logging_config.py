"""
Logging configuration for the TDA toolkit.

Provides :func:`get_logger` which returns a named logger that respects
the ``TDA_LOG_LEVEL`` environment variable and an optional verbose flag.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

_LOGGER_CACHE: dict[str, logging.Logger] = {}
_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def get_logger(name: str = "tda",
               level: Optional[str] = None,
               verbose: bool = False) -> logging.Logger:
    """Return (and cache) a configured logger.

    Parameters
    ----------
    name : str
        Logger name (dotted).
    level : str, optional
        Logging level name (``DEBUG``, ``INFO``, …). If ``None``, falls
        back to the ``TDA_LOG_LEVEL`` environment variable, then to
        ``DEBUG`` if *verbose* is True, otherwise ``WARNING``.
    verbose : bool
        If True and *level* is None, use ``DEBUG``.
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    if level is None:
        level = os.environ.get("TDA_LOG_LEVEL",
                               "DEBUG" if verbose else "WARNING")
    numeric = getattr(logging, level.upper(), logging.WARNING)

    logger = logging.getLogger(name)
    logger.setLevel(numeric)

    # Avoid duplicate handlers on repeated import.
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        logger.addHandler(handler)
    logger.propagate = False

    _LOGGER_CACHE[name] = logger
    return logger