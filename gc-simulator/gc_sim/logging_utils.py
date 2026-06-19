"""Structured logging utilities for the GC simulator.

Provides a lightweight logging configuration that can be toggled on/off
and routed to stderr or a file.  Collectors emit log messages at key
points (start of mark, sweep, compact, promote) so that runs can be traced.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

_LOGGER_NAME = "gc_sim"
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Return the package logger, creating it lazily."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(_LOGGER_NAME)
        _logger.setLevel(logging.WARNING)
        _logger.addHandler(logging.NullHandler())
    return _logger


def configure_logging(level: str = "WARNING",
                       logfile: Optional[str] = None,
                       fmt: Optional[str] = None) -> None:
    """Configure the package logger.

    Parameters
    ----------
    level : str
        Logging level: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``.
    logfile : str, optional
        Path to a log file.  If ``None``, logs go to stderr.
    fmt : str, optional
        Custom log format string.
    """
    logger = get_logger()
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))
    # remove existing handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)
    if logfile:
        handler: logging.Handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stderr)
    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.propagate = False


def log_debug(msg: str, *args) -> None:
    get_logger().debug(msg, *args)


def log_info(msg: str, *args) -> None:
    get_logger().info(msg, *args)


def log_warning(msg: str, *args) -> None:
    get_logger().warning(msg, *args)


def log_error(msg: str, *args) -> None:
    get_logger().error(msg, *args)