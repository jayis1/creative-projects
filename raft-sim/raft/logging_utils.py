"""Logging support for the Raft simulator.

Provides a configured logger and structured event logging that integrates
with the Python ``logging`` module.  Logs include timestamps, node ids,
and RPC types, making it easy to trace consensus rounds.

Usage::

    from raft.logging_utils import get_logger, configure_logging
    configure_logging(level="DEBUG")
    log = get_logger("raft.sim")
    log.info("Leader elected", extra={"node": 3, "term": 5})
"""

from __future__ import annotations

import logging
from typing import Any

_DEFAULT_FORMAT = (
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_CONFIGURED = False


def configure_logging(
    level: str | int = "INFO",
    fmt: str | None = None,
    datefmt: str | None = None,
) -> None:
    """Configure root logging for the raft-sim package.

    Call once at startup (e.g. from the CLI) to get consistent output.
    """
    global _CONFIGURED
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    fmt = fmt or _DEFAULT_FORMAT
    datefmt = datefmt or _DATE_FMT
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt, datefmt))
    root = logging.getLogger("raft")
    # Avoid duplicate handlers on re-configure.
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)
    _CONFIGURED = True


def get_logger(name: str = "raft") -> logging.Logger:
    """Return a logger under the ``raft`` namespace."""
    return logging.getLogger(name)


class StructuredEventLogger:
    """A lightweight structured logger that emits events as key=value pairs.

    This is useful for tracing RPC flows during simulations::

        slog = StructuredEventLogger("raft.trace")
        slog.event("AppendEntries", src=0, dst=1, term=3, entries=2)
    """

    def __init__(self, name: str = "raft.trace", level: int = logging.DEBUG) -> None:
        self._log = logging.getLogger(name)
        self._level = level

    def event(self, event_type: str, **fields: Any) -> None:
        """Log a structured event with arbitrary fields."""
        if self._log.isEnabledFor(self._level):
            parts = [f"{k}={v}" for k, v in sorted(fields.items())]
            self._log.log(self._level, f"{event_type} | {' '.join(parts)}")