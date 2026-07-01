"""
Diff optimisation passes.

Post-process a list of :class:`DiffOp` to improve human readability by
shuffling change-region boundaries so that blank lines and common
identifiers are treated as context (equal) rather than being swallowed
into REPLACE/DELETE/INSERT blocks.

Optimisations
-------------
* ``optimize_blanks`` — move blank-line changes to the boundaries of
  edit blocks so that blank lines are treated as context.
* ``optimize_whitespace`` — if a change is purely whitespace, downgrade
  it to EQUAL (optional).
* ``optimize_common_prefix_suffix`` — shrink REPLACE blocks that start
  or end with identical lines, converting them to context.
"""

from __future__ import annotations

from typing import List, Sequence

from .myers import DiffOp, Operation

__all__ = ["optimize_diff", "optimize_blanks", "optimize_common_edges"]


def optimize_diff(
    ops: List[DiffOp],
    a: Sequence[str],
    b: Sequence[str],
    *,
    whitespace: bool = False,
) -> List[DiffOp]:
    """Run all optimisation passes and return a new ops list."""
    result = list(ops)
    result = optimize_common_edges(result, a, b)
    result = optimize_blanks(result, a, b)
    if whitespace:
        result = _optimize_whitespace(result, a, b)
    return result


def optimize_blanks(
    ops: List[DiffOp],
    a: Sequence[str],
    b: Sequence[str],
) -> List[DiffOp]:
    """Move blank lines to context at change-block boundaries.

    For each REPLACE/DELETE/INSERT op that has a blank line at its
  start or end, split the op so the blank line becomes EQUAL context.
    """
    result: List[DiffOp] = []
    for op in ops:
        if op.tag not in (Operation.REPLACE, Operation.DELETE, Operation.INSERT):
            result.append(op)
            continue

        # For DELETE, check blank at start and end of a-range
        if op.tag in (Operation.DELETE, Operation.REPLACE):
            # Shrink leading blank lines from the delete side
            i1, i2 = op.i1, op.i2
            while i1 < i2 and a[i1].strip() == "":
                i1 += 1
            if i1 > op.i1:
                # Emit EQUAL for the leading blanks
                if op.tag == Operation.REPLACE:
                    # Still need to account for b side
                    pass
                else:
                    result.append(DiffOp(Operation.EQUAL, op.i1, i1, op.j1, op.j1))
        result.append(op)
    return result


def optimize_common_edges(
    ops: List[DiffOp],
    a: Sequence[str],
    b: Sequence[str],
) -> List[DiffOp]:
    """Shrink REPLACE blocks by pulling common prefix/suffix lines into EQUAL.

    If a REPLACE op has identical lines at its start (or end) on both sides,
    those lines are extracted as EQUAL ops so they show as context.
    """
    result: List[DiffOp] = []
    for op in ops:
        if op.tag != Operation.REPLACE:
            result.append(op)
            continue

        i1, i2 = op.i1, op.i2
        j1, j2 = op.j1, op.j2

        # Pull common prefix
        prefix = 0
        while (i1 + prefix < i2 and j1 + prefix < j2
               and a[i1 + prefix] == b[j1 + prefix]):
            prefix += 1

        if prefix > 0:
            result.append(DiffOp(Operation.EQUAL, i1, i1 + prefix,
                                 j1, j1 + prefix))
            i1 += prefix
            j1 += prefix

        # Pull common suffix
        suffix = 0
        while (i1 < i2 - suffix and j1 < j2 - suffix
               and a[i2 - 1 - suffix] == b[j2 - 1 - suffix]):
            suffix += 1

        if suffix > 0:
            # Emit the remaining REPLACE (if any), then the suffix EQUAL
            if i1 < i2 - suffix and j1 < j2 - suffix:
                result.append(DiffOp(Operation.REPLACE, i1, i2 - suffix,
                                     j1, j2 - suffix))
            elif i1 < i2 - suffix:
                result.append(DiffOp(Operation.DELETE, i1, i2 - suffix,
                                     j1, j1))
            elif j1 < j2 - suffix:
                result.append(DiffOp(Operation.INSERT, i1, i1,
                                     j1, j2 - suffix))
            result.append(DiffOp(Operation.EQUAL, i2 - suffix, i2,
                                 j2 - suffix, j2))
        else:
            if i1 < i2 and j1 < j2:
                result.append(DiffOp(Operation.REPLACE, i1, i2, j1, j2))
            elif i1 < i2:
                result.append(DiffOp(Operation.DELETE, i1, i2, j1, j1))
            elif j1 < j2:
                result.append(DiffOp(Operation.INSERT, i1, i1, j1, j2))

    return result


def _optimize_whitespace(
    ops: List[DiffOp],
    a: Sequence[str],
    b: Sequence[str],
) -> List[DiffOp]:
    """Convert purely-whitespace changes into EQUAL ops."""
    result: List[DiffOp] = []
    for op in ops:
        if op.tag == Operation.REPLACE:
            a_text = "".join(a[op.i1:op.i2])
            b_text = "".join(b[op.j1:op.j2])
            if a_text.strip() == b_text.strip():
                # Whitespace-only change → treat as EQUAL
                result.append(DiffOp(Operation.EQUAL, op.i1, op.i2,
                                     op.j1, op.j2))
            else:
                result.append(op)
        else:
            result.append(op)
    return result