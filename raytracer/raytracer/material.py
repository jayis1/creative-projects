"""material.py — Surface materials and BSDFs.

Supports:
  * matte (Lambertian diffuse) — optionally textured
  * metal (specular reflection with adjustable fuzziness)
  * dielectric (glass / transparent refraction with Schlick Fresnel)
  * emissive (for area light sources)
  * a "checker" procedural pattern that maps to two child materials based on
    world position.
  * isotropic (volume scattering / participating media)
  * textured variants via :class:`~raytracer.texture.Texture`

Every material exposes ``scatter(...)`` which returns either ``None`` (full
absorption) or a tuple ``(attenuation, scattered_ray)``.  The lighting
integrator accumulates attenuation multiplicatively along the path.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, Union

from .vec import Vec3
from .ray import Ray
from .texture import Texture, SolidColor

__all__ = [
    "Material",
    "Matte",
    "Metal",
    "Dielectric",
    "Emissive",
    "Checker",
    "Isotropic",
    "HitRecord",
]


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


def _coerce_texture(albedo: Union[Vec3, Texture, None]) -> Texture:
    """Accept either a Vec3 color or a Texture; wrap colors in SolidColor."""
    if albedo is None:
        return SolidColor(Vec3(0.8, 0.8, 0.8))
    if isinstance(albedo, Texture):
        return albedo
    if isinstance(albedo, Vec3):
        return SolidColor(albedo)
    raise TypeError(f"albedo must be Vec3 or Texture, not {type(albedo).__name__}")


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

    def scattering_pdf(self, ray_in: Ray, rec: HitRecord, scattered: Ray) -> float:
        """Probability density for the given scattered ray.

        Used by importance-sampled integrators.  The default (uniform
        hemisphere) is a conservative estimate.
        """
        return 0.0


# --------------------------------------------------------------------------- #
# Matte (Lambertian diffuse) — now textured
# --------------------------------------------------------------------------- #
class Matte(Material):
    """Lambertian diffuse surface with optional texture."""

    def __init__(self, albedo: Union[Vec3, Texture]) -> None:
        self.texture = _coerce_texture(albedo)

    @property
    def albedo(self) -> Vec3:
        """Backward-compatible accessor: returns the texture's base color if
        it is a :class:`SolidColor`, else white."""
        if isinstance(self.texture, SolidColor):
            return self.texture.color
        return Vec3(0.8, 0.8, 0.8)

    def scatter(self, ray_in: Ray, rec: HitRecord):
        target = rec.point + rec.normal + _random_in_unit_sphere()
        scattered_dir = target - rec.point
        # Guard against degenerate scatter direction.
        if scattered_dir.length_squared() < 1e-12:
            scattered_dir = rec.normal
        scattered = Ray(rec.point, scattered_dir, tmax=ray_in.tmax)
        attenuation = self.texture.value(rec.u, rec.v, rec.point)
        return (attenuation, scattered)

    def scattering_pdf(self, ray_in: Ray, rec: HitRecord, scattered: Ray) -> float:
        # Cosine-weighted PDF: cos(theta) / pi.
        cos = scattered.direction.dot(rec.normal)
        return max(0.0, cos) / math.pi


# --------------------------------------------------------------------------- #
# Metal (specular reflection with fuzzy roughness) — now textured
# --------------------------------------------------------------------------- #
class Metal(Material):
    """Specular metal with optional fuzzy reflection and texture."""

    def __init__(self, albedo: Union[Vec3, Texture], fuzz: float = 0.0) -> None:
        self.texture = _coerce_texture(albedo)
        self.fuzz = max(0.0, min(1.0, fuzz))

    @property
    def albedo(self) -> Vec3:
        if isinstance(self.texture, SolidColor):
            return self.texture.color
        return Vec3(0.8, 0.8, 0.8)

    def scatter(self, ray_in: Ray, rec: HitRecord):
        reflected = ray_in.direction.reflect(rec.normal)
        if self.fuzz > 0.0:
            reflected = reflected + _random_in_unit_sphere() * self.fuzz
        # Rays that scatter below the surface are absorbed.
        if reflected.dot(rec.normal) <= 0.0:
            return None
        scattered = Ray(rec.point, reflected, tmax=ray_in.tmax)
        attenuation = self.texture.value(rec.u, rec.v, rec.point)
        return (attenuation, scattered)


# --------------------------------------------------------------------------- #
# Dielectric (glass / transparent refraction with Schlick Fresnel)
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Emissive (area light source) — now with optional texture
# --------------------------------------------------------------------------- #
class Emissive(Material):
    """Diffuse area light source with optional texture map."""

    def __init__(
        self,
        color: Union[Vec3, Texture],
        intensity: float = 1.0,
    ) -> None:
        self.texture = _coerce_texture(color)
        self.intensity = float(intensity)

    @property
    def color(self) -> Vec3:
        if isinstance(self.texture, SolidColor):
            return self.texture.color
        return Vec3(1.0, 1.0, 1.0)

    def emit(self, u: float, v: float, p: Vec3) -> Vec3:
        return self.texture.value(u, v, p) * self.intensity

    def emitted_albedo(self) -> Vec3:
        return self.color * self.intensity


# --------------------------------------------------------------------------- #
# Checker (procedural checkerboard delegating to two child materials)
# --------------------------------------------------------------------------- #
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
# Isotropic (volume scattering / participating media)
# --------------------------------------------------------------------------- #
class Isotropic(Material):
    """Isotropically scattering participating medium.

    Used by volumetric primitives (e.g. constant-density fog / smoke).  Each
    interaction randomly scatters the ray in any direction, attenuated by the
    texture color.
    """

    def __init__(self, albedo: Union[Vec3, Texture]) -> None:
        self.texture = _coerce_texture(albedo)

    @property
    def albedo(self) -> Vec3:
        if isinstance(self.texture, SolidColor):
            return self.texture.color
        return Vec3(0.5, 0.5, 0.5)

    def scatter(self, ray_in: Ray, rec: HitRecord):
        direction = _random_in_unit_sphere()
        scattered = Ray(rec.point, direction, tmax=ray_in.tmax)
        attenuation = self.texture.value(rec.u, rec.v, rec.point)
        return (attenuation, scattered)


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


def _random_unit_vector() -> Vec3:
    """Sample a uniformly-distributed unit vector on the sphere."""
    while True:
        p = _random_in_unit_sphere()
        if p.length_squared() > 1e-12:
            return p.normalized()


def _random_in_hemisphere(normal: Vec3) -> Vec3:
    """Cosine-weighted hemisphere sample around *normal*.

    The returned vector lies in the hemisphere whose pole is *normal*.  Used
    by the AO and path integrators for diffuse scattering.
    """
    v = _random_in_unit_sphere()
    if v.dot(normal) < 0.0:
        v = -v
    return v