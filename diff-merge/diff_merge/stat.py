"""
Diff statistics (diffstat).

Computes line-level change statistics from a list of DiffOps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .myers import DiffOp, Operation

__all__ = ["DiffStat", "compute_diffstat"]


@dataclass
class DiffStat:
    """Statistics about a diff."""
    additions: int = 0       # lines added (insert + replace new lines)
    deletions: int = 0      # lines deleted (delete + replace old lines)
    unchanged: int = 0     # lines unchanged (equal)
    total_changed: int = 0  # additions + deletions
    total_lines_a: int = 0  # total lines in original
    total_lines_b: int = 0  # total lines in modified

    @property
    def net_change(self) -> int:
        """Net line count change (additions - deletions)."""
        return self.additions - self.deletions

    @property
    def change_ratio(self) -> float:
        """Fraction of lines that changed (0.0 to 1.0)."""
        total = self.total_lines_a + self.total_lines_b
        if total == 0:
            return 0.0
        return (self.additions + self.deletions) / total

    def histogram(self, width: int = 40) -> str:
        """Return an ASCII bar chart histogram of additions/deletions."""
        total = self.additions + self.deletions
        if total == 0:
            return "No changes"

        add_ratio = self.additions / total
        del_ratio = self.deletions / total

        add_width = int(add_ratio * width)
        del_width = int(del_ratio * width)

        add_bar = "+" * add_width
        del_bar = "-" * del_width

        return f"{add_bar}{del_bar} ({self.additions}+/{self.deletions}-)"

    def summary(self) -> str:
        """Return a one-line summary string."""
        return (
            f"{self.additions} insertion(s), {self.deletions} deletion(s), "
            f"{self.unchanged} unchanged"
        )


def compute_diffstat(
    ops: List[DiffOp],
    a: Sequence[str],
    b: Sequence[str],
) -> DiffStat:
    """Compute diff statistics from a list of DiffOps."""
    stat = DiffStat()
    stat.total_lines_a = len(a)
    stat.total_lines_b = len(b)

    for op in ops:
        if op.tag == Operation.EQUAL:
            count = op.i2 - op.i1
            stat.unchanged += count
        elif op.tag == Operation.DELETE:
            count = op.i2 - op.i1
            stat.deletions += count
        elif op.tag == Operation.INSERT:
            count = op.j2 - op.j1
            stat.additions += count
        elif op.tag == Operation.REPLACE:
            a_count = op.i2 - op.i1
            b_count = op.j2 - op.j1
            stat.deletions += a_count
            stat.additions += b_count

    stat.total_changed = stat.additions + stat.deletions
    return stat