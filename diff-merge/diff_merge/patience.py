"""
Patience diff algorithm (Bram Cohen).

The idea: find the unique common elements that appear *once* in each
sequence, use them as anchors, then recursively diff the segments
between anchors.  Falls back to Myers/LCS for small or ambiguous
segments.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .myers import DiffOp, Operation
from .lcs import lcs_diff

__all__ = ["patience_diff"]


def _unique_common(
    a: Sequence[str], a_start: int, a_end: int,
    b: Sequence[str], b_start: int, b_end: int,
) -> List[Tuple[int, int]]:
    """Find unique lines common to both sub-ranges.

    Returns a list of (a_index, b_index) pairs sorted by a_index.
    """
    a_counts: Dict[str, List[int]] = {}
    for i in range(a_start, a_end):
        a_counts.setdefault(a[i], []).append(i)
    b_counts: Dict[str, List[int]] = {}
    for j in range(b_start, b_end):
        b_counts.setdefault(b[j], []).append(j)

    common: List[Tuple[int, int]] = []
    for line, a_indices in a_counts.items():
        if len(a_indices) != 1:
            continue
        b_indices = b_counts.get(line)
        if b_indices is None or len(b_indices) != 1:
            continue
        common.append((a_indices[0], b_indices[0]))

    common.sort()
    return common


def _patience_lcs(
    pairs: List[Tuple[int, int]]
) -> List[Tuple[int, int]]:
    """Given (a_idx, b_idx) anchor pairs, return the longest increasing
    subsequence by b_idx (which is automatically increasing in a_idx too
    because we sorted by a_idx)."""
    if not pairs:
        return []

    # Patience LIS on b_idx
    tails: List[int] = []          # b_idx values
    back: List[int] = []           # index into pairs
    parent: List[int] = [-1] * len(pairs)

    import bisect

    for idx, (_ai, bi) in enumerate(pairs):
        pos = bisect.bisect_left(tails, bi)
        if pos == len(tails):
            tails.append(bi)
            back.append(idx)
        else:
            tails[pos] = bi
            back[pos] = idx
        parent[idx] = back[pos - 1] if pos > 0 else -1

    # Reconstruct
    result: List[Tuple[int, int]] = []
    k = back[-1]
    while k != -1:
        result.append(pairs[k])
        k = parent[k]
    result.reverse()
    return result


def patience_diff(
    a: Sequence[str], b: Sequence[str]
) -> List[DiffOp]:
    """Compute the patience diff of *a* and *b*."""
    ops: List[DiffOp] = []
    _patience_recursive(a, 0, len(a), b, 0, len(b), ops)
    _coalesce(ops)
    return ops


def _patience_recursive(
    a: Sequence[str], a_start: int, a_end: int,
    b: Sequence[str], b_start: int, b_end: int,
    out: List[DiffOp],
) -> None:
    n = a_end - a_start
    m = b_end - b_start

    if n == 0 and m == 0:
        return
    if n == 0:
        out.append(DiffOp(Operation.INSERT, a_start, a_start, b_start, b_end))
        return
    if m == 0:
        out.append(DiffOp(Operation.DELETE, a_start, a_end, b_start, b_start))
        return
    if a[a_start:a_end] == b[b_start:b_end]:
        out.append(DiffOp(Operation.EQUAL, a_start, a_end, b_start, b_end))
        return

    pairs = _unique_common(a, a_start, a_end, b, b_start, b_end)
    anchors = _patience_lcs(pairs)

    if not anchors:
        # No unique common lines — fall back to LCS diff for this segment
        new_ops = lcs_diff(a[a_start:a_end], b[b_start:b_end])
        out.extend(new_ops)
        # Fix up indices (lcs_diff returns indices relative to the slices)
        _shift_ops(out, a_start, b_start, len(new_ops))
        return

    prev_ai = a_start
    prev_bi = b_start
    for ai, bi in anchors:
        _patience_recursive(
            a, prev_ai, ai,
            b, prev_bi, bi,
            out,
        )
        # Emit the anchor as EQUAL
        out.append(DiffOp(Operation.EQUAL, ai, ai + 1, bi, bi + 1))
        prev_ai = ai + 1
        prev_bi = bi + 1

    _patience_recursive(
        a, prev_ai, a_end,
        b, prev_bi, b_end,
        out,
    )


def _shift_ops(
    ops: List[DiffOp], a_off: int, b_off: int, count: int
) -> None:
    """Shift the indices of the last *count* ops by a_off/b_off."""
    for i in range(len(ops) - count, len(ops)):
        op = ops[i]
        ops[i] = DiffOp(
            op.tag,
            op.i1 + a_off, op.i2 + a_off,
            op.j1 + b_off, op.j2 + b_off,
        )


def _coalesce(ops: List[DiffOp]) -> None:
    """Merge adjacent ops of the same tag in place."""
    if not ops:
        return
    merged: List[DiffOp] = [ops[0]]
    for op in ops[1:]:
        last = merged[-1]
        if (
            last.tag == op.tag
            and last.i2 == op.i1
            and last.j2 == op.j1
        ):
            merged[-1] = DiffOp(
                last.tag, last.i1, op.i2, last.j1, op.j2
            )
        else:
            merged.append(op)
    ops[:] = merged