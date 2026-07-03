"""Structured logging for graph-layout operations.

Provides a thin wrapper around the stdlib ``logging`` module with sensible
defaults: timestamps, level names, and optional file output.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(level: str = "INFO",
                 logfile: Optional[str] = None,
                 fmt: str = _LOG_FORMAT) -> logging.Logger:
    """Configure and return the package logger.

    Args:
        level: logging level name (DEBUG, INFO, WARNING, ERROR).
        logfile: optional file path for log output.
        fmt: log message format string.
    """
    global _configured
    logger = logging.getLogger("graph_layout")
    if _configured:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler: logging.Handler
    if logfile:
        handler = logging.FileHandler(logfile, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt, datefmt=_DATE_FORMAT))
    logger.addHandler(handler)
    _configured = True
    return logger


def get_logger(name: str = "graph_layout") -> logging.Logger:
    """Return a child logger under the graph_layout namespace."""
    return logging.getLogger(name)


__all__ = ["setup_logging", "get_logger"]