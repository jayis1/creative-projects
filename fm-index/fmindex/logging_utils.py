"""Logging setup for FM-Index.

Provides a configured logger with sensible defaults and a context manager
for timing operations.  The logger is configured once on import; callers
can re-configure via :func:`setup_logging`.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Iterator, Optional

_LOGGER_NAME = "fmindex"
_logger: Optional[logging.Logger] = None


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """Configure and return the FM-Index logger.

    Parameters
    ----------
    level:
        Logging level name (``"DEBUG"``, ``"INFO"``, …).
    log_file:
        Optional file path to also log to.
    fmt:
        Optional format string (defaults to a concise format).
    """
    global _logger
    if _logger is not None:
        for h in list(_logger.handlers):
            _logger.removeHandler(h)
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)
    # console handler
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # optional file handler
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Return the configured FM-Index logger (creating a default if needed)."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


@contextmanager
def log_time(operation: str, level: int = logging.DEBUG) -> Iterator[None]:
    """Context manager that logs the duration of an operation.

    >>> with log_time("backward search"):
    ...     idx.count("pattern")
    """
    logger = get_logger()
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        logger.log(level, "%s completed in %.3fs", operation, dt)