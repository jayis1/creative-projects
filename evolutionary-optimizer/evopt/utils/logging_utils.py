"""Logging utilities."""

from __future__ import annotations

import logging
import sys


def get_logger(name: str = "evopt", verbose: bool = False) -> logging.Logger:
    """Get a configured logger.

    Args:
        name: Logger name.
        verbose: If True, set level to DEBUG; else WARNING (silent by default).
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level = logging.DEBUG if verbose else logging.WARNING
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger