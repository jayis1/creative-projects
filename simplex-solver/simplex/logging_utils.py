"""Structured logging utilities for simplex-solver.

Provides a lightweight, stdlib-only logging configuration helper that is
used across the solver, CLI, and analysis modules.  Logging is opt-in —
the solver itself does *not* emit log records unless a handler is configured.
"""

from __future__ import annotations

import logging
import sys
from typing import TextIO

__all__ = ["get_logger", "configure_logging", "SOLVER_LOGGER"]

SOLVER_LOGGER = "simplex"


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger under the ``simplex`` namespace."""
    if name is None:
        return logging.getLogger(SOLVER_LOGGER)
    if name.startswith(SOLVER_LOGGER):
        return logging.getLogger(name)
    return logging.getLogger(f"{SOLVER_LOGGER}.{name}")


def configure_logging(
    level: str | int = "WARNING",
    *,
    stream: TextIO | None = None,
    fmt: str | None = None,
    datefmt: str = "%Y-%m-%d %H:%M:%S",
) -> logging.Logger:
    """Configure the root ``simplex`` logger and return it.

    Parameters
    ----------
    level : str | int
        Logging level — ``"DEBUG"``, ``"INFO"``, ``"WARNING"`` (default),
        ``"ERROR"``, ``"CRITICAL"``, or the corresponding integer.
    stream : file-like, optional
        Output stream (default: ``sys.stderr``).
    fmt : str, optional
        Custom log format.  Default:
        ``"%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"``.
    datefmt : str
        Date format string.
    """
    if isinstance(level, str):
        level = level.upper()
    logger = logging.getLogger(SOLVER_LOGGER)
    logger.setLevel(level)
    # Remove existing handlers to avoid duplicate output on re-config.
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt or "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
            datefmt=datefmt,
        )
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger