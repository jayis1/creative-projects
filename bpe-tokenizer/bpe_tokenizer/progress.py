"""Progress reporting utilities for BPE training.

Provides a callback-based progress interface so that CLI tools,
notebooks, and applications can monitor training progress without
polluting the core training code with print statements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

__all__ = [
    "ProgressInfo",
    "ProgressCallback",
    "create_print_callback",
]


@dataclass
class ProgressInfo:
    """Progress snapshot during BPE training.

    Attributes
    ----------
    iteration:
        Current merge iteration (1-based).
    max_merges:
        Maximum number of merges that will be performed.
    merged_pair:
        The pair that was just merged (tuple of two strings).
    merged_token:
        The resulting merged token string.
    merge_count:
        Frequency of the merged pair in the corpus.
    current_vocab_size:
        Total vocab size after this merge.
    """

    iteration: int
    max_merges: int
    merged_pair: tuple[str, str]
    merged_token: str
    merge_count: int
    current_vocab_size: int

    @property
    def progress_pct(self) -> float:
        """Completion percentage (0–100)."""
        if self.max_merges <= 0:
            return 100.0
        return (self.iteration / self.max_merges) * 100.0


ProgressCallback = Callable[[ProgressInfo], None]
"""Type alias for a progress callback function."""


def create_print_callback(every: int = 50) -> ProgressCallback:
    """Create a simple print-based progress callback.

    Prints a progress line every *every* iterations.

    >>> callback = create_print_callback(every=100)
    """

    def callback(info: ProgressInfo) -> None:
        if info.iteration % every == 0 or info.iteration == info.max_merges:
            print(
                f"  [{info.iteration}/{info.max_merges}] "
                f"({info.progress_pct:.1f}%) "
                f"merge={info.merged_token!r} "
                f"count={info.merge_count} "
                f"vocab={info.current_vocab_size}"
            )

    return callback