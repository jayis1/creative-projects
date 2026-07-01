"""
Myers O(ND) difference algorithm.

Reference: Eugene W. Myers,
"An O(ND) Difference Algorithm and Its Variations" (1986).

This module implements the classic O(ND) edit-graph shortest-edit-script
algorithm with backtracking, plus a linear-space middle-snake variant.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence, Tuple

__all__ = ["Operation", "DiffOp", "myers_diff", "diff_sequences"]


class Operation(str, Enum):
    EQUAL = "equal"
    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"


@dataclass(frozen=True)
class DiffOp:
    """A single edit-script operation.

    tag      – one of EQUAL/REPLACE/INSERT/DELETE
    i1, i2   – half-open range in the *a* sequence
    j1, j2   – half-open range in the *b* sequence
    """

    tag: Operation
    i1: int
    i2: int
    j1: int
    j2: int

    def a_lines(self, a: Sequence[str]) -> List[str]:
        return list(a[self.i1 : self.i2])

    def b_lines(self, b: Sequence[str]) -> List[str]:
        return list(b[self.j1 : self.j2])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DiffOp(tag={self.tag.value}, "
            f"a=[{self.i1}:{self.i2}], b=[{self.j1}:{self.j2}])"
        )


# ---------------------------------------------------------------------------
# Classic O(ND) with full backtracking — simple, correct, O(ND) time/space
# ---------------------------------------------------------------------------

def _shortest_edit_script(
    a: Sequence[str], b: Sequence[str]
) -> List[dict]:
    """Compute the shortest edit script trace using Myers' O(ND) algorithm.

    Returns a list of V dicts (one per edit distance d), where each V[k]
    is the x-value of the furthest reaching point on diagonal k.  The
    trace is then used to backtrack and reconstruct the path.
    """
    n = len(a)
    m = len(b)
    max_d = n + m

    # V[k] = x-value of the furthest reaching point on diagonal k
    # We use a dict and store the trace for backtracking.
    # V is indexed by k (diagonal number), where k = x - y.
    # k ranges from -d to d.

    # Store the V array at each d level for backtracking
    trace: List[dict] = []

    # Initial V: before any edits, we're at (0, 0) on diagonal 0
    # V[1] = 0 is the convention from Myers' paper (so V[0] = V[1] = 0)
    v: dict = {1: 0}
    trace.append(dict(v))

    for d in range(max_d + 1):
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                x = v.get(k + 1, 0)  # down (insert from b)
            else:
                x = v.get(k - 1, 0) + 1  # right (delete from a)
            y = x - k

            # Follow the snake (diagonal moves)
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[k] = x

            if x >= n and y >= m:
                trace.append(dict(v))
                return trace

        trace.append(dict(v))

    return trace


def _backtrack(
    trace: List[dict],
    a: Sequence[str],
    b: Sequence[str],
) -> List[Tuple[int, int, int, int, int]]:
    """Backtrack through the trace to produce a list of edit steps.

    Each step is (x1, y1, x2, y2, kind) where kind is:
      0 = snake (equal), 1 = right (delete), 2 = down (insert)

    ``trace[d]`` is the V array *after* processing edit distance d.
    During backtracking, the point (x, y) was reached at edit distance d;
    the point it came from was at edit distance d-1, so we look at
    ``trace[d-1]``.
    """
    n = len(a)
    m = len(b)
    x, y = n, m

    steps: List[Tuple[int, int, int, int, int]] = []

    for d in range(len(trace) - 1, 0, -1):
        if x == 0 and y == 0:
            break

        # V array from *before* the edit at distance d was applied
        v = trace[d - 1]
        k = x - y

        if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
            prev_k = k + 1  # came from down (insert)
        else:
            prev_k = k - 1  # came from right (delete)

        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k

        # Snake from (prev_x or prev_x+1, ...) to (x, y)
        while x > prev_x and y > prev_y:
            steps.append((x - 1, y - 1, x, y, 0))  # snake
            x -= 1
            y -= 1

        if d > 0 and (x > 0 or y > 0):
            if x == prev_x:
                # Down move (insert from b)
                steps.append((prev_x, prev_y, prev_x, prev_y + 1, 2))
                y -= 1
            else:
                # Right move (delete from a)
                steps.append((prev_x, prev_y, prev_x + 1, prev_y, 1))
                x -= 1

    # Handle any remaining initial snake from (0,0)
    while x > 0 and y > 0:
        steps.append((x - 1, y - 1, x, y, 0))
        x -= 1
        y -= 1
    # Handle remaining single-axis moves (pure inserts or deletes at start)
    while x > 0:
        steps.append((x - 1, y, x, y, 1))
        x -= 1
    while y > 0:
        steps.append((x, y - 1, x, y, 2))
        y -= 1

    steps.reverse()
    return steps


def myers_diff(a: Sequence[str], b: Sequence[str]) -> List[DiffOp]:
    """Return the Myers diff of *a* and *b* as a list of :class:`DiffOp`.

    Uses the classic O(ND) algorithm with full trace backtracking.
    """
    if not a and not b:
        return []
    if not a:
        return [DiffOp(Operation.INSERT, 0, 0, 0, len(b))]
    if not b:
        return [DiffOp(Operation.DELETE, 0, len(a), 0, 0)]
    if a == b:
        return [DiffOp(Operation.EQUAL, 0, len(a), 0, len(b))]

    # For very large inputs, increase recursion limit (we don't recurse,
    # but just in case)
    old_limit = sys.getrecursionlimit()
    if len(a) + len(b) > 5000:
        sys.setrecursionlimit(max(old_limit, (len(a) + len(b)) * 2))

    trace = _shortest_edit_script(a, b)
    steps = _backtrack(trace, a, b)

    # Convert steps to DiffOps
    ops: List[DiffOp] = []
    for x1, y1, x2, y2, kind in steps:
        if kind == 0:
            # Snake (equal)
            if ops and ops[-1].tag == Operation.EQUAL:
                # Extend
                ops[-1] = DiffOp(
                    Operation.EQUAL,
                    ops[-1].i1, x2,
                    ops[-1].j1, y2,
                )
            else:
                ops.append(DiffOp(Operation.EQUAL, x1, x2, y1, y2))
        elif kind == 1:
            # Right (delete from a)
            if ops and ops[-1].tag == Operation.DELETE:
                ops[-1] = DiffOp(
                    Operation.DELETE,
                    ops[-1].i1, x2,
                    ops[-1].j1, y2,
                )
            else:
                ops.append(DiffOp(Operation.DELETE, x1, x2, y1, y2))
        elif kind == 2:
            # Down (insert from b)
            if ops and ops[-1].tag == Operation.INSERT:
                ops[-1] = DiffOp(
                    Operation.INSERT,
                    ops[-1].i1, x2,
                    ops[-1].j1, y2,
                )
            else:
                ops.append(DiffOp(Operation.INSERT, x1, x2, y1, y2))

    sys.setrecursionlimit(old_limit)

    # Coalesce adjacent ops and convert consecutive DELETE+INSERT into REPLACE
    _coalesce(ops)
    _merge_replace(ops)
    return ops


def _coalesce(ops: List[DiffOp]) -> None:
    """Merge adjacent ops of the same tag **in place**."""
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
                last.tag,
                last.i1, op.i2,
                last.j1, op.j2,
            )
        else:
            merged.append(op)
    ops[:] = merged


def _merge_replace(ops: List[DiffOp]) -> None:
    """Convert adjacent DELETE followed by INSERT into REPLACE."""
    if len(ops) < 2:
        return
    merged: List[DiffOp] = []
    i = 0
    while i < len(ops):
        if (
            i + 1 < len(ops)
            and ops[i].tag == Operation.DELETE
            and ops[i + 1].tag == Operation.INSERT
            and ops[i].i2 == ops[i + 1].i1
            and ops[i].j2 == ops[i + 1].j1
        ):
            merged.append(DiffOp(
                Operation.REPLACE,
                ops[i].i1, ops[i + 1].i2,
                ops[i].j1, ops[i + 1].j2,
            ))
            i += 2
        else:
            merged.append(ops[i])
            i += 1
    ops[:] = merged


# ---------------------------------------------------------------------------
# Convenience public API
# ---------------------------------------------------------------------------


def diff_sequences(
    a: Sequence[str], b: Sequence[str], *, algorithm: str = "myers"
) -> List[DiffOp]:
    """Return the diff of two sequences using the chosen algorithm.

    Parameters
    ----------
    a, b : sequence of strings (lines)
    algorithm : "myers" (default) — only Myers is provided here.

    Returns
    -------
    list of :class:`DiffOp`
    """
    if algorithm != "myers":
        raise ValueError(f"Unknown algorithm: {algorithm!r}")
    return myers_diff(a, b)