"""
Logging support for the MCTS engine.

Provides a configured logger that writes to both stderr and optionally
to a file. Used throughout the engine for diagnostics, search stats,
and error reporting.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOGGER_NAME = "mcts"
_configured = False


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Get the MCTS logger, configuring it on first access."""
    global _configured
    logger = logging.getLogger(name)
    if not _configured:
        _configure_default(logger)
        _configured = True
    return logger


def _configure_default(logger: logging.Logger) -> None:
    """Set up default logging configuration."""
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(handler)


def configure_logging(
    level: str = "WARNING",
    log_file: Optional[str] = None,
    fmt: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt: str = "%H:%M:%S",
) -> logging.Logger:
    """Configure logging for the MCTS engine.

    Args:
        level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR").
        log_file: Optional file path. If given, logs are also written here.
        fmt: Log message format string.
        datefmt: Date format string.

    Returns:
        The configured logger.
    """
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))

    # Remove existing handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)

    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # stderr handler
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _configured = True
    return logger