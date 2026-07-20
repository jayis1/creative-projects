"""Centralized logging for the TSP solver.

Provides :func:`get_logger` which returns a configured logger that honors the
``TSP_LOG_LEVEL`` environment variable and an optional log file.  All
algorithm modules should use ``get_logger(__name__)`` rather than ``print``
for diagnostic output.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False
_log_level: int = logging.WARNING
_log_file: Optional[str] = None


def configure_logging(level: str = "WARNING", log_file: Optional[str] = None) -> None:
    """Configure the root logger for the ``tsp_solver`` package.

    Parameters
    ----------
    level : str
        Logging level name: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``.
    log_file : str, optional
        If given, also write logs to this file (in addition to stderr).
    """
    global _configured, _log_level, _log_file
    _log_level = getattr(logging, level.upper(), logging.WARNING)
    _log_file = log_file

    root = logging.getLogger("tsp_solver")
    root.setLevel(_log_level)
    # Remove existing handlers to avoid duplicates on re-configure
    root.handlers.clear()

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(stderr_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
        root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``tsp_solver`` namespace.

    Ensures logging is configured (using env vars or defaults) on first call.
    """
    global _configured
    if not _configured:
        import os
        level = os.environ.get("TSP_LOG_LEVEL", "WARNING")
        log_file = os.environ.get("TSP_LOG_FILE")
        configure_logging(level, log_file)
    # Ensure the name is under the tsp_solver namespace
    if not name.startswith("tsp_solver"):
        name = f"tsp_solver.{name}"
    return logging.getLogger(name)