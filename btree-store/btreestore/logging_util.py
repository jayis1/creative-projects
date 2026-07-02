"""
Logging setup for btreestore.

Provides a configurable logging system with support for
file and console output, structured formatting, and log levels.
"""

import logging
import sys
from typing import Optional

# Module-level logger
_logger: Optional[logging.Logger] = None


def get_logger(name: str = "btreestore") -> logging.Logger:
    """Get or create the btreestore logger.

    Returns a singleton logger instance configured with
    the most recent setup.
    """
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.INFO)
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            _logger.addHandler(handler)
    return _logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    name: str = "btreestore",
) -> logging.Logger:
    """Configure and return the btreestore logger.

    Args:
        level: Logging level string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        log_file: Optional file path for log output. If None, logs to stderr.
        name: Logger name.

    Returns:
        Configured logger instance.
    """
    global _logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stderr)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    _logger = logger
    return logger