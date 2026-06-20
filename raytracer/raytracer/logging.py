"""logging.py — Structured logging for the ray tracer.

Provides a pre-configured :mod:`logging` logger named ``"raytracer"`` plus
convenience helpers.  The logger is silent by default (``WARNING`` level) so
it does not interfere with render output on stderr.  Users can enable it via
:func:`configure` or by passing ``--log-level`` to the CLI.

Example
-------
::

    from raytracer.logging import logger, configure
    configure("DEBUG")
    logger.debug("BVH built with %d nodes", n)
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

__all__ = ["logger", "configure", "get_level"]

_logger = logging.getLogger("raytracer")
_logger.setLevel(logging.WARNING)
_handler: Optional[logging.Handler] = None


class _ColorFormatter(logging.Formatter):
    """Minimal ANSI color formatter for interactive use."""

    _LEVEL_COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[35m",  # magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._LEVEL_COLORS.get(record.levelname, "")
        msg = super().format(record)
        return f"{color}{record.levelname}{self._RESET}: {msg}"


def configure(level: str = "WARNING", stream=None) -> None:
    """Configure the raytracer logger.

    Parameters
    ----------
    level : one of ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``,
        ``"CRITICAL"`` (case-insensitive), or a numeric level.
    stream : output stream (default: stderr).
    """
    global _handler
    if isinstance(level, str):
        level = level.upper()
    numeric = logging.getLevelName(level) if isinstance(level, str) else int(level)
    _logger.setLevel(numeric)
    if _handler is not None:
        _logger.removeHandler(_handler)
    target = stream if stream is not None else sys.stderr
    _handler = logging.StreamHandler(target)
    _handler.setLevel(numeric)
    _handler.setFormatter(_ColorFormatter())
    _logger.addHandler(_handler)
    _logger.propagate = False


def get_level() -> int:
    """Return the current effective logging level."""
    return _logger.getEffectiveLevel()


logger = _logger