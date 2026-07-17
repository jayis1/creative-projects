"""Lightweight structured logging for the orbital-mechanics library.

Uses the standard ``logging`` module with a custom formatter that
emits timestamps and module names.  Also provides a context manager
for timing code blocks.
"""
from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Generator

_LOGGER_NAME = "orbital"
_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the package logger, configuring it on first use."""
    global _configured
    logger = logging.getLogger(name or _LOGGER_NAME)
    if not _configured:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        _configured = True
    return logger


def set_log_level(level: int | str) -> None:
    """Set the logging level (e.g. ``logging.DEBUG`` or 'DEBUG')."""
    get_logger().setLevel(level)


@contextmanager
def timed(label: str, logger: logging.Logger | None = None) -> Generator[None, None, None]:
    """Context manager that logs the elapsed time of a block."""
    log = logger or get_logger()
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        log.debug("%s: %.4f s", label, elapsed)