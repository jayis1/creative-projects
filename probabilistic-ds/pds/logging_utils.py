"""Structured logging utilities for the probabilistic-ds toolkit.

Provides a pre-configured logger and helper functions so that structures
can emit diagnostics (insertions, evictions, capacity warnings, etc.) in
a consistent, filterable format.

Usage::

    from pds.logging import get_logger, set_level
    log = get_logger("pds.bloom")
    log.info("Inserted %d items, current FPR %.4f", bf.count, fpr)
    set_level("DEBUG")  # or set_level(logging.DEBUG)
"""
from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
_initialized = False


def _ensure_init():
    """Initialize the root pds logger once."""
    global _initialized
    if _initialized:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger("pds")
    root.addHandler(handler)
    root.setLevel(logging.WARNING)  # default: warnings and above
    root.propagate = False
    _initialized = True


def get_logger(name: str = "pds") -> logging.Logger:
    """Get a logger under the ``pds`` namespace.

    Parameters
    ----------
    name : str
        Sub-logger name (appended to 'pds.', e.g. 'pds.bloom').
        If it already starts with 'pds', it is used as-is.
    """
    _ensure_init()
    if not name.startswith("pds"):
        name = f"pds.{name}"
    return logging.getLogger(name)


def set_level(level) -> None:
    """Set the logging level for all pds loggers.

    Parameters
    ----------
    level : int or str
        A logging level (e.g. ``logging.DEBUG``) or its string name
        (``'DEBUG'``, ``'INFO'``, ``'WARNING'``, etc.).
    """
    _ensure_init()
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logging.getLogger("pds").setLevel(level)


def disable() -> None:
    """Disable all pds logging (set level to CRITICAL + 1)."""
    _ensure_init()
    logging.getLogger("pds").setLevel(logging.CRITICAL + 1)