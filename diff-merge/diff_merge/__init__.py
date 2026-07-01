"""
diff_merge — a from-scratch text diff/patch/merge toolkit.

Implements:
  * Myers O(ND) difference algorithm (with backtracking)
  * Patience diff (Bram Cohen) and Histogram diff (Eclipse)
  * LCS-based diff (dynamic programming)
  * Unified / context / normal diff output formats
  * Patch parsing and application with fuzz/reject handling
  * Three-way merge with conflict markers
  * Intra-line (word-level) diff highlighting
  * Diff statistics (diffstat)
  * Configuration system (JSON/TOML/YAML)
  * Whitespace-ignoring and blank-line-ignoring options
  * Binary file detection

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
from .patch import parse_unified_diff, apply_patch, PatchError, PatchResult
from .merge import three_way_merge, MergeResult, Conflict
from .inline import word_diff, highlight_inline
from .stat import DiffStat, compute_diffstat
from .config import Config, load_config, save_config
from .utils import preprocess_lines, reverse_ops, is_binary
from .sidebyside import side_by_side, render_side_by_side
from .htmlout import html_diff, html_diff_document
from .dirdiff import diff_directories, DirDiff, FileChange, ChangeType
from .optimizer import optimize_diff, optimize_blanks, optimize_common_edges
from .logging_config import get_logger, setup_logging

__version__ = "3.0.0"
__all__ = [
    # Algorithms
    "myers_diff",
    "diff_sequences",
    "patience_diff",
    "histogram_diff",
    "lcs_diff",
    "longest_common_subsequence",
    # Formats
    "unified_diff",
    "context_diff",
    "normal_diff",
    "DiffHunk",
    "Hunk",
    # Patch
    "parse_unified_diff",
    "apply_patch",
    "PatchError",
    "PatchResult",
    # Merge
    "three_way_merge",
    "MergeResult",
    "Conflict",
    # Inline
    "word_diff",
    "highlight_inline",
    # Stats
    "DiffStat",
    "compute_diffstat",
    # Config
    "Config",
    "load_config",
    "save_config",
    # Utils
    "preprocess_lines",
    "reverse_ops",
    "is_binary",
    # Side-by-side
    "side_by_side",
    "render_side_by_side",
    # HTML output
    "html_diff",
    "html_diff_document",
    # Directory diff
    "diff_directories",
    "DirDiff",
    "FileChange",
    "ChangeType",
    # Optimizer
    "optimize_diff",
    "optimize_blanks",
    "optimize_common_edges",
    # Logging
    "get_logger",
    "setup_logging",
]