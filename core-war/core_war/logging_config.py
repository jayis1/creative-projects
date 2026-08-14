"""
Logging configuration for Core War.

Provides a structured logging setup with configurable levels, formats,
and optional file output.
"""

import logging
import sys
from typing import Optional


# Default format for console logging
_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DEBUG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: %(message)s"

# Logger name prefix for the package
LOGGER_NAME = "core_war"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    debug: bool = False,
) -> logging.Logger:
    """
    Set up logging for the core_war package.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path to write logs to.
        debug: If True, use verbose format and DEBUG level.

    Returns:
        The root logger for core_war.
    """
    if debug:
        level = "DEBUG"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates on re-configuration
    logger.handlers.clear()

    # Console handler
    fmt = _DEBUG_FORMAT if numeric_level <= logging.DEBUG else _DEFAULT_FORMAT
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger under the core_war namespace.

    Args:
        name: Sub-logger name (e.g., 'mars', 'parser').

    Returns:
        Logger instance.
    """
    return logging.getLogger(f"{LOGGER_NAME}.{name}")