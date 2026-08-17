"""Logging utilities for the NURBS toolkit.

Provides a configured logger with support for file output,
JSON formatting, and configurable log levels.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Module-level logger name.
LOGGER_NAME = "nurbs"


class JSONFormatter(logging.Formatter):
    """Log formatter that outputs JSON lines.

    Each log record is serialized as a single JSON object, making
    it easy to parse with log aggregation tools.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        if record.module:
            entry["module"] = record.module
        if record.lineno:
            entry["line"] = record.lineno
        return json.dumps(entry)


def get_logger(
    name: str = LOGGER_NAME,
    level: str = "WARNING",
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    log_file: Optional[str] = None,
    use_json: bool = False,
) -> logging.Logger:
    """Get or create a configured logger.

    Parameters
    ----------
    name : str
        Logger name (hierarchical, e.g. ``nurbs.cli``).
    level : str
        Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    log_format : str
        Format string for standard (non-JSON) output.
    log_file : str, optional
        Path to a log file. If None, only console output is used.
    use_json : bool
        If True, use JSON formatting for log output.

    Returns
    -------
    logging.Logger
        A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))
    logger.handlers.clear()

    if use_json:
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(log_format)

    # Console handler.
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (optional).
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Default logger.
logger = get_logger()


def set_log_level(level: str) -> None:
    """Set the log level on the default logger."""
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))