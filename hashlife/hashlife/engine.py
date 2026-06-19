"""Core Hashlife engine.

Nodes form a quadtree.  Every node covers a square region of side 2^level.
Level 0 is a single cell (alive or dead).  Level n>0 nodes have four children
(nw, ne, sw, se) each of level n-1.

Coordinate system
------------------
The root node is *centred* at the origin (0, 0).  A node of level L covers
the square [-2^(L-1), +2^(L-1)) on each axis.  The four children of a centred
parent are centred at (±2^(L-2), ±2^(L-2)); when we descend into a child we
remap coordinates accordingly.

Two key data structures make Hashlife fast:

* **Intern pool** — every structurally-identical node is represented by the
  same object, so subtree equality reduces to pointer equality.
* **Memo table** — ``_evolve(node)`` advances a level-n node by 2^(n-2)
  generations and returns the centred level-(n-1) result.  Because of
  interning the result depends only on the node's structure, so the memo
  cache is shared across every identical sub-pattern in the universe.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Leaves
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    """A level-0 leaf: a single square cell, either alive (1) or dead (0)."""

    alive: int  # 0 or 1

    @property
    def level(self) -> int:
        return 0

    @property
    def population(self) -> int:
        return self.alive

    @property
    def size(self) -> int:
        """Side length of the region this node covers (2**level)."""
        return 1


ALIVE = Cell(1)
DEAD = Cell(0)


# A quadtree node is either a Cell (level 0) or an interior Node (level >= 1).
QuadNode = Union[Cell, "Node"]


# ---------------------------------------------------------------------------
# Interior nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Node:
    """An interior quadtree node of level >= 1.

    The four children nw, ne, sw, se are each of level ``level-1`` and
    represent the north-west, north-east, south-west, south-east quadrants.
    """

    level: int
    nw: QuadNode
    ne: QuadNode
    sw: QuadNode
    se: QuadNode

    # Cached population (set by the interner).
    _population: int = 0

    @property
    def population(self) -> int:
        return self._population

    @property
    def size(self) -> int:
        return 1 << self.level


# ---------------------------------------------------------------------------
# Canonicalising interner + memoised evolution
# ---------------------------------------------------------------------------

class Hashlife:
    """A Hashlife engine: interning pool + memo table + universe management."""

    __slots__ = ("_pool", "_memo", "_root", "_gen")

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    def __init__(self, root_level: int = 4) -> None:
        if root_level < 3:
            raise ValueError("root_level must be >= 3")
        self._pool: Dict[tuple, QuadNode] = {}
        self._memo: Dict[int, QuadNode] = {}
        # Seed the interner with the two canonical leaves.
        self._pool[("cell", 0)] = DEAD
        self._pool[("cell", 1)] = ALIVE
        self._root: QuadNode = self._dead_node(root_level)
        self._gen = 0

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------

    @property
    def generation(self) -> int:
        return self._gen

    @property
    def root(self) -> QuadNode:
        return self._root

    @property
    def population(self) -> int:
        return self._root.population

    @property
    def pool_size(self) -> int:
        return len(self._pool)

    @property
    def memo_size(self) -> int:
        return len(self._memo)

    # ------------------------------------------------------------------
    # interning
    # ------------------------------------------------------------------

    def _make_cell(self, alive: int) -> Cell:
        return self._pool[("cell", alive)]

    def _intern(self, nw: QuadNode, ne: QuadNode, sw: QuadNode, se: QuadNode) -> Node:
        """Return the canonical node with the given four children."""
        level = nw.level + 1
        key = (level, id(nw), id(ne), id(sw), id(se))
        cached = self._pool.get(key)
        if cached is not None:
            return cached
        pop = nw.population + ne.population + sw.population + se.population
        node = Node(level=level, nw=nw, ne=ne, sw=sw, se=se, _population=pop)
        self._pool[key] = node
        return node

    def _dead_node(self, level: int) -> QuadNode:
        if level == 0:
            return DEAD
        sub = self._dead_node(level - 1)
        return self._intern(sub, sub, sub, sub)

    # ------------------------------------------------------------------
    # universe mutation
    # ------------------------------------------------------------------

    def set_cell(self, x: int, y: int, alive: bool = True) -> None:
        """Set the cell at logical coordinate (x, y).

        The root is grown (doubled) as needed so that (x, y) falls inside the
        inner half of the root — this guarantees a dead border so that births
        just outside the current population are not lost when evolving.
        """
        self._grow_to_contain(x, y)
        self._root = self._set_cell_rec(self._root, x, y, 1 if alive else 0)

    def add_pattern(self, cells, dx: int = 0, dy: int = 0) -> None:
        """Stamp a set of (x, y) live cells into the universe at offset."""
        for cx, cy in cells:
            self.set_cell(cx + dx, cy + dy, True)

    def _grow_to_contain(self, x: int, y: int) -> None:
        """Grow the root so that (x, y) lies inside the inner half."""
        while True:
            half = self._root.size // 2
            inner = half // 2
            if -inner <= x < inner and -inner <= y < inner:
                return
            self._root = self._expand(self._root)

    def _expand(self, node: QuadNode) -> Node:
        """Double the size of *node* by surrounding it with dead space."""
        d = self._dead_node(node.level)
        return self._intern(
            self._intern(d, d, d, node.nw),
            self._intern(d, d, node.ne, d),
            self._intern(d, node.sw, d, d),
            self._intern(node.se, d, d, d),
        )

    def _set_cell_rec(self, node: QuadNode, x: int, y: int, alive: int) -> QuadNode:
        if node.level == 0:
            return self._make_cell(alive)
        half = node.size // 2
        child_half = half // 2
        nw, ne, sw, se = node.nw, node.ne, node.sw, node.se
        if x < 0:
            if y < 0:
                nw = self._set_cell_rec(nw, x + child_half, y + child_half, alive)
            else:
                sw = self._set_cell_rec(sw, x + child_half, y - child_half, alive)
        else:
            if y < 0:
                ne = self._set_cell_rec(ne, x - child_half, y + child_half, alive)
            else:
                se = self._set_cell_rec(se, x - child_half, y - child_half, alive)
        return self._intern(nw, ne, sw, se)

    # ------------------------------------------------------------------
    # querying
    # ------------------------------------------------------------------

    def get_cell(self, x: int, y: int) -> int:
        """Return 1 if the cell at (x, y) is alive, else 0."""
        node = self._root
        half = node.size // 2
        if not (-half <= x < half and -half <= y < half):
            return 0
        while node.level > 0:
            half = node.size // 2
            child_half = half // 2
            if x < 0:
                if y < 0:
                    node = node.nw
                    x += child_half
                    y += child_half
                else:
                    node = node.sw
                    x += child_half
                    y -= child_half
            else:
                if y < 0:
                    node = node.ne
                    x -= child_half
                    y += child_half
                else:
                    node = node.se
                    x -= child_half
                    y -= child_half
        return node.alive

    def get_live_cells(self) -> set:
        """Return the set of (x, y) coordinates of every live cell.

        Coordinates use the centred frame: (0, 0) is the centre of the root.
        """
        result: set = set()
        half = self._root.size // 2
        self._collect_live(self._root, -half, -half, result)
        return result

    def _collect_live(self, node: QuadNode, x: int, y: int, out: set) -> None:
        if node.population == 0:
            return
        if node.level == 0:
            if node.alive:
                out.add((x, y))
            return
        half = node.size // 2
        self._collect_live(node.nw, x, y, out)
        self._collect_live(node.ne, x + half, y, out)
        self._collect_live(node.sw, x, y + half, out)
        self._collect_live(node.se, x + half, y + half, out)

    # ------------------------------------------------------------------
    # Hashlife evolution
    # ------------------------------------------------------------------

    def step(self, gens: int) -> None:
        """Advance the universe by *gens* generations.

        *gens* may be any non-negative integer.  It is decomposed into a sum
        of distinct powers of two; each power-of-two step is computed by a
        single recursive ``_evolve`` call at the appropriate level.
        """
        if gens < 0:
            raise ValueError("gens must be non-negative")
        if gens == 0:
            return
        remaining = gens
        bit = 0
        while remaining:
            if remaining & 1:
                self._advance_pow2(bit)
            remaining >>= 1
            bit += 1

    def run(self, gens: int) -> None:
        """Alias for :meth:`step`."""
        self.step(gens)

    def _advance_pow2(self, k: int) -> None:
        """Advance the universe by 2**k generations.

        A level-(k+2) node can be evolved by 2**k steps.  We grow the root
        to that level (plus one extra level of dead border) and evolve.
        """
        target_level = k + 2
        while self._root.level < target_level:
            self._root = self._expand(self._root)
        # Ensure a dead border so edge births are captured.
        self._root = self._expand(self._root)
        self._root = self._evolve(self._root)
        self._gen += 1 << k

    def _evolve(self, node: Node) -> QuadNode:
        """Evolve *node* by 2**(level-2) generations.

        Returns a node of level ``node.level - 1`` representing the centred
        region after the given number of steps.
        """
        if node.level < 2:
            raise ValueError(f"cannot evolve node at level {node.level}")

        # All-dead nodes evolve to all-dead — this also terminates recursion.
        if node.population == 0:
            return self._dead_node(node.level - 1)

        # Memo lookup — keyed by node identity (interning makes this correct).
        memo_key = id(node)
        cached = self._memo.get(memo_key)
        if cached is not None:
            return cached

        if node.level == 2:
            # Base case: 4x4 block evolved 1 step → centred 2x2 (level 1).
            result = self._evolve_base(node)
            self._memo[memo_key] = result
            return result

        # ------------------------------------------------------------------
        # Recursive case (level n > 2).
        #
        # Build the 9 level-(n-1) sub-nodes that tile a 3x3 arrangement
        # covering the parent node plus its immediate border:
        #
        #   n00 n01 n02
        #   n10 n11 n12
        #   n20 n21 n22
        #
        # Each centred 2x2 group of sub-nodes forms a level-n node.  Evolving
        # each yields a level-(n-1) result; the four results become the
        # children of the output node (level n-1).
        #
        # The recursion terminates because the 4 sub-nodes are *shifted*
        # relative to the parent — after a few levels they extend into the
        # dead border and become all-dead (caught by the population==0 check).
        # ------------------------------------------------------------------
        n00 = node.nw
        n01 = self._join_horizontal(node.nw, node.ne)
        n02 = node.ne
        n10 = self._join_vertical(node.nw, node.sw)
        n11 = self._centered_child(node)
        n12 = self._join_vertical(node.ne, node.se)
        n20 = node.sw
        n21 = self._join_horizontal(node.sw, node.se)
        n22 = node.se

        nw_res = self._evolve(self._intern(n00, n01, n10, n11))
        ne_res = self._evolve(self._intern(n01, n02, n11, n12))
        sw_res = self._evolve(self._intern(n10, n11, n20, n21))
        se_res = self._evolve(self._intern(n11, n12, n21, n22))

        result = self._intern(nw_res, ne_res, sw_res, se_res)
        self._memo[memo_key] = result
        return result

    # -- sub-node assembly helpers ---------------------------------------

    def _centered_child(self, node: Node) -> Node:
        """The level-(n-1) node at the centre of *node*.

        Built from the inner-corner children of the four quadrants.
        """
        return self._intern(node.nw.se, node.ne.sw, node.sw.ne, node.se.nw)

    def _join_horizontal(self, west: Node, east: Node) -> Node:
        """A level-(n-1) node spanning the vertical seam between *west* and *east*.

        Takes the east half of *west* and the west half of *east*.
        """
        return self._intern(west.ne.sw, east.nw.sw, west.se.nw, east.sw.nw)

    def _join_vertical(self, north: Node, south: Node) -> Node:
        """A level-(n-1) node spanning the horizontal seam between *north* and *south*.

        Takes the south half of *north* and the north half of *south*.
        """
        return self._intern(north.sw.se, north.se.se, south.nw.ne, south.ne.ne)

    # -- base case: evolve a level-2 (4x4) node by 1 step ----------------

    def _evolve_base(self, node: Node) -> QuadNode:
        """Evolve a level-2 (4x4) node by exactly one generation.

        Returns a level-1 (2x2) node representing the centred region.
        A 4x4 block contains all 8 neighbours of each of its 4 central
        cells, so a single Life step is computed directly.
        """
        grid = self._extract_4x4(node)
        result = [[0, 0], [0, 0]]
        for ry in range(2):
            for rx in range(2):
                gx, gy = rx + 1, ry + 1
                neigh = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        neigh += grid[gy + dy][gx + dx]
                alive = grid[gy][gx]
                if alive:
                    result[ry][rx] = 1 if neigh in (2, 3) else 0
                else:
                    result[ry][rx] = 1 if neigh == 3 else 0
        return self._intern(
            self._make_cell(result[0][0]),
            self._make_cell(result[0][1]),
            self._make_cell(result[1][0]),
            self._make_cell(result[1][1]),
        )

    @staticmethod
    def _extract_4x4(node: Node) -> list:
        """Extract the 4x4 bit-grid of a level-2 node.

        Layout (x → right, y → down)::

            nw[0] nw[1] ne[0] ne[1]
            nw[2] nw[3] ne[2] ne[3]
            sw[0] sw[1] se[0] se[1]
            sw[2] sw[3] se[2] se[3]

        where each leaf is indexed as [nw, ne, sw, se] → positions
        (0,0),(1,0),(0,1),(1,1).
        """
        grid = [[0] * 4 for _ in range(4)]
        for qy, quad in enumerate((node.nw, node.ne, node.sw, node.se)):
            qx = (qy % 2) * 2
            qyy = (qy // 2) * 2
            leaves = (quad.nw, quad.ne, quad.sw, quad.se)
            for ci, cell in enumerate(leaves):
                lx = ci % 2
                ly = ci // 2
                grid[qyy + ly][qx + lx] = cell.alive
        return grid