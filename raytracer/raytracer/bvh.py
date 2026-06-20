"""bvh.py — Bounding Volume Hierarchy acceleration structure.

A simple binary BVH built with the surface-area heuristic via midpoint split on
the longest axis.  Provides fast ray-primitive intersection for scenes with many
primitives, plus an :class:`AABB` axis-aligned bounding box used throughout.
"""

from __future__ import annotations

import random as _random
from typing import List, Optional, Sequence

from .vec import Vec3
from .ray import Ray
from .material import HitRecord

__all__ = ["AABB", "BVHNode", "HittableList"]


class AABB:
    """Axis-aligned bounding box."""

    __slots__ = ("mn", "mx")

    def __init__(self, mn: Vec3, mx: Vec3) -> None:
        # Guard against inverted boxes.
        self.mn = Vec3(min(mn.x, mx.x), min(mn.y, mx.y), min(mn.z, mx.z))
        self.mx = Vec3(max(mn.x, mx.x), max(mn.y, mx.y), max(mn.z, mx.z))

    def hit(self, ray: Ray, tmin: float, tmax: float) -> bool:
        # Slab method.  Handle zero-direction components safely: if the ray is
        # parallel to a slab (dir component == 0) the ray only intersects that
        # slab when its origin lies within [mn, mx] for that axis.
        for a in ("x", "y", "z"):
            d = getattr(ray.direction, a)
            o = getattr(ray.origin, a)
            lo = getattr(self.mn, a)
            hi = getattr(self.mx, a)
            if d == 0.0:
                # Ray parallel to this slab: must be inside the slab extents.
                if o < lo or o > hi:
                    return False
                continue
            inv_d = 1.0 / d
            t0 = (lo - o) * inv_d
            t1 = (hi - o) * inv_d
            if inv_d < 0.0:
                t0, t1 = t1, t0
            tmin = max(tmin, t0)
            tmax = min(tmax, t1)
            if tmax < tmin:
                return False
        return True

    def center(self) -> Vec3:
        return Vec3(
            (self.mn.x + self.mx.x) * 0.5,
            (self.mn.y + self.mx.y) * 0.5,
            (self.mn.z + self.mx.z) * 0.5,
        )

    def surface_area(self) -> float:
        d = self.mx - self.mn
        return 2.0 * (d.x * d.y + d.y * d.z + d.z * d.x)

    @staticmethod
    def surrounding(a: "AABB", b: "AABB") -> "AABB":
        return AABB(
            Vec3(min(a.mn.x, b.mn.x), min(a.mn.y, b.mn.y), min(a.mn.z, b.mn.z)),
            Vec3(max(a.mx.x, b.mx.x), max(a.mx.y, b.mx.y), max(a.mx.z, b.mx.z)),
        )


class _Hittable:
    """Anything that can be intersected by a ray."""

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        raise NotImplementedError

    def bbox(self) -> AABB:
        raise NotImplementedError

    def centroid(self) -> Vec3:
        return self.bbox().center()


class HittableList(_Hittable):
    """Linear list of hittables — used for small scenes / leaves."""

    def __init__(self, items: Optional[Sequence[_Hittable]] = None) -> None:
        self.items: List[_Hittable] = list(items) if items else []

    def add(self, obj: _Hittable) -> None:
        self.items.append(obj)

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        closest = tmax
        rec: Optional[HitRecord] = None
        for obj in self.items:
            r = obj.hit(ray, tmin, closest)
            if r is not None:
                closest = r.t
                rec = r
        return rec

    def bbox(self) -> AABB:
        if not self.items:
            return AABB(Vec3(0, 0, 0), Vec3(0, 0, 0))
        box = self.items[0].bbox()
        for obj in self.items[1:]:
            box = AABB.surrounding(box, obj.bbox())
        return box


class BVHNode(_Hittable):
    """Binary BVH node built by midpoint split on the widest axis."""

    def __init__(self, items: Sequence[_Hittable], rng: Optional[_random.Random] = None) -> None:
        if not items:
            self.left: Optional[_Hittable] = None
            self.right: Optional[_Hittable] = None
            self.box = AABB(Vec3(0, 0, 0), Vec3(0, 0, 0))
            return
        if len(items) == 1:
            self.left = items[0]
            self.right = None
            self.box = items[0].bbox()
            return
        if len(items) == 2:
            self.left = items[0]
            self.right = items[1]
            self.box = AABB.surrounding(items[0].bbox(), items[1].bbox())
            return

        # Choose split axis as the longest extent of the combined bounding box.
        combined = items[0].bbox()
        for it in items[1:]:
            combined = AABB.surrounding(combined, it.bbox())
        extents = combined.mx - combined.mn
        axis = 0 if extents.x >= extents.y and extents.x >= extents.z else (
            1 if extents.y >= extents.z else 2
        )
        axis_names = ("x", "y", "z")
        key = lambda it: getattr(it.centroid(), axis_names[axis])

        sorted_items = sorted(items, key=key)
        mid = len(sorted_items) // 2
        self.left = BVHNode(sorted_items[:mid], rng)
        self.right = BVHNode(sorted_items[mid:], rng)
        self.box = AABB.surrounding(self.left.bbox(), self.right.bbox())

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        if not self.box.hit(ray, tmin, tmax):
            return None
        rec_left = self.left.hit(ray, tmin, tmax) if self.left else None
        if rec_left is not None:
            rec_right = self.right.hit(ray, tmin, rec_left.t) if self.right else None
            return rec_right or rec_left
        return self.right.hit(ray, tmin, tmax) if self.right else None

    def bbox(self) -> AABB:
        return self.box