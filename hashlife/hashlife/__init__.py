"""Hashlife — Conway's Game of Life via the memoized-quadtree Hashlife algorithm.

This package implements Bill Gosper's Hashlife algorithm: the infinite Life
universe is represented as a quadtree of canonical (interned) nodes, and the
future of each node is computed recursively with memoization, giving effectively
O(log n) time per power-of-two step.

Public API:
    Hashlife       — the engine (intern pool + memo table + root manipulation)
    Cell           — a single live/dead cell (leaf of the quadtree)
    Node           — an interior quadtree node
    load_rle       — parse a standard Game of Life RLE pattern string
    pattern_to_set — convert a pattern string to a set of (x, y) live cells
    render         — ASCII-render a region of the universe
"""

from .engine import Hashlife, Node, Cell
from .rle import load_rle, pattern_to_set
from .render import render

__all__ = [
    "Hashlife",
    "Node",
    "Cell",
    "load_rle",
    "pattern_to_set",
    "render",
]

__version__ = "1.0.0"