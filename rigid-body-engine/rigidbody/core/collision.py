"""Collision detection producing contact manifolds.

The detector is responsible for answering ``do these two shapes overlap, and
if so where?``.  It returns :class:`Manifold` objects describing one or two
contact points with normals and penetration depths — exactly what the
sequential-impulse solver needs.

Three shape-pair combinations are supported:

* polygon × polygon  — SAT (Separating Axis Theorem) with reference/incident
  edge clipping for a proper 2-point contact manifold.
* circle × circle    — distance-based, single contact.
* circle × polygon   — closest-point-on-polygon with vertex/edge cases.

The implementation favours clarity over micro-optimisation.  Every public
function is pure (no side effects) so it is easy to unit-test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from .shapes import Circle, Polygon
from .vec2 import Vec2

__all__ = ["Manifold", "ContactPoint", "collide", "point_in_polygon"]


@dataclass
class ContactPoint:
    """A single contact: world-space position, normal (A→B), penetration."""

    point: Vec2
    normal: Vec2  # unit normal pointing from A to B
    penetration: float


@dataclass
class Manifold:
    """A set of contact points between two bodies.

    ``body_a`` and ``body_b`` are indices into the world's body list (or
    ``None`` for one-sided queries).  The normal always points from A to B.
    """

    body_a: Optional[int] = None
    body_b: Optional[int] = None
    points: List[ContactPoint] = field(default_factory=list)
    normal: Vec2 = field(default_factory=lambda: Vec2(0.0, 1.0))
    penetration: float = 0.0

    @property
    def contact_count(self) -> int:
        return len(self.points)


def collide(
    shape_a, shape_b, pos_a: Vec2, angle_a: float, pos_b: Vec2, angle_b: float
) -> Optional[Manifold]:
    """Dispatch on shape types and return a :class:`Manifold` or ``None``.

    The returned normal (if any) always points from **A** to **B**.
    """
    ta = shape_a.shape_type
    tb = shape_b.shape_type
    if ta == "circle" and tb == "circle":
        return _circle_circle(shape_a, pos_a, shape_b, pos_b)
    if ta == "polygon" and tb == "polygon":
        return _polygon_polygon(shape_a, pos_a, angle_a, shape_b, pos_b, angle_b)
    if ta == "circle" and tb == "polygon":
        return _circle_polygon(shape_a, pos_a, angle_a, shape_b, pos_b, angle_b)
    if ta == "polygon" and tb == "circle":
        m = _circle_polygon(shape_b, pos_b, angle_b, shape_a, pos_a, angle_a)
        if m is not None:
            # _circle_polygon returns normal circle→polygon; we need polygon→circle.
            m.normal = -m.normal
            for p in m.points:
                p.normal = -p.normal
        return m
    return None


# --------------------------------------------------------------------------- #
# circle × circle
# --------------------------------------------------------------------------- #
def _circle_circle(a: Circle, pos_a: Vec2, b: Circle, pos_b: Vec2) -> Optional[Manifold]:
    # Account for local offsets.
    ca = a.offset.rotate(0.0) + pos_a  # circles don't rotate meaningfully but keep API
    ca = pos_a + a.offset
    cb = pos_b + b.offset
    d = cb - ca
    r_sum = a.radius + b.radius
    dist_sq = d.length_sq()
    if dist_sq >= r_sum * r_sum:
        return None
    dist = math.sqrt(dist_sq)
    if dist > 1e-9:
        normal = d / dist
    else:
        normal = Vec2(0.0, 1.0)
        dist = 0.0
    penetration = r_sum - dist
    point = ca + normal * a.radius
    cp = ContactPoint(point=point, normal=normal, penetration=penetration)
    return Manifold(points=[cp], normal=normal, penetration=penetration)


# --------------------------------------------------------------------------- #
# polygon × polygon  (SAT + clipping)
# --------------------------------------------------------------------------- #
def _get_world_vertices(poly: Polygon, pos: Vec2, angle: float) -> List[Vec2]:
    c, s = math.cos(angle), math.sin(angle)
    out = []
    for v in poly.vertices:
        out.append(Vec2(v.x * c - v.y * s + pos.x, v.x * s + v.y * c + pos.y))
    return out


def _get_world_normals(poly: Polygon, angle: float) -> List[Vec2]:
    c, s = math.cos(angle), math.sin(angle)
    out = []
    for n in poly.normals:
        out.append(Vec2(n.x * c - n.y * s, n.x * s + n.y * c))
    return out


def _project(verts: List[Vec2], axis: Vec2) -> tuple[float, float]:
    """Project *verts* onto *axis*, return (min, max)."""
    mn = mx = verts[0].dot(axis)
    for v in verts[1:]:
        proj = v.dot(axis)
        if proj < mn:
            mn = proj
        if proj > mx:
            mx = proj
    return mn, mx


def _polygon_polygon(
    a: Polygon, pos_a: Vec2, angle_a: float, b: Polygon, pos_b: Vec2, angle_b: float
) -> Optional[Manifold]:
    verts_a = _get_world_vertices(a, pos_a, angle_a)
    verts_b = _get_world_vertices(b, pos_b, angle_b)
    norms_a = _get_world_normals(a, angle_a)
    norms_b = _get_world_normals(b, angle_b)

    # SAT: test all face normals for separation; among the front-facing
    # normals pick the one with minimum overlap as the contact edge.
    min_overlap = math.inf
    ref_from_a = True
    ref_edge = 0
    best_normal = Vec2(0.0, 1.0)
    d_center = pos_b - pos_a  # direction from A to B (for facing test)

    def _check(norms, verts_self, verts_other, from_a: bool) -> None:
        nonlocal min_overlap, ref_from_a, ref_edge, best_normal
        for i, n in enumerate(norms):
            # Orient the candidate normal from A→B.
            cand = n if from_a else -n
            mn_s, mx_s = _project(verts_self, cand)
            mn_o, mx_o = _project(verts_other, cand)
            if mx_o < mn_s or mx_s < mn_o:
                raise _Separation  # genuine separating axis
            # Only front-facing edges can be the *contact* edge.
            if cand.dot(d_center) <= 0.0:
                continue
            overlap = min(mx_s, mx_o) - max(mn_s, mn_o)
            if overlap < min_overlap:
                min_overlap = overlap
                ref_from_a = from_a
                ref_edge = i
                best_normal = cand

    try:
        _check(norms_a, verts_a, verts_b, True)
        _check(norms_b, verts_b, verts_a, False)
    except _Separation:
        return None

    # Set up reference (the edge whose normal is the min-overlap axis) and
    # incident (the other polygon's best edge to clip).
    if ref_from_a:
        ref_verts = verts_a
        inc_verts = verts_b
    else:
        ref_verts = verts_b
        inc_verts = verts_a

    ref_normal = best_normal  # oriented A→B

    v1 = ref_verts[ref_edge]
    v2 = ref_verts[(ref_edge + 1) % len(ref_verts)]
    ref_dir = (v2 - v1).normalize()

    # Find incident edge: the edge of the *other* polygon whose outward normal
    # is most anti-parallel to ref_normal.
    best = 0
    best_dot = math.inf
    for i in range(len(inc_verts)):
        v0 = inc_verts[i]
        v1i = inc_verts[(i + 1) % len(inc_verts)]
        edge = v1i - v0
        n = Vec2(edge.y, -edge.x).normalize()
        d = n.dot(ref_normal)
        if d < best_dot:
            best_dot = d
            best = i

    inc_v1 = inc_verts[best]
    inc_v2 = inc_verts[(best + 1) % len(inc_verts)]

    # Clip incident edge against the two side planes of the reference edge.
    clipped = _clip(inc_v1, inc_v2, ref_dir, v1.dot(ref_dir))
    if len(clipped) < 2:
        return None
    neg_dir = Vec2(-ref_dir.x, -ref_dir.y)
    clipped = _clip(clipped[0], clipped[1], neg_dir, -v2.dot(ref_dir))
    if len(clipped) < 2:
        return None

    # Keep points that are behind the reference plane (inside the other body).
    ref_offset = ref_normal.dot(v1)
    contacts: List[ContactPoint] = []
    for cp in clipped:
        dist = ref_normal.dot(cp) - ref_offset
        if dist <= 1e-6:
            # penetration along the normal — capped at min_overlap for safety.
            pen = max(0.0, min(min_overlap, min_overlap - dist))
            contacts.append(ContactPoint(point=cp, normal=ref_normal, penetration=pen))
    if not contacts:
        return None

    return Manifold(points=contacts, normal=ref_normal, penetration=min_overlap)


class _Separation(Exception):
    """Internal sentinel to short-circuit the SAT loop."""


def _clip(v1: Vec2, v2: Vec2, normal: Vec2, offset: float) -> List[Vec2]:
    """Sutherland-Hodgman clip: keep points where ``normal·p >= offset``."""
    out = []
    d1 = normal.dot(v1) - offset
    d2 = normal.dot(v2) - offset
    if d1 >= 0.0:
        out.append(v1)
    if d2 >= 0.0:
        out.append(v2)
    if d1 * d2 < 0.0:
        t = d1 / (d1 - d2)
        out.append(v1 + (v2 - v1) * t)
    return out


# --------------------------------------------------------------------------- #
# circle × polygon
# --------------------------------------------------------------------------- #
def _circle_polygon(
    circle: Circle, circle_pos: Vec2, circle_angle: float,
    poly: Polygon, poly_pos: Vec2, poly_angle: float,
) -> Optional[Manifold]:
    """Circle is A, polygon is B.  Normal points circle→polygon."""
    world_center = circle.offset.rotate(circle_angle) + circle_pos
    verts = _get_world_vertices(poly, poly_pos, poly_angle)

    # Find the closest point on the polygon to the circle centre.
    closest = verts[0]
    closest_dist_sq = (world_center - closest).length_sq()
    n = len(verts)
    for i in range(n):
        v0 = verts[i]
        v1 = verts[(i + 1) % n]
        edge = v1 - v0
        edge_len_sq = edge.length_sq()
        if edge_len_sq < 1e-16:
            continue
        t = max(0.0, min(1.0, (world_center - v0).dot(edge) / edge_len_sq))
        candidate = v0 + edge * t
        dsq = (world_center - candidate).length_sq()
        if dsq < closest_dist_sq:
            closest_dist_sq = dsq
            closest = candidate

    dist = math.sqrt(closest_dist_sq)
    inside = _point_in_polygon_verts(world_center, verts)

    if inside:
        # Circle centre is inside the polygon — deep penetration.
        # Push the circle out along the direction from closest→centre.
        if dist > 1e-9:
            normal = (world_center - closest).normalize()
        else:
            # Centre coincides with a vertex; use the edge normal instead.
            # Find the edge with the smallest positive distance.
            best_n = Vec2(0.0, 1.0)
            best_d = math.inf
            for i in range(n):
                v0 = verts[i]
                v1 = verts[(i + 1) % n]
                e = v1 - v0
                fn = Vec2(e.y, -e.x).normalize()
                d = (world_center - v0).dot(fn)
                if d < best_d:
                    best_d = d
                    best_n = fn
            normal = best_n
            dist = 0.0
        # Normal points circle→polygon (A→B): from centre toward closest = inward.
        # We want to push the circle out, so the contact normal (A→B) is the
        # inward direction = (closest - centre).
        normal = (closest - world_center)
        if normal.length_sq() > 1e-16:
            normal = normal.normalize()
        else:
            normal = Vec2(0.0, 1.0)
        penetration = circle.radius + dist
        contact = closest
    else:
        if dist >= circle.radius:
            return None
        # External contact: normal points from circle centre toward closest
        # point on polygon (i.e., A→B direction = inward).
        if dist > 1e-9:
            normal = (closest - world_center) / dist
        else:
            normal = Vec2(0.0, 1.0)
        penetration = circle.radius - dist
        contact = closest

    cp = ContactPoint(point=contact, normal=normal, penetration=penetration)
    return Manifold(points=[cp], normal=normal, penetration=penetration)


def _point_in_polygon_verts(p: Vec2, verts: List[Vec2]) -> bool:
    """Point-in-convex-polygon test using cross products (CCW polygon)."""
    n = len(verts)
    sign = 0
    for i in range(n):
        v0 = verts[i]
        v1 = verts[(i + 1) % n]
        cross = (v1 - v0).cross(p - v0)
        c = 1 if cross > 0 else (-1 if cross < 0 else 0)
        if c == 0:
            continue
        if sign == 0:
            sign = c
        elif c != sign:
            return False
    return True


def point_in_polygon(p: Vec2, poly: Polygon, pos: Vec2, angle: float) -> bool:
    """Public helper: is world-space point *p* inside polygon *poly*?"""
    verts = _get_world_vertices(poly, pos, angle)
    return _point_in_polygon_verts(p, verts)