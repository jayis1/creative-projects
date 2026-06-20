"""primitive.py — Geometric primitives with ray-intersection routines.

Each primitive implements ``hit(ray, tmin, tmax)`` returning either a
:class:`~raytracer.material.HitRecord` or ``None``, and a ``bbox()`` method
returning an :class:`AABB` for BVH construction.

Supported primitives
--------------------
* :class:`Sphere`   — analytic ray-sphere via reduced quadratic
* :class:`Plane`    — infinite ray-plane
* :class:`Triangle` — Möller–Trumbore ray-triangle
* :class:`XYRect` / :class:`XZRect` / :class:`YZRect` — axis-aligned rectangles
* :class:`Box`      — axis-aligned box (6 axis-aligned rectangles)
* :class:`Disk`     — flat circular disk
* :class:`Cylinder` — finite cylinder (side + optional caps)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, List

from .vec import Vec3
from .ray import Ray
from .material import HitRecord, Material, Matte
from .bvh import AABB, _Hittable, HittableList, BVHNode

__all__ = [
    "Primitive",
    "Sphere",
    "Plane",
    "Triangle",
    "XYRect",
    "XZRect",
    "YZRect",
    "Box",
    "Disk",
    "Cylinder",
]


class Primitive(_Hittable):
    """Abstract base for ray-hittable geometry."""


# --------------------------------------------------------------------------- #
# Sphere
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Plane
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Triangle
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Axis-aligned rectangles
# --------------------------------------------------------------------------- #
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
        # Guard against rays parallel to the rectangle plane (dir.z == 0),
        # which would otherwise divide by zero.
        if ray.direction.z == 0.0:
            return None
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


class XZRect(Primitive):
    """An axis-aligned rectangle in the y=y0 plane."""

    def __init__(
        self,
        x0: float,
        x1: float,
        z0: float,
        z1: float,
        y: float,
        material: Material | None = None,
    ) -> None:
        if x0 > x1:
            x0, x1 = x1, x0
        if z0 > z1:
            z0, z1 = z1, z0
        self.x0, self.x1 = x0, x1
        self.z0, self.z1 = z0, z1
        self.y = y
        self.material = material if material is not None else Matte(Vec3(0.9, 0.9, 0.9))

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        if ray.direction.y == 0.0:
            return None
        t = (self.y - ray.origin.y) / ray.direction.y
        if t < tmin or t > tmax:
            return None
        p = ray.at(t)
        if p.x < self.x0 or p.x > self.x1 or p.z < self.z0 or p.z > self.z1:
            return None
        u = (p.x - self.x0) / (self.x1 - self.x0) if self.x1 != self.x0 else 0.0
        v = (p.z - self.z0) / (self.z1 - self.z0) if self.z1 != self.z0 else 0.0
        normal = Vec3(0.0, 1.0, 0.0)
        return HitRecord(t, p, normal, self.material, ray, u, v)

    def bbox(self) -> AABB:
        eps = 1e-5
        return AABB(
            Vec3(self.x0, self.y - eps, self.z0),
            Vec3(self.x1, self.y + eps, self.z1),
        )


class YZRect(Primitive):
    """An axis-aligned rectangle in the x=x0 plane."""

    def __init__(
        self,
        y0: float,
        y1: float,
        z0: float,
        z1: float,
        x: float,
        material: Material | None = None,
    ) -> None:
        if y0 > y1:
            y0, y1 = y1, y0
        if z0 > z1:
            z0, z1 = z1, z0
        self.y0, self.y1 = y0, y1
        self.z0, self.z1 = z0, z1
        self.x = x
        self.material = material if material is not None else Matte(Vec3(0.9, 0.9, 0.9))

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        if ray.direction.x == 0.0:
            return None
        t = (self.x - ray.origin.x) / ray.direction.x
        if t < tmin or t > tmax:
            return None
        p = ray.at(t)
        if p.y < self.y0 or p.y > self.y1 or p.z < self.z0 or p.z > self.z1:
            return None
        u = (p.y - self.y0) / (self.y1 - self.y0) if self.y1 != self.y0 else 0.0
        v = (p.z - self.z0) / (self.z1 - self.z0) if self.z1 != self.z0 else 0.0
        normal = Vec3(1.0, 0.0, 0.0)
        return HitRecord(t, p, normal, self.material, ray, u, v)

    def bbox(self) -> AABB:
        eps = 1e-5
        return AABB(
            Vec3(self.x - eps, self.y0, self.z0),
            Vec3(self.x + eps, self.y1, self.z1),
        )


# --------------------------------------------------------------------------- #
# Box (axis-aligned, built from six rectangles)
# --------------------------------------------------------------------------- #
class Box(Primitive):
    """An axis-aligned box defined by two opposite corners.

    Implemented as a :class:`HittableList` of six axis-aligned rectangles so
    the BVH can accelerate it and each face can carry its own (shared) material.
    """

    def __init__(
        self,
        p_min: Vec3,
        p_max: Vec3,
        material: Material | None = None,
    ) -> None:
        # Normalize corners.
        lo = Vec3(min(p_min.x, p_max.x), min(p_min.y, p_max.y), min(p_min.z, p_max.z))
        hi = Vec3(max(p_min.x, p_max.x), max(p_min.y, p_max.y), max(p_min.z, p_max.z))
        self.p_min = lo
        self.p_max = hi
        self.material = material if material is not None else Matte(Vec3(0.8, 0.8, 0.8))
        m = self.material
        sides: List[_Hittable] = [
            XYRect(lo.x, hi.x, lo.y, hi.y, hi.z, m),  # front  (+z)
            XYRect(lo.x, hi.x, lo.y, hi.y, lo.z, m),  # back   (−z)
            XZRect(lo.x, hi.x, lo.z, hi.z, hi.y, m),  # top    (+y)
            XZRect(lo.x, hi.x, lo.z, hi.z, lo.y, m),  # bottom (−y)
            YZRect(lo.y, hi.y, lo.z, hi.z, lo.x, m),  # left   (−x)
            YZRect(lo.y, hi.y, lo.z, hi.z, hi.x, m),  # right  (+x)
        ]
        self._sides = HittableList(sides)

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        return self._sides.hit(ray, tmin, tmax)

    def bbox(self) -> AABB:
        return AABB(self.p_min, self.p_max)


# --------------------------------------------------------------------------- #
# Disk
# --------------------------------------------------------------------------- #
class Disk(Primitive):
    """A flat circular disk defined by a center, normal, and radius."""

    def __init__(
        self,
        center: Vec3,
        normal: Vec3,
        radius: float,
        material: Material | None = None,
    ) -> None:
        self.center = center
        n = normal.length()
        if n == 0.0:
            raise ValueError("Disk normal cannot be zero")
        self.normal = normal / n
        self.radius = float(radius)
        self.material = material if material is not None else Matte(Vec3(0.8, 0.8, 0.8))

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        denom = ray.direction.dot(self.normal)
        if abs(denom) < 1e-12:
            return None
        t = (self.center - ray.origin).dot(self.normal) / denom
        if t < tmin or t > tmax:
            return None
        p = ray.at(t)
        d = p - self.center
        if d.length_squared() > self.radius * self.radius:
            return None
        # UV via polar coordinates.
        u = 0.5 + math.atan2(d.z, d.x) / (2.0 * math.pi)
        v = d.length() / self.radius
        return HitRecord(t, p, self.normal, self.material, ray, u, v)

    def bbox(self) -> AABB:
        # Conservative AABB: enclose the disk's bounding sphere.
        r = self.radius
        return AABB(self.center - Vec3(r, r, r), self.center + Vec3(r, r, r))


# --------------------------------------------------------------------------- #
# Cylinder (finite, axis-aligned along Y)
# --------------------------------------------------------------------------- #
class Cylinder(Primitive):
    """A finite cylinder with its axis along the Y direction.

    Parameters
    ----------
    center : base center of the cylinder (at ``y = y0``).
    radius : cylinder radius.
    y0, y1 : extent of the cylinder along the Y axis (``y0 < y1``).
    material : surface material (applied to side and caps).
    capped : if ``True`` (default) add disk caps at ``y0`` and ``y1``.
    """

    def __init__(
        self,
        center: Vec3,
        radius: float,
        y0: float,
        y1: float,
        material: Material | None = None,
        capped: bool = True,
    ) -> None:
        if y0 > y1:
            y0, y1 = y1, y0
        self.center = center
        self.radius = float(radius)
        self.y0 = float(y0)
        self.y1 = float(y1)
        self.capped = capped
        self.material = material if material is not None else Matte(Vec3(0.8, 0.8, 0.8))

    def _hit_side(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        """Intersect the infinite cylinder side, clipped to [y0, y1]."""
        # Project ray onto XZ plane relative to center.
        ox = ray.origin.x - self.center.x
        oz = ray.origin.z - self.center.z
        dx = ray.direction.x
        dz = ray.direction.z
        a = dx * dx + dz * dz
        if a < 1e-12:
            # Ray is parallel to the cylinder axis — never hits the side.
            return None
        b = ox * dx + oz * dz
        c = ox * ox + oz * oz - self.radius * self.radius
        disc = b * b - a * c
        if disc < 0.0:
            return None
        sq = math.sqrt(disc)
        root = (-b - sq) / a
        if root < tmin or root > tmax:
            root = (-b + sq) / a
            if root < tmin or root > tmax:
                return None
        p = ray.at(root)
        if p.y < self.y0 or p.y > self.y1:
            return None
        outward = Vec3(p.x - self.center.x, 0.0, p.z - self.center.z)
        n_len = outward.length()
        if n_len > 0:
            outward = outward / n_len
        u = 0.5 + math.atan2(outward.z, outward.x) / (2.0 * math.pi)
        v = (p.y - self.y0) / (self.y1 - self.y0) if self.y1 != self.y0 else 0.0
        return HitRecord(root, p, outward, self.material, ray, u, v)

    def _hit_cap(self, ray: Ray, tmin: float, tmax: float, y: float, normal: Vec3) -> Optional[HitRecord]:
        """Intersect a single disk cap at height *y* with *normal*."""
        if ray.direction.y == 0.0:
            return None
        t = (y - ray.origin.y) / ray.direction.y
        if t < tmin or t > tmax:
            return None
        p = ray.at(t)
        d = Vec3(p.x - self.center.x, 0.0, p.z - self.center.z)
        if d.length_squared() > self.radius * self.radius:
            return None
        u = 0.5 + math.atan2(d.z, d.x) / (2.0 * math.pi)
        v = d.length() / self.radius
        return HitRecord(t, p, normal, self.material, ray, u, v)

    def hit(self, ray: Ray, tmin: float, tmax: float) -> Optional[HitRecord]:
        closest_t = tmax
        best: Optional[HitRecord] = None
        rec = self._hit_side(ray, tmin, closest_t)
        if rec is not None:
            best = rec
            closest_t = rec.t
        if self.capped:
            for y, n in ((self.y0, Vec3(0, -1, 0)), (self.y1, Vec3(0, 1, 0))):
                rec = self._hit_cap(ray, tmin, closest_t, y, n)
                if rec is not None:
                    best = rec
                    closest_t = rec.t
        return best

    def bbox(self) -> AABB:
        r = self.radius
        return AABB(
            Vec3(self.center.x - r, self.y0, self.center.z - r),
            Vec3(self.center.x + r, self.y1, self.center.z + r),
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
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