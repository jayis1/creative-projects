"""Centralized logging configuration for the BPE tokenizer.

Provides a helper to configure logging with sensible defaults,
supporting both library-level and CLI-level usage.
"""

from __future__ import annotations

import logging
import sys
from typing import TextIO

__all__ = ["configure_logging", "get_logger"]

# Sentinel to avoid configuring logging twice.
_configured = False


def configure_logging(
    level: int | str = logging.INFO,
    stream: TextIO | None = None,
    fmt: str | None = None,
) -> None:
    """Configure the ``bpe_tokenizer`` logger.

    Parameters
    ----------
    level:
        Logging level (``logging.DEBUG``, ``"WARNING"``, etc.).
    stream:
        Output stream (default: ``sys.stderr``).
    fmt:
        Custom format string.  A sensible default is used if None.
    """
    global _configured

    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(logging.Formatter(fmt))

    logger = logging.getLogger("bpe_tokenizer")
    # Remove existing handlers to allow reconfiguration.
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger under the ``bpe_tokenizer`` namespace.

    If :func:`configure_logging` hasn't been called, a default
    NullHandler is attached so that logging never produces output
    unless explicitly configured (per the stdlib logging cookbook).
    """
    global _configured
    logger_name = "bpe_tokenizer" if name is None else f"bpe_tokenizer.{name}"
    logger = logging.getLogger(logger_name)
    if not _configured and not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger