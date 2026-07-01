"""
Diff output formatters: unified, context, and normal diff formats.

Also provides the :class:`Hunk` data class used by the patch applier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from .myers import DiffOp, Operation

__all__ = [
    "DiffHunk",
    "Hunk",
    "unified_diff",
    "context_diff",
    "normal_diff",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DiffHunk:
    """A logical hunk of changes grouped together for output."""

    a_start: int  # 1-based start line in old file (0 if empty)
    a_count: int  # number of old lines
    b_start: int  # 1-based start line in new file (0 if empty)
    b_count: int  # number of new lines
    lines: List[tuple] = field(default_factory=list)
    # Each entry in *lines* is (sign, text) where sign is
    # ' ' (equal), '-' (delete), '+' (insert), or '!' (replace marker).


@dataclass
class Hunk:
    """A parsed hunk (from a unified-diff patch) ready to apply.

    old_start, old_count : 1-based line range in the original file
    new_start, new_count : 1-based line range in the patched file
    lines : list of (sign, text) tuples
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[tuple] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_ops_to_hunks(
    ops: List[DiffOp],
    a: Sequence[str],
    b: Sequence[str],
    context: int,
) -> List[DiffHunk]:
    """Group *ops* into :class:`DiffHunk` objects with *context* lines
    of surrounding equality on each side.
    """
    hunks: List[DiffHunk] = []

    # Expand ops into per-line entries
    entries: List[tuple] = []  # (tag, i, j)
    for op in ops:
        if op.tag == Operation.EQUAL:
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                entries.append((Operation.EQUAL, i, j))
        elif op.tag == Operation.DELETE:
            for i in range(op.i1, op.i2):
                entries.append((Operation.DELETE, i, None))
        elif op.tag == Operation.INSERT:
            for j in range(op.j1, op.j2):
                entries.append((Operation.INSERT, None, j))
        elif op.tag == Operation.REPLACE:
            a_lines = list(range(op.i1, op.i2))
            b_lines = list(range(op.j1, op.j2))
            # Emit deletes then inserts
            for i in a_lines:
                entries.append((Operation.DELETE, i, None))
            for j in b_lines:
                entries.append((Operation.INSERT, None, j))

    # Find change segments
    change_indices = [
        idx for idx, (tag, _i, _j) in enumerate(entries)
        if tag != Operation.EQUAL
    ]
    if not change_indices:
        return []

    # Group change indices into contiguous blocks separated by > 2*context equal lines
    groups: List[List[int]] = [[change_indices[0]]]
    for idx in change_indices[1:]:
        if idx - groups[-1][-1] > 2 * context + 1:
            groups.append([idx])
        else:
            groups[-1].append(idx)

    for group in groups:
        first = group[0]
        last = group[-1]
        ctx_start = max(0, first - context)
        ctx_end = min(len(entries) - 1, last + context)

        hunk_lines: List[tuple] = []
        for idx in range(ctx_start, ctx_end + 1):
            tag, i, j = entries[idx]
            if tag == Operation.EQUAL:
                hunk_lines.append((" ", a[i]))
            elif tag == Operation.DELETE:
                hunk_lines.append(("-", a[i]))
            elif tag == Operation.INSERT:
                hunk_lines.append(("+", b[j]))

        # Compute hunk header (1-based)
        # old start/count
        old_indices = [
            entries[idx][1] for idx in range(ctx_start, ctx_end + 1)
            if entries[idx][0] in (Operation.EQUAL, Operation.DELETE)
        ]
        new_indices = [
            entries[idx][2] for idx in range(ctx_start, ctx_end + 1)
            if entries[idx][0] in (Operation.EQUAL, Operation.INSERT)
        ]

        if old_indices:
            a_start = old_indices[0] + 1
            a_count = old_indices[-1] - old_indices[0] + 1
        else:
            a_start = 0
            a_count = 0

        if new_indices:
            b_start = new_indices[0] + 1
            b_count = new_indices[-1] - new_indices[0] + 1
        else:
            b_start = 0
            b_count = 0

        hunks.append(DiffHunk(
            a_start=a_start, a_count=a_count,
            b_start=b_start, b_count=b_count,
            lines=hunk_lines,
        ))

    return hunks


# ---------------------------------------------------------------------------
# Unified diff
# ---------------------------------------------------------------------------


def unified_diff(
    a: Sequence[str],
    b: Sequence[str],
    *,
    fromfile: str = "a",
    tofile: str = "b",
    fromfiledate: str = "",
    tofiledate: str = "",
    context: int = 3,
    algorithm: str = "myers",
) -> List[str]:
    """Produce a unified diff between *a* and *b*.

    Returns a list of lines (without trailing newlines added beyond
    what the source lines already contain).
    """
    from .myers import myers_diff
    from .patience import patience_diff
    from .histogram import histogram_diff

    if algorithm == "myers":
        ops = myers_diff(a, b)
    elif algorithm == "patience":
        ops = patience_diff(a, b)
    elif algorithm == "histogram":
        ops = histogram_diff(a, b)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm!r}")

    result: List[str] = []

    header_from = f"--- {fromfile}"
    header_to = f"+++ {tofile}"
    if fromfiledate:
        header_from += f"\t{fromfiledate}"
    if tofiledate:
        header_to += f"\t{tofiledate}"

    hunks = _split_ops_to_hunks(ops, a, b, context)

    if not hunks:
        return []

    result.append(header_from)
    result.append(header_to)

    for hunk in hunks:
        result.append(
            f"@@ -{hunk.a_start},{hunk.a_count} +{hunk.b_start},{hunk.b_count} @@"
        )
        for sign, text in hunk.lines:
            result.append(f"{sign}{text}")

    return result


# ---------------------------------------------------------------------------
# Context diff
# ---------------------------------------------------------------------------


def context_diff(
    a: Sequence[str],
    b: Sequence[str],
    *,
    fromfile: str = "a",
    tofile: str = "b",
    fromfiledate: str = "",
    tofiledate: str = "",
    context: int = 3,
    algorithm: str = "myers",
) -> List[str]:
    """Produce a context-format diff between *a* and *b*."""
    from .myers import myers_diff
    from .patience import patience_diff
    from .histogram import histogram_diff

    if algorithm == "myers":
        ops = myers_diff(a, b)
    elif algorithm == "patience":
        ops = patience_diff(a, b)
    elif algorithm == "histogram":
        ops = histogram_diff(a, b)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm!r}")

    hunks = _split_ops_to_hunks(ops, a, b, context)
    if not hunks:
        return []

    result: List[str] = []
    result.append(f"*** {fromfile}" + (f"\t{fromfiledate}" if fromfiledate else ""))
    result.append(f"--- {tofile}" + (f"\t{tofiledate}" if tofiledate else ""))

    for hunk in hunks:
        result.append("***************")
        # Old section
        if hunk.a_count == 0:
            result.append(f"*** {hunk.a_start} ****")
        else:
            result.append(f"*** {hunk.a_start},{hunk.a_start + hunk.a_count - 1} ****")
        old_lines = [(s, t) for s, t in hunk.lines if s in (" ", "-")]
        # In context diff, unchanged context lines are just ' '
        # and removed lines are prefixed with '- '
        for sign, text in old_lines:
            if sign == "-":
                result.append(f"- {text}")
            else:
                result.append(f"  {text}")

        # New section
        if hunk.b_count == 0:
            result.append(f"--- {hunk.b_start} ----")
        else:
            result.append(f"--- {hunk.b_start},{hunk.b_start + hunk.b_count - 1} ----")
        new_lines = [(s, t) for s, t in hunk.lines if s in (" ", "+")]
        for sign, text in new_lines:
            if sign == "+":
                result.append(f"+ {text}")
            else:
                result.append(f"  {text}")

    return result


# ---------------------------------------------------------------------------
# Normal diff (RCS-style)
# ---------------------------------------------------------------------------


def normal_diff(
    a: Sequence[str],
    b: Sequence[str],
    *,
    algorithm: str = "myers",
) -> List[str]:
    """Produce a normal (RCS-style) diff between *a* and *b*."""
    from .myers import myers_diff
    from .patience import patience_diff
    from .histogram import histogram_diff

    if algorithm == "myers":
        ops = myers_diff(a, b)
    elif algorithm == "patience":
        ops = patience_diff(a, b)
    elif algorithm == "histogram":
        ops = histogram_diff(a, b)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm!r}")

    result: List[str] = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            continue
        a_len = op.i2 - op.i1
        b_len = op.j2 - op.j1
        a_start_1 = op.i1 + 1  # 1-based

        if op.tag == Operation.DELETE:
            if a_len == 1:
                result.append(f"{a_start_1}d{op.j1}")
            else:
                result.append(f"{a_start_1},{a_start_1 + a_len - 1}d{op.j1}")
            for i in range(op.i1, op.i2):
                result.append(f"< {a[i]}")
        elif op.tag == Operation.INSERT:
            if b_len == 1:
                result.append(f"{a_start_1 - 1}a{op.j1}")
            else:
                result.append(f"{a_start_1 - 1}a{op.j1},{op.j1 + b_len - 1}")
            for j in range(op.j1, op.j2):
                result.append(f"> {b[j]}")
        elif op.tag == Operation.REPLACE:
            if a_len == 1:
                result.append(f"{a_start_1}c{op.j1 + 1}")
            else:
                result.append(
                    f"{a_start_1},{a_start_1 + a_len - 1}c"
                    f"{op.j1 + 1},{op.j1 + b_len}"
                )
            for i in range(op.i1, op.i2):
                result.append(f"< {a[i]}")
            result.append("---")
            for j in range(op.j1, op.j2):
                result.append(f"> {b[j]}")

    return result