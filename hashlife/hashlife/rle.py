"""RLE (Run-Length Encoded) pattern parsing for Conway's Game of Life.

The RLE format is the de-facto interchange format for Life patterns
(see https://conwaylife.com/wiki/Run_Length_Encoded).

A minimal example — the Gosper glider gun::

    #N Gosper Glider Gun
    x = 36, y = 9, rule = B3/S23
    24bo11b$22bobo11b$12b2o6b2o12b2o$11bo3bo4b2o12b2o$2o8bo5bo3b2o$2o8bo3b
    o4b2o$10b2o6b2o12b2o$22bobo11b$24bo!

This module parses that format into a set of (x, y) live-cell coordinates
and also provides a tiny ``pattern_to_set`` helper for the simpler "o"/"b"
inline notation used in tests.
"""

from __future__ import annotations

import re
from typing import Set, Tuple


def load_rle(text: str) -> Set[Tuple[int, int]]:
    """Parse an RLE pattern string and return the set of live (x, y) cells.

    Parameters
    ----------
    text : str
        Full contents of an RLE file (header lines, ``#`` comments, body).

    Returns
    -------
    set of (int, int)
        Coordinates of every live cell, with (0, 0) at the top-left corner
        of the pattern's bounding box.

    Raises
    ------
    ValueError
        If the RLE body is malformed (bad run count, unknown tag character,
        or missing ``!`` terminator).
    """
    if not isinstance(text, str):
        raise TypeError("RLE input must be a string")

    # Strip comment / header lines, keep only the body (runs of [0-9] and
    # the tag chars b o $ ! with whitespace allowed).
    body_chars: list = []
    found_header = False
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s.startswith("x"):
            # header line — we parse it but don't strictly need its values.
            found_header = True
            continue
        body_chars.append(s)

    if not body_chars:
        raise ValueError("RLE body is empty")

    body = "".join(body_chars)

    cells: Set[Tuple[int, int]] = set()
    x, y = 0, 0
    count = 0
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch.isdigit():
            # accumulate run-length prefix
            j = i
            while j < n and body[j].isdigit():
                j += 1
            count = int(body[i:j])
            i = j
            continue
        if ch == "!" :
            break
        run = count if count > 0 else 1
        if ch == "b":
            x += run
        elif ch == "o":
            for _ in range(run):
                cells.add((x, y))
                x += 1
        elif ch == "$":
            y += run
            x = 0
        elif ch in " \t\r\n":
            pass  # whitespace inside body is ignored
        else:
            raise ValueError(f"Unknown RLE tag character: {ch!r}")
        count = 0
        i += 1

    return cells


def pattern_to_set(pattern: str, alive: str = "o") -> Set[Tuple[int, int]]:
    """Parse a simple multi-line ASCII pattern into a set of live cells.

    Each character is one cell; ``alive`` (default ``'o'``) marks a live cell
    and any other non-newline character (commonly ``.`` or ``b``) is dead.
    Lines need not be equal length.  Useful for embedding test patterns
    directly in source code.

    >>> sorted(pattern_to_set("oo\\n.o"))
    [(0, 0), (1, 0), (1, 1)]
    """
    cells: Set[Tuple[int, int]] = set()
    for y, line in enumerate(pattern.splitlines()):
        for x, ch in enumerate(line):
            if ch == alive:
                cells.add((x, y))
    return cells


def to_rle(cells) -> str:
    """Serialise a set of (x, y) cells to a minimal RLE string."""
    if not cells:
        return "x = 0, y = 0\n!\n"
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    width = maxx - minx + 1
    grid = [["b"] * width for _ in range(maxy - miny + 1)]
    for cx, cy in cells:
        grid[cy - miny][cx - minx] = "o"

    out = [f"x = {width}, y = {maxy - miny + 1}, rule = B3/S23"]
    line = []
    line_len = 0
    for row in grid:
        run = 0
        prev = None
        for ch in row + ["$"]:
            if ch == prev:
                run += 1
            else:
                if prev is not None:
                    tag = prev
                    token = (str(run) if run > 1 else "") + tag
                    line.append(token)
                    line_len += len(token)
                    if line_len > 68:
                        out.append("".join(line))
                        line = []
                        line_len = 0
                prev = ch
                run = 1
    out.append("".join(line) + "!")
    return "\n".join(out) + "\n"