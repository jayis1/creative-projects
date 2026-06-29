"""Logging utilities for EvOpt.

Provides a configurable logging setup with support for:
    - Console and file output
    - Log levels (DEBUG, INFO, WARNING, ERROR)
    - Named loggers per algorithm
    - JSON-line logging for machine-readable logs

Example::

    from evopt.utils.logging_utils import setup_logging
    setup_logging(level="INFO", logfile="evopt.log")
    # ... run algorithms ...
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, Union

# Track configured loggers to avoid duplicate handlers
_configured_loggers: set = set()


def get_logger(name: str = "evopt", verbose: bool = False) -> logging.Logger:
    """Get a configured logger.

    Args:
        name: Logger name (typically the algorithm class name).
        verbose: If True, set level to DEBUG; else WARNING (silent by default).
    """
    logger = logging.getLogger(name)
    if name in _configured_loggers:
        return logger
    level = logging.DEBUG if verbose else logging.WARNING
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    _configured_loggers.add(name)
    return logger


def setup_logging(level: Union[str, int] = "WARNING",
                  logfile: Optional[Union[str, Path]] = None,
                  fmt: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                  datefmt: str = "%Y-%m-%d %H:%M:%S",
                  json_format: bool = False) -> logging.Logger:
    """Configure the root EvOpt logger and optionally add a file handler.

    Args:
        level: Logging level — one of "DEBUG", "INFO", "WARNING", "ERROR" or
            the corresponding int constants.
        logfile: If provided, also write logs to this file.
        fmt: Log message format string.
        datefmt: Date format string.
        json_format: If True, write JSON-lines to the logfile (each line is a
            JSON object with timestamp, level, name, message).

    Returns:
        The configured root logger.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.WARNING)

    root = logging.getLogger("evopt")
    root.setLevel(level)
    root.propagate = False

    # Clear existing handlers to allow reconfiguration
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(console)

    # File handler
    if logfile:
        p = Path(logfile)
        p.parent.mkdir(parents=True, exist_ok=True)
        if json_format:
            file_handler = _JsonLineHandler(p)
        else:
            file_handler = logging.FileHandler(p, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        file_handler.setLevel(level)
        root.addHandler(file_handler)

    _configured_loggers.add("evopt")
    return root


class _JsonLineHandler(logging.Handler):
    """A logging handler that writes one JSON object per line."""

    import json as _json

    def __init__(self, filepath: Path):
        super().__init__()
        self._filepath = filepath
        self._file = open(filepath, "a", encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:
        import json
        entry = {
            "timestamp": self.format_time(record),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        try:
            self._file.write(json.dumps(entry) + "\n")
            self._file.flush()
        except Exception:
            self.handleError(record)

    @staticmethod
    def format_time(record: logging.LogRecord) -> str:
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))

    def close(self) -> None:
        try:
            self._file.close()
        finally:
            super().close()


def set_verbose(verbose: bool = True) -> None:
    """Globally toggle verbose (DEBUG) logging for all EvOpt loggers."""
    level = logging.DEBUG if verbose else logging.WARNING
    for name in list(_configured_loggers):
        logging.getLogger(name).setLevel(level)
    logging.getLogger("evopt").setLevel(level)