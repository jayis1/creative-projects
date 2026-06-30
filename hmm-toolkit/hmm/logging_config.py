"""Logging configuration for hmm-toolkit.

Provides a standard logger and a helper to configure it from a config
dict or verbosity flag.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOGGER_NAME = "hmm_toolkit"
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Return the package-wide logger (lazily configured)."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(_LOGGER_NAME)
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            _logger.addHandler(handler)
            _logger.setLevel(logging.WARNING)
    return _logger


def configure_logging(level: str = "WARNING", filepath: Optional[str] = None) -> None:
    """Configure the logger.

    Parameters
    ----------
    level : str
        One of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
    filepath : str, optional
        If given, also write logs to this file.
    """
    logger = get_logger()
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))
    if filepath:
        fh = logging.FileHandler(filepath)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(fh)