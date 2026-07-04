"""Logging configuration for the rigid-body engine.

The engine uses Python's standard :mod:`logging` module.  Importing this
module (or calling :func:`configure_logging`) sets up a sensible default
logger named ``rigidbody`` that writes to stderr.  Library code uses
``logging.getLogger("rigidbody")`` so applications can reconfigure it.

Example
-------
::

    from rigidbody.logger import configure_logging, get_logger
    configure_logging(level="DEBUG")
    log = get_logger("rigidbody.world")
    log.debug("stepping world dt=%s", dt)
"""

from __future__ import annotations

import logging
import sys
from typing import Optional, Union

__all__ = ["configure_logging", "get_logger", "LOG_NAME"]

LOG_NAME = "rigidbody"

_DEFAULT_FORMAT = "[%(asctime)s] %(name)s %(levelname)s: %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(
    level: Union[str, int] = "INFO",
    stream=None,
    fmt: str = _DEFAULT_FORMAT,
    datefmt: str = _DEFAULT_DATEFMT,
) -> logging.Logger:
    """Configure the ``rigidbody`` logger.

    Safe to call multiple times — subsequent calls update the level/handlers
    rather than duplicating them.

    Parameters
    ----------
    level:
        Logging level (name or int).  Default ``"INFO"``.
    stream:
        Output stream (default: ``sys.stderr``).
    fmt, datefmt:
        :mod:`logging` format strings.
    """
    global _configured
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(level)
    if _configured:
        # Already configured — just update level.
        logger.setLevel(level)
        return logger
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    logger.addHandler(handler)
    _configured = True
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger under the ``rigidbody`` namespace.

    If *name* is ``None`` the root engine logger is returned.  The first
    call to this function auto-configures INFO-level logging to stderr so
    that simply importing and using the library produces useful output
    without explicit setup.
    """
    global _configured
    if not _configured:
        configure_logging("INFO")
    if name is None:
        return logging.getLogger(LOG_NAME)
    if name.startswith(LOG_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{LOG_NAME}.{name}")