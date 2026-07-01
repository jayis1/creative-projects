"""
LCS (longest common subsequence) diff via dynamic programming.

This is O(NM) time and O(NM) space — simple but a useful reference
implementation and correctness check against Myers.
"""

from __future__ import annotations

from typing import List, Sequence

from .myers import DiffOp, Operation

__all__ = ["lcs_diff", "longest_common_subsequence"]


def longest_common_subsequence(
    a: Sequence[str], b: Sequence[str]
) -> List[str]:
    """Return the LCS of *a* and *b* (list of common elements)."""
    n, m = len(a), len(b)

    # dp[i][j] = length of LCS of a[:i] and b[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack
    result: List[str] = []
    i, j = n, m
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            result.append(a[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    result.reverse()
    return result


def lcs_diff(a: Sequence[str], b: Sequence[str]) -> List[DiffOp]:
    """Return a diff of *a* and *b* using the LCS DP table.

    Walks the DP table to emit EQUAL / INSERT / DELETE ops, then coalesces
    adjacent ops of the same tag.
    """
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack to build edit script (in reverse)
    raw: List[DiffOp] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            raw.append(DiffOp(Operation.EQUAL, i - 1, i, j - 1, j))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
            raw.append(DiffOp(Operation.INSERT, i, i, j - 1, j))
            j -= 1
        else:
            raw.append(DiffOp(Operation.DELETE, i - 1, i, j, j))
            i -= 1

    raw.reverse()
    _coalesce(raw)
    return raw


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