"""
Directory (recursive) diff.

Compares two directory trees and produces a list of file-level changes
(added, removed, modified).  Can optionally compute per-file diffs and
summary statistics.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .myers import myers_diff, Operation
from .stat import compute_diffstat, DiffStat
from .utils import is_binary

__all__ = ["FileChange", "ChangeType", "DirDiff", "diff_directories"]


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class FileChange:
    """A single file change between two directories."""
    path: str               # relative path (common to both sides)
    change_type: ChangeType
    size_a: int = -1
    size_b: int = -1
    diffstat: Optional[DiffStat] = None


@dataclass
class DirDiff:
    """Result of a directory comparison."""
    changes: List[FileChange] = field(default_factory=list)
    total_added: int = 0
    total_removed: int = 0
    total_modified: int = 0
    total_unchanged: int = 0

    @property
    def has_changes(self) -> bool:
        return any(c.change_type != ChangeType.UNCHANGED for c in self.changes)

    def summary(self) -> str:
        return (
            f"{self.total_added} added, {self.total_removed} removed, "
            f"{self.total_modified} modified, {self.total_unchanged} unchanged"
        )


def _walk_files(root: str) -> Dict[str, str]:
    """Return ``{relative_path: absolute_path}`` for all files under *root*."""
    result: Dict[str, str] = {}
    root_path = Path(root)
    if not root_path.is_dir():
        return result
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in sorted(filenames):
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            # Normalise separators
            rel = rel.replace(os.sep, "/")
            result[rel] = full
    return result


def _read_text_lines(path: str) -> Optional[List[str]]:
    """Read a file as text lines.  Returns ``None`` if binary or unreadable."""
    with open(path, "rb") as f:
        data = f.read()
    if is_binary(data):
        return None
    text = data.decode("utf-8", errors="replace")
    return text.splitlines()


def diff_directories(
    dir_a: str,
    dir_b: str,
    *,
    compute_stats: bool = True,
) -> DirDiff:
    """Compare two directories and return a :class:`DirDiff`.

    Parameters
    ----------
    dir_a, dir_b
        Paths to the two directories.
    compute_stats
        If ``True``, compute per-file diffstats for modified files.
    """
    files_a = _walk_files(dir_a)
    files_b = _walk_files(dir_b)

    all_paths = sorted(set(files_a) | set(files_b))
    result = DirDiff()

    for rel in all_paths:
        in_a = rel in files_a
        in_b = rel in files_b

        if in_a and not in_b:
            result.changes.append(FileChange(
                path=rel, change_type=ChangeType.REMOVED,
                size_a=os.path.getsize(files_a[rel]),
            ))
            result.total_removed += 1
        elif in_b and not in_a:
            result.changes.append(FileChange(
                path=rel, change_type=ChangeType.ADDED,
                size_b=os.path.getsize(files_b[rel]),
            ))
            result.total_added += 1
        else:
            size_a = os.path.getsize(files_a[rel])
            size_b = os.path.getsize(files_b[rel])

            if size_a == size_b:
                # Quick check: compare file contents
                with open(files_a[rel], "rb") as f:
                    da = f.read()
                with open(files_b[rel], "rb") as f:
                    db = f.read()
                if da == db:
                    result.changes.append(FileChange(
                        path=rel, change_type=ChangeType.UNCHANGED,
                        size_a=size_a, size_b=size_b,
                    ))
                    result.total_unchanged += 1
                    continue

            # Modified — compute diff if text
            stat = None
            if compute_stats:
                lines_a = _read_text_lines(files_a[rel])
                lines_b = _read_text_lines(files_b[rel])
                if lines_a is not None and lines_b is not None:
                    ops = myers_diff(lines_a, lines_b)
                    stat = compute_diffstat(ops, lines_a, lines_b)

            result.changes.append(FileChange(
                path=rel, change_type=ChangeType.MODIFIED,
                size_a=size_a, size_b=size_b, diffstat=stat,
            ))
            result.total_modified += 1

    return result