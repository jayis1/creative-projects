"""Structured logging support for the wavelet tree library."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data
        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    fmt: str = "text",
    log_file: str | None = None,
) -> logging.Logger:
    """Set up logging for the wavelet tree library.

    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR").
        fmt: Format ("text" or "json").
        log_file: Optional file path for log output.

    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger("wavelet_tree")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    if fmt == "json":
        handler_formatter = JsonFormatter()
    else:
        handler_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(handler_formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(handler_formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """Get the wavelet tree logger."""
    return logging.getLogger("wavelet_tree")