"""Well-known CA patterns (oscillators, spaceships, still lifes, etc.).

All patterns are defined as lists of (x, y) coordinates relative to an origin,
so they can be placed onto any grid via ``CellularAutomaton.set_cell``.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

Pattern = List[Tuple[int, int]]


# ---------------------------------------------------------------------------
# Still lifes
# ---------------------------------------------------------------------------

BLOCK: Pattern = [(0, 0), (1, 0), (0, 1), (1, 1)]
BEEHIVE: Pattern = [(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (2, 2)]
LOAF: Pattern = [(1, 0), (2, 0), (0, 1), (3, 1), (2, 2), (3, 2), (1, 3)]
SHIP: Pattern = [(0, 0), (1, 0), (0, 1), (2, 1), (1, 2), (2, 2)]
BOAT: Pattern = [(0, 0), (1, 0), (0, 1), (2, 1), (1, 2)]
TUB: Pattern = [(1, 0), (0, 1), (2, 1), (1, 2)]


# ---------------------------------------------------------------------------
# Oscillators
# ---------------------------------------------------------------------------

BLINKER: Pattern = [(0, 0), (1, 0), (2, 0)]
TOAD: Pattern = [(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1)]
BEACON: Pattern = [(0, 0), (1, 0), (0, 1), (1, 1), (2, 2), (3, 2), (2, 3), (3, 3)]
PULSAR: Pattern = [
    (2, 0), (3, 0), (4, 0), (8, 0), (9, 0), (10, 0),
    (0, 2), (5, 2), (7, 2), (12, 2),
    (0, 3), (5, 3), (7, 3), (12, 3),
    (0, 4), (5, 4), (7, 4), (12, 4),
    (2, 5), (3, 5), (4, 5), (8, 5), (9, 5), (10, 5),
    (2, 7), (3, 7), (4, 7), (8, 7), (9, 7), (10, 7),
    (0, 8), (5, 8), (7, 8), (12, 8),
    (0, 9), (5, 9), (7, 9), (12, 9),
    (0, 10), (5, 10), (7, 10), (12, 10),
    (2, 12), (3, 12), (4, 12), (8, 12), (9, 12), (10, 12),
]
# The pentadecathlon is a period-15 oscillator.
# RLE: 2bo4bo$2ob4ob2o$2bo4bo! (from LifeWiki)
# Row 0: 2 dead, 1 alive, 4 dead, 1 alive  →  cells at x=2 and x=7
# Row 1: 2 alive, 1 dead, 4 alive, 1 dead, 2 alive → cells at x=0,1,3,4,5,6,8,9
# Row 2: same as row 0 → cells at x=2 and x=7
PENTADECATHLON: Pattern = [
    (2, 0), (7, 0),
    (0, 1), (1, 1), (3, 1), (4, 1), (5, 1), (6, 1), (8, 1), (9, 1),
    (2, 2), (7, 2),
]


# ---------------------------------------------------------------------------
# Spaceships
# ---------------------------------------------------------------------------

GLIDER: Pattern = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]
LWSS: Pattern = [  # light-weight spaceship
    (1, 0), (4, 0),
    (0, 1),
    (0, 2), (3, 2),
    (0, 3), (1, 3), (2, 3),
]
MWSS: Pattern = [  # middle-weight spaceship
    (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
    (5, 1),
    (5, 2), (0, 2),
    (0, 3), (4, 3),
]
HWSS: Pattern = [  # heavy-weight spaceship
    (1, 0), (2, 0), (3, 0), (4, 0), (5, 0),
    (0, 1), (6, 1),
    (0, 2), (6, 2),
    (0, 3), (5, 3),
    (2, 4), (3, 4),
]


# ---------------------------------------------------------------------------
# Guns & methuselahs
# ---------------------------------------------------------------------------

GOSPER_GLIDER_GUN: Pattern = [
    (0, 4), (0, 5),
    (1, 4), (1, 5),
    (10, 4), (10, 5), (10, 6),
    (11, 3), (11, 7),
    (12, 2), (12, 8),
    (13, 2), (13, 8),
    (14, 5),
    (15, 3), (15, 7),
    (16, 4), (16, 5), (16, 6),
    (17, 5),
    (20, 2), (20, 3), (20, 4),
    (21, 2), (21, 3), (21, 4),
    (22, 1), (22, 5),
    (24, 0), (24, 1), (24, 5), (24, 6),
    (34, 2), (34, 3),
    (35, 2), (35, 3),
]

R_PENTOMINO: Pattern = [(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)]
DIEHARD: Pattern = [
    (6, 0),
    (0, 1), (1, 1),
    (1, 2), (5, 2), (6, 2), (7, 2),
]
ACORN: Pattern = [(1, 0), (3, 1), (0, 2), (1, 2), (4, 2), (5, 2), (6, 2)]


PATTERNS: Dict[str, Pattern] = {
    # still lifes
    "block": BLOCK,
    "beehive": BEEHIVE,
    "loaf": LOAF,
    "ship": SHIP,
    "boat": BOAT,
    "tub": TUB,
    # oscillators
    "blinker": BLINKER,
    "toad": TOAD,
    "beacon": BEACON,
    "pulsar": PULSAR,
    "pentadecathlon": PENTADECATHLON,
    # spaceships
    "glider": GLIDER,
    "lwss": LWSS,
    "mwss": MWSS,
    "hwss": HWSS,
    # guns
    "gosper_gun": GOSPER_GLIDER_GUN,
    # methuselahs
    "r_pentomino": R_PENTOMINO,
    "diehard": DIEHARD,
    "acorn": ACORN,
}


def get_pattern(name: str) -> Pattern:
    """Look up a builtin pattern by name (case-insensitive)."""
    if name in PATTERNS:
        return PATTERNS[name]
    lower = {k.lower(): v for k, v in PATTERNS.items()}
    if name.lower() in lower:
        return lower[name.lower()]
    raise KeyError(f"Unknown pattern: {name!r}")


def place_pattern(ca, pattern: Pattern, x: int = 0, y: int = 0) -> None:
    """Place ``pattern`` onto CA ``ca`` with top-left corner at (x, y)."""
    for dx, dy in pattern:
        ca.set_cell(x + dx, y + dy, 1)


def parse_rle(rle: str) -> Pattern:
    """Parse a minimal Run Length Encoded (RLE) Game of Life string.

    Supports the subset: ``b`` = dead, ``o`` = alive, ``$`` = row end,
    ``!`` = end of pattern.  Run-length prefixes are supported (e.g. ``3o``).

    Example::

        >>> parse_rle("bo$2bo$3o!")
        [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]
    """
    pattern: Pattern = []
    x = y = 0
    num = ""
    for ch in rle.strip():
        if ch.isdigit():
            num += ch
        elif ch == "b":
            count = int(num) if num else 1
            x += count
            num = ""
        elif ch in ("o",):
            count = int(num) if num else 1
            for _ in range(count):
                pattern.append((x, y))
                x += 1
            num = ""
        elif ch == "$":
            y += int(num) if num else 1
            x = 0
            num = ""
        elif ch == "!":
            break
        # ignore other chars (comments etc. — minimal parser)
    return pattern


def pattern_bounds(pattern: Pattern) -> Tuple[int, int, int, int]:
    """Return (min_x, min_y, max_x, max_y) of the pattern."""
    xs = [p[0] for p in pattern]
    ys = [p[1] for p in pattern]
    return min(xs), min(ys), max(xs), max(ys)