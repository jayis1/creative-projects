"""Logging setup for the MIDI Step Sequencer.

Provides a centralized logging configuration with both console
and optional file output.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

# Module-level logger
logger = logging.getLogger("sequencer")

# Default format
CONSOLE_FORMAT = "%(levelname)s: %(message)s"
FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(
    level: str = "WARNING",
    log_file: Optional[str] = None,
    console: bool = True,
) -> logging.Logger:
    """Configure logging for the sequencer.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to a log file
        console: Whether to enable console output

    Returns:
        The root sequencer logger
    """
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(numeric_level)

    # Remove existing handlers
    logger.handlers.clear()

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
        logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the sequencer namespace.

    Args:
        name: Submodule name (e.g. 'export', 'generators')

    Returns:
        A logger named 'sequencer.<name>'
    """
    return logger.getChild(name)