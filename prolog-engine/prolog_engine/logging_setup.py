"""Logging setup for the mini-Prolog engine.

Provides a structured logging configuration with configurable levels
and format. Uses Python's standard logging module.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

# Module-level logger
logger = logging.getLogger("prolog_engine")

# Default format
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"


def configure_logging(
    level: int = logging.WARNING,
    format_str: Optional[str] = None,
    log_file: Optional[str] = None,
    simple: bool = False,
) -> None:
    """Configure logging for the Prolog engine.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        format_str: Custom format string. Defaults to DEFAULT_FORMAT.
        log_file: Optional file path to write logs to.
        simple: If True, use a simpler format suitable for CLI output.
    """
    fmt = format_str or (SIMPLE_FORMAT if simple else DEFAULT_FORMAT)
    formatter = logging.Formatter(fmt)

    handler: logging.Handler
    if log_file:
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler(sys.stderr)

    handler.setFormatter(formatter)

    # Clear existing handlers
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the prolog_engine namespace.

    Args:
        name: Submodule name (e.g., 'engine', 'parser').

    Returns:
        A Logger instance for the given submodule.
    """
    return logger.getChild(name)