"""
Logging configuration for the diff_merge toolkit.

Provides a pre-configured logger that honours the ``DIFF_MERGE_LOG_LEVEL``
environment variable and can optionally write to a file.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

__all__ = ["get_logger", "setup_logging"]

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(
    level: Optional[str] = None,
    logfile: Optional[str] = None,
) -> logging.Logger:
    """Configure and return the root ``diff_merge`` logger.

    Parameters
    ----------
    level
        Logging level as a string (``"DEBUG"``, ``"INFO"``, …).
        Defaults to the ``DIFF_MERGE_LOG_LEVEL`` env var or ``"WARNING"``.
    logfile
        If given, also write log records to this file.
    """
    global _configured

    if level is None:
        level = os.environ.get("DIFF_MERGE_LOG_LEVEL", "WARNING")

    logger = logging.getLogger("diff_merge")
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))

    if _configured:
        return logger

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    logger.addHandler(handler)

    if logfile:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(fh)

    _configured = True
    return logger


def get_logger(name: str = "diff_merge") -> logging.Logger:
    """Return a child logger under the ``diff_merge`` namespace.

    If *name* does not start with ``"diff_merge"``, it is prefixed
    automatically (e.g. ``"test"`` → ``"diff_merge.test"``).
    """
    setup_logging()
    if not name.startswith("diff_merge"):
        name = f"diff_merge.{name}"
    return logging.getLogger(name)