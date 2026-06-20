"""primitive.py — Geometric primitives with ray-intersection routines.

Each primitive implements ``hit(ray, tmin, tmax)`` returning either a
:class:`~raytracer.material.HitRecord` or ``None``, and a ``bbox()`` method
returning an :class:`AABB` for BVH construction.
"""

from __future__ import annotations

import math
from typing import Optional

from .vec import Vec3
from .ray import Ray
from .material import HitRecord, Material, Matte
from .bvh import AABB, _Hittable

__all__ = ["Primitive", "Sphere", "Plane", "Triangle", "XYRect"]


class Primitive(_Hittable):
    """Abstract base for ray-hittable geometry."""


class Sphere(Primitive):
    """A sphere defined by center and radius."""

    def __init__(self, center: Vec3, radius: float, material: Material | None = None) -> None:
        self.center = center
        self.radius = float(radius)
        self.material = material if material is not None else Matte(Vec3(0.8, 0.8, 0.8))

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        oc = ray.origin - self.center
        a = ray.direction.length_squared()  # ~1 for unit dir
        half_b = oc.dot(ray.direction)
        c = oc.length_squared() - self.radius * self.radius
        disc = half_b * half_b - a * c
        if disc < 0.0:
            return None
        sq = math.sqrt(disc)
        # Try nearest root first.
        root = (-half_b - sq) / a
        if root < tmin or root > tmax:
            root = (-half_b + sq) / a
            if root < tmin or root > tmax:
                return None
        p = ray.at(root)
        outward = (p - self.center) / self.radius
        # Compute spherical UV for texture mapping.
        u = 0.5 + math.atan2(outward.z, outward.x) / (2.0 * math.pi)
        v = 0.5 - math.asin(max(-1.0, min(1.0, outward.y))) / math.pi
        return HitRecord(root, p, outward, self.material, ray, u, v)

    def bbox(self) -> AABB:
        r = self.radius
        mn = Vec3(self.center.x - r, self.center.y - r, self.center.z - r)
        mx = Vec3(self.center.x + r, self.center.y + r, self.center.z + r)
        return AABB(mn, mx)


class Plane(Primitive):
    """An infinite plane defined by a point and unit normal."""

    def __init__(
        self, point: Vec3, normal: Vec3, material: Material | None = None
    ) -> None:
        self.point = point
        n = normal.length()
        if n == 0.0:
            raise ValueError("Plane normal cannot be zero")
        self.normal = normal / n
        self.material = material if material is not None else Matte(Vec3(0.6, 0.6, 0.6))

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        denom = ray.direction.dot(self.normal)
        if abs(denom) < 1e-8:
            return None
        t = (self.point - ray.origin).dot(self.normal) / denom
        if t < tmin or t > tmax:
            return None
        p = ray.at(t)
        # Plane UV via projection onto two basis vectors.
        u, v = _plane_uv(p, self.normal)
        return HitRecord(t, p, self.normal, self.material, ray, u, v)

    def bbox(self) -> AABB:
        # Infinite plane — return a huge AABB.
        big = 1e9
        return AABB(Vec3(-big, -big, -big), Vec3(big, big, big))


class Triangle(Primitive):
    """A triangle given three vertex positions (winding via right-hand rule)."""

    def __init__(
        self,
        a: Vec3,
        b: Vec3,
        c: Vec3,
        material: Material | None = None,
    ) -> None:
        self.a = a
        self.b = b
        self.c = c
        self.material = material if material is not None else Matte(Vec3(0.8, 0.8, 0.8))
        # Precompute face normal (Möller–Trumbore uses edge vectors).
        self._edge1 = b - a
        self._edge2 = c - a
        self._normal = self._edge1.cross(self._edge2)
        n_len = self._normal.length()
        self._area2 = n_len  # |cross| = 2 * area
        self._unit_normal = (
            self._normal / n_len if n_len > 0 else Vec3(0, 1, 0)
        )

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        # Möller–Trumbore ray-triangle intersection.
        h = ray.direction.cross(self._edge2)
        a = self._edge1.dot(h)
        if abs(a) < 1e-12:
            return None  # parallel
        f = 1.0 / a
        s = ray.origin - self.a
        u = f * s.dot(h)
        if u < 0.0 or u > 1.0:
            return None
        q = s.cross(self._edge1)
        v = f * ray.direction.dot(q)
        if v < 0.0 or u + v > 1.0:
            return None
        t = f * self._edge2.dot(q)
        if t < tmin or t > tmax:
            return None
        p = ray.at(t)
        return HitRecord(t, p, self._unit_normal, self.material, ray, u, v)

    def bbox(self) -> AABB:
        eps = 1e-5
        mn = Vec3(
            min(self.a.x, self.b.x, self.c.x) - eps,
            min(self.a.y, self.b.y, self.c.y) - eps,
            min(self.a.z, self.b.z, self.c.z) - eps,
        )
        mx = Vec3(
            max(self.a.x, self.b.x, self.c.x) + eps,
            max(self.a.y, self.b.y, self.c.y) + eps,
            max(self.a.z, self.b.z, self.c.z) + eps,
        )
        return AABB(mn, mx)


class XYRect(Primitive):
    """An axis-aligned rectangle in the z=z0 plane (used as an area light)."""

    def __init__(
        self,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z: float,
        material: Material | None = None,
    ) -> None:
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        self.x0, self.x1 = x0, x1
        self.y0, self.y1 = y0, y1
        self.z = z
        self.material = material if material is not None else Matte(Vec3(0.9, 0.9, 0.9))

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        t = (self.z - ray.origin.z) / ray.direction.z
        if t < tmin or t > tmax:
            return None
        p = ray.at(t)
        if p.x < self.x0 or p.x > self.x1 or p.y < self.y0 or p.y > self.y1:
            return None
        u = (p.x - self.x0) / (self.x1 - self.x0) if self.x1 != self.x0 else 0.0
        v = (p.y - self.y0) / (self.y1 - self.y0) if self.y1 != self.y0 else 0.0
        normal = Vec3(0.0, 0.0, 1.0)
        return HitRecord(t, p, normal, self.material, ray, u, v)

    def bbox(self) -> AABB:
        eps = 1e-5
        return AABB(
            Vec3(self.x0, self.y0, self.z - eps),
            Vec3(self.x1, self.y1, self.z + eps),
        )


def _plane_uv(p: Vec3, normal: Vec3) -> tuple:
    """Cheap planar UV using two orthonormal basis vectors around *normal*."""
    if abs(normal.x) < 0.9:
        u_axis = Vec3(1.0, 0.0, 0.0).cross(normal)
    else:
        u_axis = Vec3(0.0, 1.0, 0.0).cross(normal)
    n2 = u_axis.length()
    if n2 == 0.0:
        return (0.0, 0.0)
    u_axis = u_axis / n2
    v_axis = normal.cross(u_axis)
    u = (p - Vec3(0, 0, 0)).dot(u_axis)
    v = (p - Vec3(0, 0, 0)).dot(v_axis)
    return (u, v)