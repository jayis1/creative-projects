"""material.py — Surface materials and BSDFs.

Supports:
  * matte (Lambertian diffuse)
  * metal (specular reflection with adjustable fuzziness)
  * dielectric (glass / transparent refraction with Schlick Fresnel)
  * emissive (for area light sources)
  * a "checker" procedural pattern that maps to two child materials based on
    world position.

Every material exposes ``scatter(...)`` which returns either ``None`` (full
absorption) or a tuple ``(attenuation, scattered_ray)``.  The lighting integrator
accumulates attenuation multiplicatively along the path.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from .vec import Vec3
from .ray import Ray

__all__ = ["Material", "Matte", "Metal", "Dielectric", "Emissive", "Checker"]


class HitRecord:
    """Bundle of information produced by a primitive intersection."""

    __slots__ = ("t", "point", "normal", "material", "u", "v", "front_face")

    def __init__(
        self,
        t: float,
        point: Vec3,
        outward_normal: Vec3,
        material: "Material",
        ray: Ray,
        u: float = 0.0,
        v: float = 0.0,
    ) -> None:
        self.t = t
        self.point = point
        self.material = material
        self.u = u
        self.v = v
        # Orient the normal against the ray so it always points toward the
        # viewer — needed for correct refraction and shading.
        front_face = ray.direction.dot(outward_normal) < 0.0
        self.front_face = front_face
        self.normal = outward_normal if front_face else -outward_normal


class Material:
    """Base class.  Subclasses implement :meth:`scatter` and :meth:`emit`."""

    def scatter(
        self, ray_in: Ray, rec: HitRecord
    ) -> Optional[Tuple[Vec3, Ray]]:
        return None

    def emit(self, u: float, v: float, p: Vec3) -> Vec3:
        return Vec3.zero()

    def emitted_albedo(self) -> Vec3:
        """Luminance used for direct light sampling; 0 for non-emitters."""
        return Vec3.zero()


class Matte(Material):
    """Lambertian diffuse surface."""

    def __init__(self, albedo: Vec3) -> None:
        self.albedo = albedo

    def scatter(self, ray_in: Ray, rec: HitRecord):
        target = rec.point + rec.normal + _random_in_unit_sphere()
        scattered_dir = target - rec.point
        # Guard against degenerate scatter direction.
        if scattered_dir.length_squared() < 1e-12:
            scattered_dir = rec.normal
        scattered = Ray(rec.point, scattered_dir, tmax=ray_in.tmax)
        return (self.albedo, scattered)


class Metal(Material):
    """Specular metal with optional fuzzy reflection."""

    def __init__(self, albedo: Vec3, fuzz: float = 0.0) -> None:
        self.albedo = albedo
        self.fuzz = max(0.0, min(1.0, fuzz))

    def scatter(self, ray_in: Ray, rec: HitRecord):
        reflected = ray_in.direction.reflect(rec.normal)
        if self.fuzz > 0.0:
            reflected = reflected + _random_in_unit_sphere() * self.fuzz
        # Rays that scatter below the surface are absorbed.
        if reflected.dot(rec.normal) <= 0.0:
            return None
        scattered = Ray(rec.point, reflected, tmax=ray_in.tmax)
        return (self.albedo, scattered)


class Dielectric(Material):
    """Transparent dielectric (e.g. glass) using Schlick's Fresnel approx."""

    def __init__(self, ior: float = 1.5, albedo: Vec3 | None = None) -> None:
        self.ior = ior
        self.albedo = albedo if albedo is not None else Vec3(1.0, 1.0, 1.0)

    def scatter(self, ray_in: Ray, rec: HitRecord):
        # Determine ratio of refractive indices depending on which side.
        if rec.front_face:
            eta = 1.0 / self.ior
            cos_i = -ray_in.direction.dot(rec.normal)
        else:
            eta = self.ior
            cos_i = -ray_in.direction.dot(-rec.normal)
        cos_i = max(0.0, min(1.0, cos_i))

        sin_t2 = eta * eta * (1.0 - cos_i * cos_i)
        if sin_t2 > 1.0:
            # Total internal reflection.
            reflected = ray_in.direction.reflect(rec.normal)
            scattered = Ray(rec.point, reflected, tmax=ray_in.tmax)
            return (self.albedo, scattered)

        cos_t = math.sqrt(1.0 - sin_t2)
        refracted = ray_in.direction * eta + rec.normal * (eta * cos_i - cos_t)
        # Schlick reflectance for the entering ray.
        r0 = ((1.0 - self.ior) / (1.0 + self.ior)) ** 2
        reflectance = r0 + (1.0 - r0) * (1.0 - cos_i) ** 5
        if _drand48() < reflectance:
            reflected = ray_in.direction.reflect(rec.normal)
            scattered = Ray(rec.point, reflected, tmax=ray_in.tmax)
        else:
            scattered = Ray(rec.point, refracted, tmax=ray_in.tmax)
        return (self.albedo, scattered)


class Emissive(Material):
    """Diffuse area light source."""

    def __init__(self, color: Vec3, intensity: float = 1.0) -> None:
        self.color = color
        self.intensity = float(intensity)

    def emit(self, u: float, v: float, p: Vec3) -> Vec3:
        return self.color * self.intensity

    def emitted_albedo(self) -> Vec3:
        return self.color * self.intensity


class Checker(Material):
    """Procedural checkerboard that delegates to two child materials."""

    def __init__(
        self,
        a: Material,
        b: Material,
        scale: float = 1.0,
    ) -> None:
        self.a = a
        self.b = b
        self.scale = max(1e-6, float(scale))

    def _which(self, p: Vec3) -> Material:
        s = self.scale
        n = int(math.floor(p.x / s)) + int(math.floor(p.y / s)) + int(math.floor(p.z / s))
        return self.a if (n & 1) == 0 else self.b

    def scatter(self, ray_in: Ray, rec: HitRecord):
        return self._which(rec.point).scatter(ray_in, rec)

    def emit(self, u: float, v: float, p: Vec3) -> Vec3:
        return self._which(p).emit(u, v, p)


# --------------------------------------------------------------------------- #
# Random helpers (kept module-local so they can be monkeypatched in tests).
# --------------------------------------------------------------------------- #
import random as _random

_rng = _random.Random()


def seed(s: int) -> None:
    _rng.seed(s)


def _drand48() -> float:
    return _rng.random()


def _random_in_unit_sphere() -> Vec3:
    """Uniformly sample a point inside the unit sphere (rejection method)."""
    while True:
        x = _rng.uniform(-1.0, 1.0)
        y = _rng.uniform(-1.0, 1.0)
        z = _rng.uniform(-1.0, 1.0)
        v = Vec3(x, y, z)
        if v.length_squared() < 1.0:
            return v