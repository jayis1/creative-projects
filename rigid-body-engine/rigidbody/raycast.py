"""Ray casting: find the closest body hit by a ray.

A ray is defined by an origin point and a direction (any length; it is
normalised internally).  The query walks every body's shape and computes
the entry fraction along the ray, returning the closest hit with the
world-space contact point and surface normal.

This is a *linear* (brute-force) ray cast — no acceleration structure is
used.  For the scene sizes this engine targets (hundreds of bodies) it is
fast enough.  A BVH could be layered on top of the broad phase later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from .core.body import RigidBody
from .core.collision import _get_world_vertices, _point_in_polygon_verts
from .core.shapes import Circle, Polygon
from .core.vec2 import Vec2

__all__ = ["RayCastHit", "ray_cast", "ray_cast_body"]


@dataclass
class RayCastHit:
    """Result of a ray-cast query."""

    body_index: int
    point: Vec2
    normal: Vec2
    fraction: float  # 0..1 of max_distance


def ray_cast_body(
    body: RigidBody,
    origin: Vec2,
    direction: Vec2,
    max_fraction: float = 1.0,
) -> Optional[float]:
    """Return the fraction (0..max_fraction) at which *ray* enters *body*.

    Returns ``None`` if no hit.  This is the per-body primitive used by
    :func:`ray_cast`; callers needing the contact point/normal should use
    the higher-level function.
    """
    shape = body.shape
    if isinstance(shape, Circle):
        return _ray_circle(body, shape, origin, direction, max_fraction)
    if isinstance(shape, Polygon):
        return _ray_polygon(body, shape, origin, direction, max_fraction)
    return None


def _ray_circle(
    body: RigidBody,
    circle: Circle,
    origin: Vec2,
    direction: Vec2,
    max_fraction: float,
) -> Optional[float]:
    center = circle.offset.rotate(body.angle) + body.position
    m = origin - center
    b = m.dot(direction)
    c = m.length_sq() - circle.radius * circle.radius
    # Quadratic: t^2 + 2b t + c = 0 (direction is unit).
    if c > 0.0 and b > 0.0:
        return None  # ray origin outside and pointing away
    disc = b * b - c
    if disc < 0.0:
        return None
    t = -b - math.sqrt(disc)
    if t < 0.0:
        t = 0.0  # origin inside — hit at origin
    if t > max_fraction:
        return None
    return t


def _ray_polygon(
    body: RigidBody,
    poly: Polygon,
    origin: Vec2,
    direction: Vec2,
    max_fraction: float,
) -> Optional[float]:
    """Slab-method ray vs convex polygon in world space."""
    verts = _get_world_vertices(poly, body.position, body.angle)
    n = len(verts)
    t_min = 0.0
    t_max = max_fraction
    # For each edge, compute the plane: normal points outward.
    for i in range(n):
        v0 = verts[i]
        v1 = verts[(i + 1) % n]
        edge = v1 - v0
        normal = Vec2(edge.y, -edge.x).normalize()
        denom = normal.dot(direction)
        dist = (origin - v0).dot(normal)
        if abs(denom) < 1e-12:
            # Ray parallel to this edge plane.
            if dist > 0.0:
                return None  # origin outside this slab — no hit
            continue
        t = -dist / denom
        if denom < 0.0:
            # Entering.
            if t > t_min:
                t_min = t
        else:
            # Exiting.
            if t < t_max:
                t_max = t
        if t_min > t_max:
            return None
    if t_min > t_max or t_min < 0.0:
        return None
    return t_min if t_min > 0.0 else 0.0


def ray_cast(
    bodies: List[RigidBody],
    origin: Vec2,
    direction: Vec2,
    max_distance: float = 1e6,
    ignore: Optional[set] = None,
) -> Optional[RayCastHit]:
    """Cast a ray against *bodies* and return the closest hit.

    Parameters
    ----------
    bodies:
        World body list (or any list of :class:`RigidBody`).
    origin:
        Ray origin in world space.
    direction:
        Ray direction (need not be normalised).
    max_distance:
        Maximum ray length in world units.
    ignore:
        Optional set of body indices to skip.

    Returns
    -------
    RayCastHit or None
    """
    d = direction.normalize()
    if d.length_sq() < 1e-16:
        return None
    best_dist = max_distance  # closest hit distance in world units
    best_idx = -1
    for i, body in enumerate(bodies):
        if ignore is not None and i in ignore:
            continue
        if body.aabb is not None:
            # Quick AABB rejection.
            if not _ray_aabb(origin, d, body.aabb, max_distance):
                continue
        # ray_cast_body returns distance in world units (direction is normalized).
        dist = ray_cast_body(body, origin, d, max_distance)
        if dist is not None and dist < best_dist:
            best_dist = dist
            best_idx = i
    if best_idx < 0:
        return None
    body = bodies[best_idx]
    point = origin + d * best_dist
    normal = _surface_normal(body, point)
    return RayCastHit(
        body_index=best_idx,
        point=point,
        normal=normal,
        fraction=best_dist / max_distance if max_distance > 0 else 0.0,
    )


def _ray_aabb(origin: Vec2, direction: Vec2, aabb, max_dist: float) -> bool:
    """Slab test: does ray hit the AABB within *max_dist*?"""
    t_min = 0.0
    t_max = max_dist
    for axis_idx, (o, d, lo, hi) in enumerate(
        [
            (origin.x, direction.x, aabb.min.x, aabb.max.x),
            (origin.y, direction.y, aabb.min.y, aabb.max.y),
        ]
    ):
        if abs(d) < 1e-12:
            if o < lo or o > hi:
                return False
            continue
        t1 = (lo - o) / d
        t2 = (hi - o) / d
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
        if t_min > t_max:
            return False
    return True


def _surface_normal(body: RigidBody, point: Vec2) -> Vec2:
    """Approximate surface normal at *point* on *body*."""
    shape = body.shape
    if isinstance(shape, Circle):
        center = shape.offset.rotate(body.angle) + body.position
        d = point - center
        if d.length_sq() > 1e-16:
            return d.normalize()
        return Vec2(0.0, 1.0)
    if isinstance(shape, Polygon):
        verts = _get_world_vertices(shape, body.position, body.angle)
        n = len(verts)
        best_n = Vec2(0.0, 1.0)
        best_d = math.inf
        for i in range(n):
            v0 = verts[i]
            v1 = verts[(i + 1) % n]
            edge = v1 - v0
            normal = Vec2(edge.y, -edge.x).normalize()
            d = (point - v0).dot(normal)
            if abs(d) < best_d:
                best_d = abs(d)
                best_n = normal
        return best_n
    return Vec2(0.0, 1.0)