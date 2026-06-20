"""camera.py — Pinhole camera with depth-of-field (aperture / focus)."""

from __future__ import annotations

import math

from .vec import Vec3
from .ray import Ray
from . import material as _mat

__all__ = ["Camera"]


class Camera:
    """A configurable pinhole camera.

    Parameters mirror the popular ``rtweekend`` parameterisation so scenes can
    be specified by ``lookfrom``/``lookat``/``up``/``vfov`` plus optional
    aperture and focus distance for depth-of-field effects.
    """

    def __init__(
        self,
        look_from: Vec3,
        look_at: Vec3,
        up: Vec3,
        vfov_deg: float,
        aspect: float,
        aperture: float = 0.0,
        focus_dist: float | None = None,
    ) -> None:
        self.look_from = look_from
        self.look_at = look_at
        self.up = up
        self.vfov = vfov_deg
        self.aspect = aspect
        self.aperture = aperture
        self.lens_radius = aperture * 0.5
        if focus_dist is None:
            # Default focus distance = distance to look_at.
            focus_dist = (look_from - look_at).length()
        self.focus_dist = focus_dist

        theta = math.radians(vfov_deg)
        half_h = math.tan(theta / 2.0)
        half_w = aspect * half_h

        w = (look_from - look_at).normalized()
        u = up.cross(w).normalized()
        v = w.cross(u)

        self.origin = look_from
        self.lower_left = (
            look_from
            - u * (half_w * focus_dist)
            - v * (half_h * focus_dist)
            - w * focus_dist
        )
        self.horizontal = u * (2.0 * half_w * focus_dist)
        self.vertical = v * (2.0 * half_h * focus_dist)
        self._u = u
        self._v = v
        self._w = w

    def get_ray(self, s: float, t: float) -> Ray:
        # Map (s, t) in [0, 1]^2 to the focal plane, perturbing the origin within
        # the lens disk for depth-of-field.
        rd = Vec3(0, 0, 0)
        if self.lens_radius > 0.0:
            rd = _mat._random_in_unit_sphere() * self.lens_radius
        offset = self._u * rd.x + self._v * rd.y
        origin = self.origin + offset
        direction = (
            self.lower_left
            + self.horizontal * s
            + self.vertical * t
            - origin
        )
        return Ray(origin, direction)