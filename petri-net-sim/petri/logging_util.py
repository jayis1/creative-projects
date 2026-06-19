"""Logging support for petri-net-sim.

Provides a configured logger with structured output, configurable verbosity,
and optional file logging.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str = "petri", level: int = logging.INFO) -> logging.Logger:
    """Get or create a configured logger.

    Parameters
    ----------
    name : str
        Logger name (typically "petri").
    level : int
        Logging level (logging.DEBUG, logging.INFO, etc.)
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    name: str = "petri",
) -> logging.Logger:
    """Configure logging with optional file output.

    Parameters
    ----------
    level : str
        Logging level as string: "DEBUG", "INFO", "WARNING", "ERROR".
    log_file : str, optional
        If provided, also log to this file.
    name : str
        Logger name.
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = level_map.get(level.upper(), logging.INFO)

    logger = get_logger(name, log_level)
    logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT))
    console.setLevel(log_level)
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT))
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

    logger.setLevel(log_level)
    return logger