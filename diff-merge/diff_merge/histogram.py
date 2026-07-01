"""
Histogram diff (Eclipse JGit).

An enhancement of patience diff: instead of only using *unique* lines
as anchors, histogram diff uses the *least frequent* common lines as
anchors.  When all lines are unique, it falls back to patience diff's
unique-line matching.  When there are no unique lines, it picks the
least frequent non-unique lines and recurses.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Sequence, Tuple

from .myers import DiffOp, Operation
from .lcs import lcs_diff

__all__ = ["histogram_diff"]


def _histogram_common(
    a: Sequence[str], a_start: int, a_end: int,
    b: Sequence[str], b_start: int, b_end: int,
) -> List[Tuple[int, int]]:
    """Find anchor candidates using histogram (least-frequency) matching.

    Returns a list of (a_index, b_index) pairs, sorted by a_index.
    """
    a_counts: Counter[str] = Counter(
        a[i] for i in range(a_start, a_end)
    )
    b_counts: Counter[str] = Counter(
        b[j] for j in range(b_start, b_end)
    )

    # For each line that appears in both, compute combined frequency
    # (occurrences in a + occurrences in b).
    candidates: Dict[str, int] = {}
    for line in a_counts:
        if line in b_counts:
            candidates[line] = a_counts[line] + b_counts[line]

    if not candidates:
        return []

    # Pick the minimum-frequency lines
    min_freq = min(candidates.values())
    rare_lines = {
        line for line, freq in candidates.items() if freq == min_freq
    }

    # If the minimum frequency is 2 (unique in each side), use the
    # classic patience approach. Otherwise use the first occurrence
    # in each side.
    common: List[Tuple[int, int]] = []
    if min_freq == 2:
        # Unique in each side — patience-style
        a_first: Dict[str, int] = {}
        for i in range(a_start, a_end):
            line = a[i]
            if line in rare_lines and line not in a_first:
                a_first[line] = i
        b_first: Dict[str, int] = {}
        for j in range(b_start, b_end):
            line = b[j]
            if line in rare_lines and line not in b_first:
                b_first[line] = j
        for line, ai in a_first.items():
            bi = b_first.get(line)
            if bi is not None:
                common.append((ai, bi))
    else:
        # Non-unique rare lines — take first occurrence in each
        a_first: Dict[str, int] = {}
        for i in range(a_start, a_end):
            line = a[i]
            if line in rare_lines and line not in a_first:
                a_first[line] = i
        b_first: Dict[str, int] = {}
        for j in range(b_start, b_end):
            line = b[j]
            if line in rare_lines and line not in b_first:
                b_first[line] = j
        for line, ai in a_first.items():
            bi = b_first.get(line)
            if bi is not None:
                common.append((ai, bi))

    common.sort()
    return common


def _patience_lis(
    pairs: List[Tuple[int, int]]
) -> List[Tuple[int, int]]:
    """Longest increasing subsequence by b-index."""
    if not pairs:
        return []
    import bisect

    tails: List[int] = []
    back: List[int] = []
    parent: List[int] = [-1] * len(pairs)

    for idx, (_ai, bi) in enumerate(pairs):
        pos = bisect.bisect_left(tails, bi)
        if pos == len(tails):
            tails.append(bi)
            back.append(idx)
        else:
            tails[pos] = bi
            back[pos] = idx
        parent[idx] = back[pos - 1] if pos > 0 else -1

    result: List[Tuple[int, int]] = []
    k = back[-1]
    while k != -1:
        result.append(pairs[k])
        k = parent[k]
    result.reverse()
    return result


def histogram_diff(
    a: Sequence[str], b: Sequence[str]
) -> List[DiffOp]:
    """Compute the histogram diff of *a* and *b*."""
    ops: List[DiffOp] = []
    _histogram_recursive(a, 0, len(a), b, 0, len(b), ops)
    _coalesce(ops)
    return ops


def _histogram_recursive(
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

    pairs = _histogram_common(a, a_start, a_end, b, b_start, b_end)
    anchors = _patience_lis(pairs)

    if not anchors:
        new_ops = lcs_diff(a[a_start:a_end], b[b_start:b_end])
        out.extend(new_ops)
        _shift_ops(out, a_start, b_start, len(new_ops))
        return

    prev_ai = a_start
    prev_bi = b_start
    for ai, bi in anchors:
        _histogram_recursive(a, prev_ai, ai, b, prev_bi, bi, out)
        out.append(DiffOp(Operation.EQUAL, ai, ai + 1, bi, bi + 1))
        prev_ai = ai + 1
        prev_bi = bi + 1
    _histogram_recursive(a, prev_ai, a_end, b, prev_bi, b_end, out)


def _shift_ops(
    ops: List[DiffOp], a_off: int, b_off: int, count: int
) -> None:
    for i in range(len(ops) - count, len(ops)):
        op = ops[i]
        ops[i] = DiffOp(
            op.tag,
            op.i1 + a_off, op.i2 + a_off,
            op.j1 + b_off, op.j2 + b_off,
        )


def _coalesce(ops: List[DiffOp]) -> None:
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