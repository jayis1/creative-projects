"""Structured logging setup for WFC."""

from __future__ import annotations

import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO",
    fmt: Optional[str] = None,
    stream=None,
) -> logging.Logger:
    """Configure the ``wfc_generator`` logger.

    Parameters
    ----------
    level:
        Logging level name (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
    fmt:
        Optional log message format string.
    stream:
        Output stream (defaults to ``sys.stderr``).

    Returns
    -------
    logging.Logger
        The configured ``wfc_generator`` logger.
    """
    logger = logging.getLogger("wfc_generator")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Avoid duplicate handlers across repeated calls.
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(
        logging.Formatter(fmt or "%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    return logger