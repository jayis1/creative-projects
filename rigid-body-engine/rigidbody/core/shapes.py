"""Collision shapes: circles, convex polygons, and AABBs.

All shapes are *value* objects — they carry only geometry, not state.  A
:class:`~rigidbody.core.body.RigidBody` owns a shape reference and supplies
the position/orientation needed to compute world-space geometry on demand.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .vec2 import Vec2

__all__ = ["Shape", "Circle", "Polygon", "AABB"]


class Shape:
    """Base class for collision shapes."""

    shape_type: str = "base"

    def compute_mass(self, density: float) -> Tuple[float, float]:
        """Return ``(mass, rotational_inertia)`` for this shape at *density*."""
        raise NotImplementedError

    def compute_aabb(self, position: Vec2, angle: float) -> "AABB":
        raise NotImplementedError


class Circle(Shape):
    """A circle of a given radius centred at the local origin.

    ``radius`` must be positive.  Optionally a local offset can be given so the
    circle is not centred on the body origin — useful for compound shapes.
    """

    shape_type = "circle"

    def __init__(self, radius: float, offset: Vec2 | None = None) -> None:
        if radius <= 0.0:
            raise ValueError(f"circle radius must be positive, got {radius}")
        self.radius = float(radius)
        self.offset = offset if offset is not None else Vec2.zero()

    def compute_mass(self, density: float) -> Tuple[float, float]:
        # I = (1/2) m r^2  for a solid disk.
        mass = math.pi * self.radius * self.radius * density
        inertia = 0.5 * mass * self.radius * self.radius
        # Parallel-axis theorem for the offset.
        if self.offset.length_sq() > 0.0:
            inertia += mass * self.offset.length_sq()
        return mass, inertia

    def compute_aabb(self, position: Vec2, angle: float) -> "AABB":
        world_center = self.offset.rotate(angle) + position
        r = self.radius
        return AABB(
            Vec2(world_center.x - r, world_center.y - r),
            Vec2(world_center.x + r, world_center.y + r),
        )


class Polygon(Shape):
    """A convex polygon given by counter-clockwise local vertices.

    Vertices are re-centred on the polygon centroid in the constructor so the
    local origin coincides with the centre of mass (this keeps rotation look
    natural).  The original vertex order is preserved.
    """

    shape_type = "polygon"

    def __init__(self, vertices: Sequence[Vec2]) -> None:
        if len(vertices) < 3:
            raise ValueError("polygon needs at least 3 vertices")
        # Validate convexity & CCW orientation, and store a defensive copy.
        verts = [Vec2(v.x, v.y) for v in vertices]
        if not _is_convex_ccw(verts):
            verts = _ensure_ccw(verts)
            if not _is_convex_ccw(verts):
                raise ValueError("polygon is not convex")
        # Re-centre on centroid so rotation pivots around the CoM.
        centroid = _polygon_centroid(verts)
        self.vertices = [v - centroid for v in verts]
        # Precompute normals (outward) for each edge — used by SAT.
        self.normals: List[Vec2] = []
        n = len(self.vertices)
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            edge = v2 - v1
            # Outward normal for a CCW polygon: rotate edge -90° → (y, -x)
            normal = Vec2(edge.y, -edge.x).normalize()
            self.normals.append(normal)

    def compute_mass(self, density: float) -> Tuple[float, float]:
        area, inertia = 0.0, 0.0
        n = len(self.vertices)
        for i in range(n):
            v0 = self.vertices[i]
            v1 = self.vertices[(i + 1) % n]
            cross = abs(v0.cross(v1))
            area += cross
            inertia += cross * (v0.dot(v0) + v0.dot(v1) + v1.dot(v1))
        area *= 0.5
        inertia *= density / 12.0
        mass = area * density
        return mass, inertia

    def compute_aabb(self, position: Vec2, angle: float) -> "AABB":
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        xs = []
        ys = []
        for v in self.vertices:
            wx = v.x * cos_a - v.y * sin_a + position.x
            wy = v.x * sin_a + v.y * cos_a + position.y
            xs.append(wx)
            ys.append(wy)
        return AABB(Vec2(min(xs), min(ys)), Vec2(max(xs), max(ys)))

    # --- convenience factory helpers --------------------------------- #
    @classmethod
    def box(cls, width: float, height: float) -> "Polygon":
        """Create an axis-aligned rectangle centred on the origin."""
        if width <= 0.0 or height <= 0.0:
            raise ValueError("box dimensions must be positive")
        hw, hh = width * 0.5, height * 0.5
        return cls([Vec2(-hw, -hh), Vec2(hw, -hh), Vec2(hw, hh), Vec2(-hw, hh)])

    @classmethod
    def regular_polygon(cls, sides: int, radius: float) -> "Polygon":
        if sides < 3:
            raise ValueError("need at least 3 sides")
        if radius <= 0.0:
            raise ValueError("radius must be positive")
        verts = []
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            verts.append(Vec2(math.cos(a) * radius, math.sin(a) * radius))
        return cls(verts)


class AABB:
    """Axis-aligned bounding box — a plain min/max pair.

    Used by the broad phase and for quick rejection tests.  Not a collision
    *shape*; it carries no mass data.
    """

    __slots__ = ("min", "max")

    def __init__(self, min_pt: Vec2, max_pt: Vec2) -> None:
        self.min = min_pt
        self.max = max_pt

    def overlaps(self, other: "AABB") -> bool:
        return (
            self.min.x <= other.max.x
            and self.max.x >= other.min.x
            and self.min.y <= other.max.y
            and self.max.y >= other.min.y
        )

    def combine(self, other: "AABB") -> "AABB":
        return AABB(
            Vec2(min(self.min.x, other.min.x), min(self.min.y, other.min.y)),
            Vec2(max(self.max.x, other.max.x), max(self.max.y, other.max.y)),
        )

    def contains(self, point: Vec2) -> bool:
        return (
            self.min.x <= point.x <= self.max.x
            and self.min.y <= point.y <= self.max.y
        )

    @property
    def width(self) -> float:
        return self.max.x - self.min.x

    @property
    def height(self) -> float:
        return self.max.y - self.min.y

    @property
    def center(self) -> Vec2:
        return Vec2(
            (self.min.x + self.max.x) * 0.5,
            (self.min.y + self.max.y) * 0.5,
        )

    def surface_area(self) -> float:
        return 2.0 * (self.width + self.height)

    def __repr__(self) -> str:
        return f"AABB({self.min}, {self.max})"


# --------------------------------------------------------------------------- #
# internal helpers
# --------------------------------------------------------------------------- #
def _signed_area(verts: Sequence[Vec2]) -> float:
    """Shoelace area — positive if CCW, negative if CW."""
    area = 0.0
    n = len(verts)
    for i in range(n):
        v0 = verts[i]
        v1 = verts[(i + 1) % n]
        area += v0.cross(v1)
    return area * 0.5


def _polygon_centroid(verts: Sequence[Vec2]) -> Vec2:
    """Polygon centroid via the standard area-weighted formula."""
    cx = cy = 0.0
    a = 0.0
    n = len(verts)
    for i in range(n):
        v0 = verts[i]
        v1 = verts[(i + 1) % n]
        cross = v0.cross(v1)
        a += cross
        cx += (v0.x + v1.x) * cross
        cy += (v0.y + v1.y) * cross
    a *= 0.5
    if abs(a) < 1e-12:
        # Degenerate polygon — fall back to the vertex average.
        return Vec2(sum(v.x for v in verts) / n, sum(v.y for v in verts) / n)
    inv = 1.0 / (6.0 * a)
    return Vec2(cx * inv, cy * inv)


def _ensure_ccw(verts: List[Vec2]) -> List[Vec2]:
    if _signed_area(verts) < 0.0:
        return list(reversed(verts))
    return verts


def _is_convex_ccw(verts: Sequence[Vec2]) -> bool:
    """True if *verts* are CCW and strictly convex (all cross products > 0)."""
    n = len(verts)
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        v0 = verts[i]
        v1 = verts[(i + 1) % n]
        v2 = verts[(i + 2) % n]
        cross = (v1 - v0).cross(v2 - v1)
        if abs(cross) < 1e-12:
            continue  # collinear edges are tolerated
        if sign == 0:
            sign = 1 if cross > 0 else -1
        elif (cross > 0) != (sign > 0):
            return False
    return sign >= 0