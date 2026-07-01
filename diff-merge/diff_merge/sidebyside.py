"""
Side-by-side diff rendering.

Produces a two-column visual diff where the old (left) and new (right)
versions are shown next to each other, with change markers and optional
ANSI colour highlighting.

Example output::

    line 1           | line 1
    - old line 2     | + new line 2
    line 3           | line 3

This is useful for code review and human-friendly inspection.
"""

from __future__ import annotations

from typing import Iterator, List, Sequence, Tuple

from .myers import DiffOp, Operation
from .patience import patience_diff
from .histogram import histogram_diff
from .lcs import lcs_diff

__all__ = ["side_by_side", "render_side_by_side"]


# ANSI colour codes ------------------------------------------------------------

_RED = "\033[31m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _get_diff_fn(algorithm: str = "myers"):
    """Return the diff function for *algorithm*."""
    if algorithm == "myers":
        from .myers import myers_diff
        return myers_diff
    if algorithm == "patience":
        return patience_diff
    if algorithm == "histogram":
        return histogram_diff
    if algorithm == "lcs":
        return lcs_diff
    raise ValueError(f"Unknown algorithm: {algorithm!r}")


def _expand_ops(ops: List[DiffOp]) -> List[Tuple[str, int | None, int | None]]:
    """Expand DiffOps into per-line ``(tag, i, j)`` tuples.

    ``i`` / ``j`` are ``None`` when the line does not exist on that side.
    """
    entries: List[Tuple[str, int | None, int | None]] = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                entries.append(("=", i, j))
        elif op.tag == Operation.DELETE:
            for i in range(op.i1, op.i2):
                entries.append(("-", i, None))
        elif op.tag == Operation.INSERT:
            for j in range(op.j1, op.j2):
                entries.append(("+", None, j))
        elif op.tag == Operation.REPLACE:
            a_lines = list(range(op.i1, op.i2))
            b_lines = list(range(op.j1, op.j2))
            # Interleave deletions and insertions for side-by-side display
            for idx in range(max(len(a_lines), len(b_lines))):
                ai = a_lines[idx] if idx < len(a_lines) else None
                bj = b_lines[idx] if idx < len(b_lines) else None
                if ai is not None and bj is not None:
                    entries.append(("!", ai, bj))
                elif ai is not None:
                    entries.append(("-", ai, None))
                else:
                    entries.append(("+", None, bj))
    return entries


def side_by_side(
    a: Sequence[str],
    b: Sequence[str],
    *,
    width: int = 80,
    algorithm: str = "myers",
    color: bool = False,
    show_line_numbers: bool = True,
) -> List[str]:
    """Produce a side-by-side visual diff.

    Parameters
    ----------
    a, b
        The two sequences of lines (without trailing newlines recommended).
    width
        Total output width in characters.  Each column gets roughly
        ``(width - separator) / 2`` characters.
    algorithm
        Which diff algorithm to use (``"myers"``, ``"patience"``,
        ``"histogram"``, ``"lcs"``).
    color
        If ``True``, add ANSI colour codes to highlight changes.
    show_line_numbers
        If ``True``, prefix each column with a 1-based line number.

    Returns
    -------
    list of str
        Lines of rendered output (no trailing newlines).
    """
    diff_fn = _get_diff_fn(algorithm)
    ops = diff_fn(a, b)
    entries = _expand_ops(ops)

    # Column widths
    sep = " │ "          # vertical separator
    line_num_w = 6       # e.g. "  123│"
    col_w = max(1, (width - len(sep) - (2 * line_num_w if show_line_numbers else 0)) // 2)

    result: List[str] = []

    def _fmt_line(text: str | None, line_num: int | None, side: str) -> str:
        """Format a single cell."""
        # Truncate long lines
        display = (text or "")
        if len(display) > col_w:
            display = display[: col_w - 1] + "…"

        pad = col_w - len(display)
        if show_line_numbers:
            if line_num is not None:
                ln = f"{line_num:>{line_num_w - 1}}│"
            else:
                ln = " " * line_num_w
        else:
            ln = ""

        return f"{ln}{display}{' ' * pad}"

    def _colorize(text: str, tag: str, side: str) -> str:
        if not color:
            return text
        if tag == "-":
            return f"{_RED}{text}{_RESET}"
        if tag == "+":
            return f"{_GREEN}{text}{_RESET}"
        if tag == "!":
            if side == "L":
                return f"{_RED}{text}{_RESET}"
            return f"{_GREEN}{text}{_RESET}"
        return f"{_DIM}{text}{_RESET}" if False else text  # equal: no colour

    for tag, ai, bj in entries:
        if tag == "=":
            left = _fmt_line(a[ai] if ai is not None else None, ai, "L")
            right = _fmt_line(b[bj] if bj is not None else None, bj, "R")
        elif tag == "-":
            left = _fmt_line(a[ai] if ai is not None else None, ai, "L")
            right = _fmt_line(None, None, "R")
        elif tag == "+":
            left = _fmt_line(None, None, "L")
            right = _fmt_line(b[bj] if bj is not None else None, bj, "R")
        elif tag == "!":
            left = _fmt_line(a[ai] if ai is not None else None, ai, "L")
            right = _fmt_line(b[bj] if bj is not None else None, bj, "R")
        else:
            continue

        left_c = _colorize(left, tag, "L")
        right_c = _colorize(right, tag, "R")

        result.append(f"{left_c}{sep}{right_c}")

    return result


def render_side_by_side(
    filepath_a: str,
    filepath_b: str,
    *,
    width: int = 80,
    algorithm: str = "myers",
    color: bool = False,
) -> List[str]:
    """Read two files and return a side-by-side diff."""
    from pathlib import Path

    def _read(path: str) -> List[str]:
        return Path(path).read_text(encoding="utf-8").splitlines()

    a = _read(filepath_a)
    b = _read(filepath_b)
    return side_by_side(a, b, width=width, algorithm=algorithm, color=color)