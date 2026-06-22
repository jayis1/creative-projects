"""Logging setup for the jpeg-codec package.

Provides a configurable logger that can be enabled via the CLI
``--verbose`` / ``-v`` flag or programmatically.  By default the
library is silent (no log output); enabling logging gives detailed
insight into the encoding/decoding pipeline.
"""

import logging
import sys

_LOGGER_NAME = "jpeg_codec"
_logger: logging.Logger = logging.getLogger(_LOGGER_NAME)
_logger.addHandler(logging.NullHandler())


def get_logger() -> logging.Logger:
    """Return the package logger."""
    return _logger


def setup_logging(
    level: int = logging.INFO,
    stream=sys.stderr,
    fmt: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
) -> logging.Logger:
    """Configure the package logger with a stream handler.

    Parameters
    ----------
    level : int
        Logging level (default ``logging.INFO``).
    stream
        Output stream (default ``sys.stderr``).
    fmt : str
        Log message format string.

    Returns
    -------
    logging.Logger
        The configured logger.
    """
    # Remove existing handlers (except NullHandler).
    for h in list(_logger.handlers):
        if not isinstance(h, logging.NullHandler):
            _logger.removeHandler(h)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(fmt))
    _logger.addHandler(handler)
    _logger.setLevel(level)
    return _logger


def set_verbose(verbose: bool = True) -> None:
    """Enable or disable verbose (DEBUG-level) logging."""
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        # Reset to NullHandler only.
        for h in list(_logger.handlers):
            if not isinstance(h, logging.NullHandler):
                _logger.removeHandler(h)