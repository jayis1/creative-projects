"""Generation statistics tracking."""

from __future__ import annotations


class GenerationStats:
    """Track statistics about a single WFC generation run.

    Attributes
    ----------
    start_time, end_time:
        Wall-clock timestamps (seconds) marking the run window.
    collapse_steps:
        Number of cells collapsed.
    propagation_steps:
        Number of propagation iterations performed.
    backtrack_count:
        Number of backtracking attempts.
    restart_count:
        Number of full restarts after exhausting backtracking.
    contradiction:
        Whether the run ended in an unrecoverable contradiction.
    grid_width, grid_height:
        Dimensions of the generated grid.
    """

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.collapse_steps: int = 0
        self.propagation_steps: int = 0
        self.backtrack_count: int = 0
        self.restart_count: int = 0
        self.contradiction: bool = False
        self.grid_width: int = 0
        self.grid_height: int = 0

    @property
    def duration(self) -> float:
        """Time taken for generation in seconds."""
        return self.end_time - self.start_time if self.end_time else 0.0

    @property
    def cells_per_second(self) -> float:
        """Generation speed in cells/second."""
        total_cells = self.grid_width * self.grid_height
        if self.duration > 0:
            return total_cells / self.duration
        return 0.0

    def to_dict(self) -> dict:
        """Serialize stats to a plain dict (JSON-friendly)."""
        return {
            "duration": self.duration,
            "collapse_steps": self.collapse_steps,
            "propagation_steps": self.propagation_steps,
            "backtrack_count": self.backtrack_count,
            "restart_count": self.restart_count,
            "contradiction": self.contradiction,
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "cells_per_second": self.cells_per_second,
        }

    def __repr__(self) -> str:
        return (
            f"GenerationStats("
            f"time={self.duration:.3f}s, "
            f"collapses={self.collapse_steps}, "
            f"propagations={self.propagation_steps}, "
            f"backtracks={self.backtrack_count}, "
            f"restarts={self.restart_count}, "
            f"speed={self.cells_per_second:.0f} cells/s, "
            f"contradiction={self.contradiction})"
        )