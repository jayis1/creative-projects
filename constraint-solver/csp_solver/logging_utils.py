"""
Logging and progress tracking for the CSP Solver.

Provides structured logging, a progress tracker, and utilities
for monitoring solver execution.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Dict, List, Optional, Any

# Create the package logger
logger = logging.getLogger("csp_solver")
logger.addHandler(logging.NullHandler())


class SolverProgress:
    """Track and report solver progress during search.

    Can be used as a progress callback with BacktrackingSolver,
    or standalone for custom progress tracking.

    Attributes:
        assignments: List of assignment sizes at each step.
        timestamps: Wall-clock timestamps for each step.
        domain_sizes: Domain size snapshots (if tracked).
        total_steps: Total number of callback invocations.
    """

    def __init__(
        self,
        track_domain_sizes: bool = False,
        log_interval: int = 1000,
    ) -> None:
        """Initialize progress tracker.

        Args:
            track_domain_sizes: Whether to record domain sizes at each step.
            log_interval: How often (in steps) to log progress. 0 = no logging.
        """
        self.track_domain_sizes = track_domain_sizes
        self.log_interval = log_interval
        self.assignments: List[int] = []
        self.timestamps: List[float] = []
        self.domain_sizes: List[Dict[str, int]] = []
        self.total_steps: int = 0
        self._start_time: float = 0.0
        self._csp_ref: Any = None

    def callback(self, assignment: Dict[str, int], stats: Any) -> None:
        """Progress callback for BacktrackingSolver.

        Args:
            assignment: Current partial assignment.
            stats: SolverStats object.
        """
        self.total_steps += 1
        self.assignments.append(len(assignment))
        self.timestamps.append(time.time())

        if self.track_domain_sizes and self._csp_ref is not None:
            sizes = {name: len(var.domain) for name, var in self._csp_ref.variables.items()}
            self.domain_sizes.append(sizes)

        if self.log_interval > 0 and self.total_steps % self.log_interval == 0:
            elapsed = time.time() - self._start_time if self._start_time else 0
            logger.info(
                "Step %d: %d/%d vars assigned, %d backtracks, %.2fs elapsed",
                self.total_steps,
                len(assignment),
                len(self._csp_ref.variables) if self._csp_ref else 0,
                stats.backtracks if stats else 0,
                elapsed,
            )

    def start(self, csp: Any = None) -> None:
        """Start tracking progress.

        Args:
            csp: Optional CSP reference for domain tracking.
        """
        self._start_time = time.time()
        self._csp_ref = csp
        self.assignments = []
        self.timestamps = []
        self.domain_sizes = []
        self.total_steps = 0

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the progress tracking.

        Returns:
            Dictionary with total_steps, total_time, avg_step_time,
            max_depth, and domain_sizes info.
        """
        if not self.timestamps:
            return {"total_steps": 0, "total_time": 0}

        total_time = self.timestamps[-1] - self.timestamps[0] if len(self.timestamps) > 1 else 0
        avg_step = total_time / max(self.total_steps, 1)

        return {
            "total_steps": self.total_steps,
            "total_time": round(total_time, 4),
            "avg_step_time": round(avg_step, 6),
            "max_depth": max(self.assignments) if self.assignments else 0,
            "domain_sizes_tracked": len(self.domain_sizes) > 0,
        }


def setup_logging(
    level: str = "WARNING",
    format_string: Optional[str] = None,
    handler: Optional[logging.Handler] = None,
) -> None:
    """Configure logging for the csp_solver package.

    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        format_string: Custom format string. Uses default if None.
        handler: Custom handler. Uses StreamHandler if None.
    """
    log_level = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(log_level)

    # Remove existing handlers (except NullHandler)
    logger.handlers = [h for h in logger.handlers if isinstance(h, logging.NullHandler)]

    if handler is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(log_level)

    if format_string is None:
        format_string = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    handler.setFormatter(logging.Formatter(format_string))
    handler.setLevel(log_level)
    logger.addHandler(handler)

    # Don't propagate to root logger
    logger.propagate = False