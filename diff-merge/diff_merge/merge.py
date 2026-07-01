"""
Three-way merge (diff3 algorithm).

Given a common ancestor (*base*), and two derived versions (*ours* and
*theirs*), produce a merged output with conflict markers where the two
sides disagree.

The algorithm:
  1. Compute diff(base → ours) and diff(base → theirs).
  2. Walk both diffs in lock-step over base indices.
  3. Group changes into "hunks" — maximal regions where at least one
     side differs from base.
  4. For each hunk, compare the two sides' content:
       - If identical → take either (clean).
       - If only one side changed → take that side (clean).
       - If both sides changed differently → conflict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .myers import DiffOp, Operation, myers_diff

__all__ = ["Conflict", "MergeResult", "three_way_merge"]


@dataclass
class Conflict:
    """A single merge conflict region."""
    base_start: int
    base_end: int
    ours_start: int
    ours_end: int
    theirs_start: int
    theirs_end: int
    our_lines: List[str] = field(default_factory=list)
    their_lines: List[str] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of a three-way merge."""
    lines: List[str]
    conflicts: List[Conflict] = field(default_factory=list)
    clean: bool = True


# ---------------------------------------------------------------------------
# Internal: classify each base line as unchanged/changed by each side
# ---------------------------------------------------------------------------

def _build_line_map(
    ops: List[DiffOp], base_len: int
) -> List[Tuple[str, int, int]]:
    """Build a per-base-line classification from a diff against base.

    Returns a list of length *base_len* (plus one sentinel at the end
    for trailing inserts).  Each element is a tuple:
      ("equal",  base_idx, src_idx)  — base line unchanged, maps to src_idx
      ("delete", base_idx, -1)       — base line deleted
      ("replace", base_idx, src_idx) — base line replaced by src[src_idx]
                                       (start of replacement block)
    Trailing inserts are stored as ("insert", base_len, src_idx) at the
    last element.
    """
    # Start with all equal
    result: List[Tuple[str, int, int]] = [
        ("equal", i, i) for i in range(base_len)
    ]
    # Plus sentinel for trailing inserts
    result.append(("none", base_len, -1))

    for op in ops:
        if op.tag == Operation.EQUAL:
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                if i < base_len:
                    result[i] = ("equal", i, j)
        elif op.tag == Operation.DELETE:
            for i in range(op.i1, op.i2):
                result[i] = ("delete", i, -1)
        elif op.tag == Operation.REPLACE:
            # Mark the replaced base lines
            a_lines = list(range(op.i1, op.i2))
            b_lines = list(range(op.j1, op.j2))
            # First base line of the replace block records the new indices
            if a_lines:
                result[a_lines[0]] = ("replace", a_lines[0], b_lines[0] if b_lines else -1)
                for i in a_lines[1:]:
                    result[i] = ("delete", i, -1)
            elif b_lines:
                # Pure insert at position op.i1
                result[base_len if op.i1 >= base_len else op.i1] = \
                    ("insert", op.i1, b_lines[0])
        elif op.tag == Operation.INSERT:
            b_lines = list(range(op.j1, op.j2))
            if b_lines:
                insert_at = op.i1
                idx = base_len if insert_at >= base_len else insert_at
                result[idx] = ("insert", insert_at, b_lines[0])

    return result


def _collect_changed_lines(
    ops: List[DiffOp],
    base: Sequence[str],
    other: Sequence[str],
    base_start: int,
    base_end: int,
) -> List[str]:
    """Collect the content from *other* corresponding to base[base_start:base_end].

    This walks the ops and gathers all 'other' lines that correspond to
    the given base range, including insertions within that range.
    """
    result: List[str] = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            # Include any equal lines that fall within the base range
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                if base_start <= i < base_end:
                    result.append(other[j])
        elif op.tag == Operation.DELETE:
            # Deleted lines — no contribution to result
            pass
        elif op.tag == Operation.REPLACE:
            # All replacement lines that overlap the base range
            if op.i1 < base_end and op.i2 > base_start:
                result.extend(other[op.j1:op.j2])
        elif op.tag == Operation.INSERT:
            # Inserted lines at position op.i1
            if base_start <= op.i1 <= base_end:
                result.extend(other[op.j1:op.j2])
    return result


def _find_changed_regions(
    ops: List[DiffOp], base_len: int
) -> List[Tuple[int, int]]:
    """Find maximal (base_start, base_end) regions where *ops* deviate from base."""
    regions: List[Tuple[int, int]] = []
    i = 0
    while i < base_len:
        # Check if line i is changed
        changed = False
        for op in ops:
            if op.tag == Operation.DELETE and op.i1 <= i < op.i2:
                changed = True
                break
            if op.tag == Operation.REPLACE and op.i1 <= i < op.i2:
                changed = True
                break
        if changed:
            # Find the end of this changed region
            start = i
            end = i + 1
            # Extend through consecutive changed lines
            while end < base_len:
                next_changed = False
                for op in ops:
                    if op.tag in (Operation.DELETE, Operation.REPLACE) and op.i1 <= end < op.i2:
                        next_changed = True
                        break
                if not next_changed:
                    break
                end += 1
            # Also extend to include insertions just before this region
            for op in ops:
                if op.tag == Operation.INSERT and op.i1 == start:
                    # Insert at start — extend region start backward? No,
                    # keep it but include the inserted content.
                    pass
            regions.append((start, end))
            i = end
        else:
            # Check for insertions at this position
            for op in ops:
                if op.tag == Operation.INSERT and op.i1 == i:
                    # Insertion point — zero-width region
                    regions.append((i, i))
                    break
            i += 1

    # Check for trailing insertions
    for op in ops:
        if op.tag == Operation.INSERT and op.i1 >= base_len:
            regions.append((base_len, base_len))
            break
        if op.tag == Operation.REPLACE and op.i1 >= base_len:
            regions.append((base_len, base_len))
            break

    return regions


def _merge_regions(
    ours_regions: List[Tuple[int, int]],
    theirs_regions: List[Tuple[int, int]],
    base_len: int,
) -> List[Tuple[int, int]]:
    """Merge overlapping change regions from both sides into a unified list."""
    all_regions = sorted(set(ours_regions + theirs_regions))
    if not all_regions:
        return []

    merged: List[Tuple[int, int]] = [all_regions[0]]
    for start, end in all_regions[1:]:
        last_start, last_end = merged[-1]
        # Only merge truly overlapping regions (not merely adjacent).
        # Adjacent regions (start == last_end) are handled independently
        # so that non-overlapping changes on different sides don't conflict.
        if start < last_end:
            # Overlapping or adjacent — merge
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def three_way_merge(
    base: Sequence[str],
    ours: Sequence[str],
    theirs: Sequence[str],
    *,
    conflict_marker_size: int = 7,
) -> MergeResult:
    """Perform a three-way merge of *ours* and *theirs* against *base*."""
    ops_ours = myers_diff(base, ours)
    ops_theirs = myers_diff(base, theirs)

    ours_regions = _find_changed_regions(ops_ours, len(base))
    theirs_regions = _find_changed_regions(ops_theirs, len(base))
    merged_regions = _merge_regions(ours_regions, theirs_regions, len(base))

    if not merged_regions:
        # No changes at all — return base
        return MergeResult(lines=list(base), conflicts=[], clean=True)

    result: List[str] = []
    conflicts: List[Conflict] = []
    base_idx = 0

    for region_start, region_end in merged_regions:
        # Copy unchanged base lines before this region
        while base_idx < region_start:
            result.append(base[base_idx])
            base_idx += 1

        # Collect content from each side for this region
        our_content = _collect_changed_lines(
            ops_ours, base, ours, region_start, region_end
        )
        their_content = _collect_changed_lines(
            ops_theirs, base, theirs, region_start, region_end
        )
        base_content = list(base[region_start:region_end])

        if our_content == their_content:
            # Both sides made the same change
            result.extend(our_content)
        elif our_content == base_content:
            # Only theirs changed
            result.extend(their_content)
        elif their_content == base_content:
            # Only ours changed
            result.extend(our_content)
        else:
            # Real conflict
            marker = "<" * conflict_marker_size
            sep = "=" * conflict_marker_size
            end_marker = ">" * conflict_marker_size
            # Determine line ending from existing content (if any)
            suffix = "\n" if (our_content and our_content[0].endswith("\n")) else \
                     ("\n" if (base_content and base_content[0].endswith("\n")) else "")
            result.append(f"{marker} ours{suffix}")
            result.extend(our_content)
            result.append(f"{sep}{suffix}")
            result.extend(their_content)
            result.append(f"{end_marker} theirs{suffix}")
            conflicts.append(Conflict(
                base_start=region_start,
                base_end=region_end,
                ours_start=region_start,
                ours_end=region_end,
                theirs_start=region_start,
                theirs_end=region_end,
                our_lines=our_content,
                their_lines=their_content,
            ))

        base_idx = region_end

    # Copy remaining unchanged base lines
    while base_idx < len(base):
        result.append(base[base_idx])
        base_idx += 1

    return MergeResult(lines=result, conflicts=conflicts, clean=not conflicts)