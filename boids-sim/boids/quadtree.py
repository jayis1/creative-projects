"""QuadTree spatial index for O(n log n) neighbor queries.

A region quadtree that recursively subdivides space into quadrants when a
node exceeds its capacity. Useful for non-uniform distributions where the
uniform-grid spatial hash wastes cells in empty regions.

Supports the same SpatialIndex protocol as SpatialHashGrid, so the two can
be used interchangeably.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from boids.spatial_index import SpatialIndex


@dataclass
class _QuadItem:
    """An object stored in the quadtree with its position."""

    obj: Any
    x: float
    y: float


class _QuadNode:
    """A single node in the quadtree — either a leaf or an internal node.

    Leaf nodes hold items directly; internal nodes have four child quadrants.
    """

    __slots__ = ("cx", "cy", "half", "capacity", "max_depth", "depth",
                 "items", "children")

    def __init__(
        self,
        cx: float,
        cy: float,
        half: float,
        capacity: int = 8,
        max_depth: int = 12,
        depth: int = 0,
    ):
        self.cx = cx
        self.cy = cy
        self.half = half  # half-width of this node's region
        self.capacity = capacity
        self.max_depth = max_depth
        self.depth = depth
        self.items: list[_QuadItem] = []
        self.children: list[_QuadNode] | None = None

    def _contains(self, x: float, y: float) -> bool:
        """Check if point (x, y) is within this node's bounds."""
        return (
            self.cx - self.half <= x <= self.cx + self.half
            and self.cy - self.half <= y <= self.cy + self.half
        )

    def _split(self) -> None:
        """Subdivide this node into four child quadrants."""
        q = self.half / 2
        d = self.depth + 1
        self.children = [
            _QuadNode(self.cx - q, self.cy - q, q, self.capacity, self.max_depth, d),
            _QuadNode(self.cx + q, self.cy - q, q, self.capacity, self.max_depth, d),
            _QuadNode(self.cx - q, self.cy + q, q, self.capacity, self.max_depth, d),
            _QuadNode(self.cx + q, self.cy + q, q, self.capacity, self.max_depth, d),
        ]
        # Redistribute existing items into children
        for item in self.items:
            self._insert_into_child(item)
        self.items = []

    def _insert_into_child(self, item: _QuadItem) -> None:
        """Insert an item into the appropriate child quadrant."""
        assert self.children is not None
        idx = 0
        if item.x > self.cx:
            idx |= 1
        if item.y > self.cy:
            idx |= 2
        self.children[idx].insert(item)

    def insert(self, item: _QuadItem) -> None:
        """Insert an item, subdividing if necessary."""
        if self.children is not None:
            self._insert_into_child(item)
            return
        self.items.append(item)
        if len(self.items) > self.capacity and self.depth < self.max_depth:
            self._split()

    def query(self, x: float, y: float, radius: float) -> Iterator[Any]:
        """Yield objects whose position may be within *radius* of (x, y).

        This is a coarse query — individual distance filtering is done by the
        caller. The quadtree returns all items in nodes that overlap the query
        circle's bounding box.
        """
        # Check if query circle overlaps this node's region
        dx = abs(x - self.cx) - self.half
        dy = abs(y - self.cy) - self.half
        if dx > radius or dy > radius:
            # bounding box doesn't overlap
            return

        if self.children is not None:
            for child in self.children:
                yield from child.query(x, y, radius)
        else:
            for item in self.items:
                yield item.obj

    def count(self) -> int:
        """Return total number of items in the tree."""
        if self.children is not None:
            return sum(c.count() for c in self.children)
        return len(self.items)

    def clear(self) -> None:
        """Clear all items and children."""
        self.items = []
        self.children = None


class QuadTree:
    """Region quadtree spatial index.

    A quadtree adaptively subdivides space based on object density, making it
    efficient for non-uniform distributions where objects cluster in certain
    regions but are sparse in others.

    Usage::

        qt = QuadTree(800, 600)
        qt.insert(boid, boid.pos.x, boid.pos.y)
        neighbors = list(qt.query(x, y, 50))

    Implements the :class:`~boids.spatial_index.SpatialIndex` protocol.
    """

    __slots__ = ("width", "height", "capacity", "max_depth", "_root", "_count")

    def __init__(
        self,
        width: float,
        height: float,
        capacity: int = 8,
        max_depth: int = 12,
    ):
        if width <= 0 or height <= 0:
            raise ValueError(f"width and height must be positive, got ({width}, {height})")
        if capacity < 1:
            raise ValueError(f"capacity must be at least 1, got {capacity}")
        self.width = float(width)
        self.height = float(height)
        self.capacity = capacity
        self.max_depth = max_depth
        self._root = _QuadNode(
            cx=width / 2, cy=height / 2,
            half=max(width, height) / 2,
            capacity=capacity,
            max_depth=max_depth,
        )
        self._count = 0

    def insert(self, obj: Any, x: float, y: float) -> None:
        """Insert *obj* at world position (x, y)."""
        self._root.insert(_QuadItem(obj, x, y))
        self._count += 1

    def query(self, x: float, y: float, radius: float) -> Iterator[Any]:
        """Yield objects whose node overlaps the query circle at (x, y)."""
        yield from self._root.query(x, y, radius)

    def clear(self) -> None:
        """Remove all objects from the tree."""
        self._root.clear()
        self._count = 0

    def __len__(self) -> int:
        return self._count

    def depth(self) -> int:
        """Return the maximum depth of the tree (0 = root only)."""
        def _max_depth(node: _QuadNode) -> int:
            if node.children is None:
                return node.depth
            return max(_max_depth(c) for c in node.children)
        return _max_depth(self._root)