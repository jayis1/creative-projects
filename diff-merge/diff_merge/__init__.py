"""
diff_merge — a from-scratch text diff/patch/merge toolkit.

Implements:
  * Myers O(ND) difference algorithm (middle-snake, linear-space)
  * Patience diff (Bram Cohen) and Histogram diff (Eclipse)
  * LCS-based diff (dynamic programming)
  * Unified / context / normal diff output formats
  * Patch parsing and application with fuzz/reject handling
  * Three-way merge with conflict markers

Pure Python (stdlib only). No external dependencies.
"""

from .myers import myers_diff, diff_sequences
from .patience import patience_diff
from .histogram import histogram_diff
from .lcs import lcs_diff, longest_common_subsequence
from .format import (
    unified_diff,
    context_diff,
    normal_diff,
    DiffHunk,
    Hunk,
)
from .patch import parse_unified_diff, apply_patch, PatchError
from .merge import three_way_merge, MergeResult, Conflict

__version__ = "1.0.0"
__all__ = [
    "myers_diff",
    "diff_sequences",
    "patience_diff",
    "histogram_diff",
    "lcs_diff",
    "longest_common_subsequence",
    "unified_diff",
    "context_diff",
    "normal_diff",
    "DiffHunk",
    "Hunk",
    "parse_unified_diff",
    "apply_patch",
    "PatchError",
    "three_way_merge",
    "MergeResult",
    "Conflict",
]