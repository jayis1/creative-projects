"""
seamcarving/logging.py — Structured logging configuration.

Provides a ``get_logger`` function that returns a configured logger
with optional file output and JSON formatting.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured log output."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def get_logger(
    name: str = "seamcarving",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    json_format: bool = False,
    configure: bool = True,
) -> logging.Logger:
    """Get a configured logger.

    Parameters
    ----------
    name : str
        Logger name (default: ``"seamcarving"``).
    level : int
        Logging level (default: ``logging.INFO``).
    log_file : str, optional
        If provided, also write logs to this file.
    json_format : bool
        If True, format log messages as JSON.
    configure : bool
        If True (default), add/remove handlers.  If False, just return
        the logger without modifying handlers (useful for module-level
        imports that don't want to add duplicate handlers).

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not configure:
        logger.setLevel(level)
        return logger

    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates on re-config
    logger.handlers.clear()

    if json_format:
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger