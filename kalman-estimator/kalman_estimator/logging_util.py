"""Structured logging utility for kalman-estimator.

Provides a configured logger that writes both to the console and
optionally to a file, with consistent formatting.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def get_logger(name: str = "kalman_estimator", level: int = logging.INFO,
               log_file: Optional[str] = None) -> logging.Logger:
    """Get or create a configured logger.

    Parameters
    ----------
    name : str
        Logger name (usually ``"kalman_estimator"``).
    level : int
        Logging level (e.g. ``logging.DEBUG``, ``logging.INFO``).
    log_file : str or None
        If provided, also write logs to this file.

    Returns
    -------
    logger : logging.Logger
    """
    global _configured
    logger = logging.getLogger(name)

    if not _configured:
        logger.setLevel(level)
        # avoid duplicate handlers on re-call
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
            logger.addHandler(handler)

            if log_file:
                fh = logging.FileHandler(log_file)
                fh.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
                logger.addHandler(fh)

        _configured = True
    else:
        logger.setLevel(level)

    return logger