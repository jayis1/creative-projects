"""
Structured logging for network-flow-solver.

Provides a configurable logger that can output to console, file, or both.
All solver modules can use this for debug-level tracing of algorithm steps.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOGGER_NAME = "networkflow"
_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Get the package logger (lazily initialized)."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(_LOGGER_NAME)
        _logger.setLevel(logging.WARNING)
        _logger.addHandler(logging.NullHandler())
    return _logger


def setup_logging(level: str = "INFO",
                  log_file: str | None = None,
                  fmt: str | None = None,
                  quiet: bool = False) -> logging.Logger:
    """Configure logging for the package.

    Parameters
    ----------
    level : str
        Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    log_file : str, optional
        If given, also write logs to this file.
    fmt : str, optional
        Custom format string.  Default includes timestamp, level, message.
    quiet : bool
        If True, suppress console output (useful in CLI quiet mode).

    Returns
    -------
    logging.Logger
        The configured logger.
    """
    logger = get_logger()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    if not quiet:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level_map.get(level.upper(), logging.INFO))
        formatter = logging.Formatter(
            fmt or "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # always debug to file
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def set_level(level: str) -> None:
    """Convenience: set the log level at runtime."""
    logger = get_logger()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))