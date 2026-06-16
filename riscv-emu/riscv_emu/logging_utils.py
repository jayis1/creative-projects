"""Logging utilities for the RISC-V emulator.

Provides structured logging with configurable levels and formatters.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


# Module-level logger names
LOGGERS = {
    "cpu": "riscv_emu.cpu",
    "memory": "riscv_emu.memory",
    "assembler": "riscv_emu.assembler",
    "disassembler": "riscv_emu.disassembler",
    "loader": "riscv_emu.loader",
    "debugger": "riscv_emu.debugger",
    "profiler": "riscv_emu.profiler",
    "tracer": "riscv_emu.tracer",
    "cli": "riscv_emu.cli",
    "config": "riscv_emu.config",
    "state": "riscv_emu.state",
}


class ColorFormatter(logging.Formatter):
    """Colored log formatter for terminal output."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "WARNING",
    log_file: Optional[str] = None,
    colored: bool = True,
    format_string: Optional[str] = None,
) -> None:
    """Configure logging for the RISC-V emulator.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path to also log to.
        colored: Whether to use colored output (for terminals).
        format_string: Custom format string.
    """
    log_level = getattr(logging, level.upper(), logging.WARNING)

    if format_string is None:
        format_string = "%(levelname)s: %(name)s: %(message)s"

    handler = logging.StreamHandler(sys.stderr)
    if colored and sys.stderr.isatty():
        handler.setFormatter(ColorFormatter(format_string))
    else:
        handler.setFormatter(logging.Formatter(format_string))
    handler.setLevel(log_level)

    root_logger = logging.getLogger("riscv_emu")
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        ))
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Short module name (e.g., 'cpu', 'memory', 'assembler').

    Returns:
        Logger instance.
    """
    full_name = LOGGERS.get(name, f"riscv_emu.{name}")
    return logging.getLogger(full_name)