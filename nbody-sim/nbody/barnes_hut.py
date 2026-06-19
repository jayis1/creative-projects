"""Barnes–Hut quadtree for O(N log N) N-body force evaluation.

A :class:`BHTree` recursively partitions 2-D space into four quadrants. Each
node stores the center of mass, total mass, and bounding square of the bodies
it contains. When evaluating the force on a body, a node whose angular size
``s / d`` is smaller than the opening parameter ``theta`` is treated as a
single point mass — the defining approximation of Barnes–Hut.

The tree is built once per step and discarded afterwards (the integrator
constructs a fresh tree each step so positions stay consistent).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .vec import Vec2, add, scale, sub

# A softening length (Plummer) keeps accelerations finite at very small
# separations. The value is exposed via the :class:`BHTree` constructor so the
# simulator can set it; see :data:`DEFAULT_SOFTENING`.
DEFAULT_SOFTENING = 0.5
# A floor on the interaction distance; below this we use the softening
# length to avoid division-by-zero / singular accelerations.
_MIN_DIST = 1e-12


@dataclass
class _Region:
    """Axis-aligned square region of space owned by a tree node."""

    cx: float  # center x of the square
    cy: float  # center y of the square
    size: float  # full side length of the square

    def quadrant_of(self, x: float, y: float) -> int:
        """Return the quadrant index 0=NW, 1=NE, 2=SW, 3=SE containing (x,y)."""
        # NB: comparisons are against the center; an exactly-on-center body
        # is assigned to the *east* and *south* quadrants deterministically.
        right = x >= self.cx
        bottom = y >= self.cy
        return (1 if right else 0) | (2 if bottom else 0)

    def child(self, quad: int) -> "_Region":
        half = self.size * 0.5
        off_x = half * 0.5 if (quad & 1) else -half * 0.5
        off_y = half * 0.5 if (quad & 2) else -half * 0.5
        return _Region(self.cx + off_x, self.cy + off_y, half)


@dataclass
class _Node:
    """A single quadtree node (leaf or internal)."""

    region: _Region
    # Aggregated mass properties (set for both leaves and internal nodes).
    mass: float = 0.0
    com_x: float = 0.0
    com_y: float = 0.0
    # If leaf: a single body lives here (``body`` is set, children are None).
    # If internal: all four children are populated, ``body`` is None.
    body: Optional[Tuple[float, float, float]] = None  # (x, y, mass)
    children: Optional[List[Optional["_Node"]]] = None

    @property
    def is_leaf(self) -> bool:
        return self.children is None

    @property
    def is_empty(self) -> bool:
        return self.mass == 0.0 and self.body is None and self.children is None


class BHTree:
    """Barnes–Hut quadtree force evaluator.

    Parameters
    ----------
    theta:
        Opening angle. Smaller → more accurate, slower (``1.0`` is the classic
        threshold; ``0`` reduces to brute force).
    softening:
        Plummer softening length squared is ``softening**2``. Two bodies closer
        than this distance see a softened gravitational pull which prevents
        unbounded accelerations.
    G:
        Gravitational constant (default 1.0; set to taste via the simulator).
    """

    def __init__(
        self,
        theta: float = 0.5,
        softening: float = DEFAULT_SOFTENING,
        G: float = 1.0,
    ) -> None:
        if not 0.0 <= theta <= 2.0:
            raise ValueError(f"theta must be in [0, 2], got {theta}")
        if softening < 0.0:
            raise ValueError(f"softening must be non-negative, got {softening}")
        self.theta = theta
        self.soft = softening
        self.soft_sq = softening * softening
        self.G = G
        self.root: Optional[_Node] = None
        self._n_bodies = 0

    # -- construction ---------------------------------------------------

    def build(self, bodies) -> None:
        """Insert ``bodies`` (iterable of (x, y, mass)) into a fresh tree."""
        self.root = None
        self._n_bodies = 0
        body_list = list(bodies)
        if not body_list:
            return
        # Compute the bounding square containing all bodies with a small
        # margin so that bodies sitting exactly on the edge still classify
        # cleanly into one of the quadrants.
        xs = [b[0] for b in body_list]
        ys = [b[1] for b in body_list]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        cx = 0.5 * (minx + maxx)
        cy = 0.5 * (miny + maxy)
        size = max(maxx - minx, maxy - miny)
        # Guard against the degenerate all-same-point case.
        if size <= 0.0:
            size = 2.0 * max(1.0, self.soft)
        # Add a 1% margin so bodies aren't on the very edge.
        size *= 1.01
        self.root = _Node(_Region(cx, cy, size))
        for b in body_list:
            self._insert(self.root, b)
            self._n_bodies += 1

    def _insert(self, node: "_Node", body: Tuple[float, float, float]) -> None:
        """Recursively insert ``body`` into ``node``, subdividing as needed."""
        bx, by, bm = body
        # Update aggregate mass / center-of-mass.
        old_mass = node.mass
        node.mass += bm
        # com = (old*old_com + m*body) / new
        if old_mass == 0.0:
            node.com_x = bx
            node.com_y = by
        else:
            node.com_x = (old_mass * node.com_x + bm * bx) / node.mass
            node.com_y = (old_mass * node.com_y + bm * by) / node.mass

        if node.is_leaf:
            if node.body is None:
                # Empty leaf: stash the body and we're done.
                node.body = body
                return
            # Occupied leaf: must subdivide. Promote the existing body and the
            # new body into the four children.
            existing = node.body
            node.body = None
            node.children = [None, None, None, None]
            # Re-insert the existing body first, then the new one. Both should
            # land in distinct sub-quadrants unless they coincide; we guard
            # against infinite recursion via a depth/size check.
            self._safe_insert(node, existing)
            self._safe_insert(node, body)
        else:
            # Internal node: descend into the matching child.
            quad = node.region.quadrant_of(bx, by)
            child = node.children[quad]
            if child is None:
                child = _Node(node.region.child(quad))
                node.children[quad] = child
            self._insert(child, body)

    def _safe_insert(self, node: "_Node", body: Tuple[float, float, float]) -> None:
        """Insert while preventing infinite subdivision of co-located bodies.

        If two bodies are *exactly* coincident they will keep forcing ever
        smaller sub-quadrants; we detect the case where the child region size
        drops below a tiny epsilon and stop subdividing, leaving the second
        body in the parent leaf. Force evaluation still works because the
        parent's center-of-mass aggregates both bodies.
        """
        bx, by, bm = body
        quad = node.region.quadrant_of(bx, by)
        child_region = node.region.child(quad)
        # If the region is tiny, treat this node as a "bucket leaf": store the
        # body directly without further subdivision. We track extra bodies in
        # a list attached to the node.
        if child_region.size < 1e-9 * max(1.0, self.soft):
            # Co-located bucket: append to node._bucket if present.
            bucket = getattr(node, "_bucket", None)
            if bucket is None:
                bucket = []
                # Use object.__setattr__ because the dataclass doesn't define
                # this attribute; we attach it lazily.
                object.__setattr__(node, "_bucket", bucket)
            bucket.append(body)
            return
        child = node.children[quad]
        if child is None:
            child = _Node(child_region)
            node.children[quad] = child
        self._insert(child, body)

    # -- force evaluation -----------------------------------------------

    def force_on(self, body: Tuple[float, float, float]) -> Tuple[float, float]:
        """Return the gravitational acceleration on ``body`` (ax, ay).

        Uses the Barnes–Hut opening criterion: a node is treated as a single
        point mass if ``size / distance < theta``.
        """
        if self.root is None or self.root.mass == 0.0:
            return (0.0, 0.0)
        return self._force(self.root, body)

    def _force(
        self, node: "_Node", body: Tuple[float, float, float]
    ) -> Tuple[float, float]:
        bx, by, _bm = body
        dx = node.com_x - bx
        dy = node.com_y - by
        d_sq = dx * dx + dy * dy
        # Avoid self-interaction: if the node is a leaf containing exactly
        # this body, skip it.
        if node.is_leaf and node.body is not None:
            sbx, sby, _sbm = node.body
            if sbx == bx and sby == by:
                # Could be a co-located *other* body; check the bucket too.
                return self._bucket_force(node, body)
        # Barnes–Hut opening decision.
        size = node.region.size
        # Use a softened distance to avoid singularities.
        r = math.sqrt(d_sq + self.soft_sq)
        if r < _MIN_DIST:
            r = _MIN_DIST
        if (size / r) < self.theta or node.is_leaf:
            # Treat as point mass.
            inv_r3 = 1.0 / (r * r * r)
            f = self.G * node.mass * inv_r3
            return (f * dx, f * dy)
        # Otherwise descend into children.
        ax = ay = 0.0
        for child in node.children:  # type: ignore[union-attr]
            if child is None:
                continue
            cx, cy = self._force(child, body)
            ax += cx
            ay += cy
        # Include any bucketed co-located bodies on this internal node.
        bx_f, by_f = self._bucket_force(node, body)
        return (ax + bx_f, ay + by_f)

    def _bucket_force(
        self, node: "_Node", body: Tuple[float, float, float]
    ) -> Tuple[float, float]:
        """Force contribution from co-located bucket bodies, if any."""
        bucket = getattr(node, "_bucket", None)
        if not bucket:
            return (0.0, 0.0)
        bx, by, _bm = body
        ax = ay = 0.0
        for (ox, oy, om) in bucket:
            if ox == bx and oy == by:
                continue
            dx = ox - bx
            dy = oy - by
            r = math.sqrt(dx * dx + dy * dy + self.soft_sq)
            if r < _MIN_DIST:
                r = _MIN_DIST
            inv_r3 = 1.0 / (r * r * r)
            f = self.G * om * inv_r3
            ax += f * dx
            ay += f * dy
        return (ax, ay)

    # -- diagnostics ----------------------------------------------------

    @property
    def n_bodies(self) -> int:
        return self._n_bodies

    def depth(self) -> int:
        """Maximum depth of the tree (root = 1)."""
        return self._depth(self.root)

    def _depth(self, node: Optional["_Node"]) -> int:
        if node is None:
            return 0
        if node.is_leaf:
            return 1
        return 1 + max(self._depth(c) for c in node.children)  # type: ignore[union-attr]


__all__ = ["BHTree"]