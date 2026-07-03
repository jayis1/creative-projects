"""Structured logging setup for rl-solver."""
from __future__ import annotations

import logging
import sys
from typing import Optional


_LOGGER_NAME = "rl_solver"


def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Get or create a logger for the rl_solver package."""
    logger_name = f"{_LOGGER_NAME}.{name}" if name else _LOGGER_NAME
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


def set_log_level(level: int) -> None:
    """Set the log level for all rl_solver loggers."""
    logging.getLogger(_LOGGER_NAME).setLevel(level)


__all__ = ["get_logger", "set_log_level"]