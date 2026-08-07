"""
Structured logging for logicmin.

Uses Python's stdlib logging with an optional JSON formatter.
"""

import logging
import sys
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Minimal JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        entry = {
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging(
    level: str = "WARNING",
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configure and return the logicmin logger."""
    logger = logging.getLogger("logicmin")
    logger.setLevel(getattr(logging, level.upper(), logging.WARNING))
    # clear existing handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)
    fmt = JSONFormatter() if json_format else logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    if log_file:
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.propagate = False
    return logger