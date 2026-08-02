"""Structured logging configuration for the matrix_decomp package.

Provides a :func:`get_logger` helper that returns a configured logger with a
consistent format.  The verbosity can be controlled via the ``MATRIX_DECOMP_LOG``
environment variable (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``) or via the
explicit ``level`` argument.

Example
-------

>>> from matrix_decomp.logging_config import get_logger
>>> log = get_logger("my_module", level="INFO")
>>> log.info("Cholesky factorization complete (n=%d)", 4)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

_LOGGER_NAME = "matrix_decomp"
_configured: bool = False


def get_logger(name: Optional[str] = None, level: Optional[str] = None) -> logging.Logger:
    """Return a logger under the ``matrix_decomp`` namespace.

    Parameters
    ----------
    name : str, optional
        Sub-module name appended to ``"matrix_decomp"``.  If ``None`` the
        top-level package logger is returned.
    level : str, optional
        Override level (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``).
        Defaults to the ``MATRIX_DECOMP_LOG`` env var, or ``"WARNING"``.
    """
    global _configured
    logger_name = _LOGGER_NAME if name is None else f"{_LOGGER_NAME}.{name}"
    logger = logging.getLogger(logger_name)

    if not _configured:
        env_level = os.environ.get("MATRIX_DECOMP_LOG", "WARNING").upper()
        root = logging.getLogger(_LOGGER_NAME)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)
        root.setLevel(env_level)
        _configured = True

    if level is not None:
        logger.setLevel(level.upper())
    return logger


def set_level(level: str) -> None:
    """Set the logging level for the entire ``matrix_decomp`` namespace."""
    logging.getLogger(_LOGGER_NAME).setLevel(level.upper())