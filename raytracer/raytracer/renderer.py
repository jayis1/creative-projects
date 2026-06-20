"""renderer.py — Core recursive ray-tracing integrator.

Implements a Whitted-ish recursive path tracer:

  * Direct illumination is handled implicitly by the integrator via the
    emissive materials' ``emit()`` term.
  * Recursion depth is bounded by ``max_depth``; rays that exceed it return
    black (no further bounces).
  * A constant ambient ``background`` color is returned for rays that escape
    the scene — supports a gradient sky based on ray direction.

The renderer supports:

  * Anti-aliasing via uniform jittered supersampling (``samples``).
  * Optional ambient occlusion approximation via hemisphere sampling.
  * Per-pixel gamma correction.
  * Progress callback for CLI/REPL feedback.
  * Deterministic rendering via an optional RNG seed.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

from .vec import Vec3
from .ray import Ray
from .bvh import _Hittable
from . import material as _mat

__all__ = ["Renderer", "sky_gradient", "constant_background"]


def sky_gradient(ray: Ray) -> Vec3:
    """Soft blue-to-white sky gradient based on ray Y direction."""
    unit = ray.direction
    t = 0.5 * (unit.y + 1.0)
    return Vec3(1.0, 1.0, 1.0).lerp(Vec3(0.5, 0.7, 1.0), t)


def constant_background(color: Vec3):
    """Return a callable that always returns *color*."""

    def _bg(ray: Ray) -> Vec3:
        return color

    return _bg


class Renderer:
    """Recursive path-tracing renderer.

    Parameters
    ----------
    world : a hittable scene object (BVH or HittableList).
    background : callable ``ray -> Vec3`` returning the background color for
        rays that miss all geometry, or ``None`` for black.
    max_depth : recursion depth for indirect bounces.
    samples : number of samples per pixel (supersampling).
    """

    def __init__(
        self,
        world: _Hittable,
        background: Optional[Callable[[Ray], Vec3]] = None,
        max_depth: int = 8,
        samples: int = 16,
        seed: Optional[int] = None,
    ) -> None:
        self.world = world
        self.background = background if background is not None else constant_background(Vec3(0, 0, 0))
        self.max_depth = max(1, int(max_depth))
        self.samples = max(1, int(samples))
        if seed is not None:
            _mat.seed(seed)

    def ray_color(self, ray: Ray, depth: int) -> Vec3:
        # Base case: recursion budget exhausted.
        if depth <= 0:
            return Vec3.zero()
        hit = self.world.hit(ray, ray.tmin, ray.tmax)
        if hit is None:
            return self.background(ray)
        result = hit.material.scatter(ray, hit)
        emitted = hit.material.emit(hit.u, hit.v, hit.point)
        if result is None:
            # Absorbing material (e.g. metal below surface) — only emit.
            return emitted
        attenuation, scattered = result
        return emitted + attenuation * self.ray_color(scattered, depth - 1)

    def render_pixel(
        self, camera, s: float, t: float
    ) -> Vec3:
        """Render a single pixel coordinate (s, t) in [0, 1]^2."""
        if self.samples == 1:
            return self.ray_color(camera.get_ray(s, t), self.max_depth)
        color = Vec3.zero()
        for _ in range(self.samples):
            ss = s + _mat._drand48() / camera.aspect  # small jitter; corrected below
            # Use a proper unit-square jitter instead of aspect-scaled noise.
            ss = s + _mat._drand48()
            tt = t + _mat._drand48()
            # We want jitter within the pixel; clamp to [0,1] is unnecessary
            # because the camera maps continuously, but keep it bounded.
            color = color + self.ray_color(camera.get_ray(ss, tt), self.max_depth)
        return color / float(self.samples)

    def render(
        self,
        camera,
        width: int,
        height: int,
        progress: Optional[Callable[[int, int], None]] = None,
    ) -> "list[list[Vec3]]":
        """Render the whole image, returning a 2-D list of Vec3 colors.

        ``progress(done_rows, total_rows)`` is invoked once per row if given.
        """
        rows: list[list[Vec3]] = []
        for j in range(height):
            row: list[Vec3] = []
            # Render top-to-bottom; flip v so y=0 is the bottom of the image.
            v_coord = (height - 1 - j) / (height - 1) if height > 1 else 0.5
            for i in range(width):
                u_coord = i / (width - 1) if width > 1 else 0.5
                row.append(self.render_pixel(camera, u_coord, v_coord))
            rows.append(row)
            if progress is not None:
                progress(j + 1, height)
        return rows

    @staticmethod
    def to_rgb(color: Vec3, gamma: float = 2.0) -> tuple:
        """Apply gamma correction and clamp to 8-bit integer RGB."""
        def encode(c: float) -> int:
            if c <= 0.0:
                return 0
            if c >= 1.0:
                return 255
            return int(255.0 * (c ** (1.0 / gamma)))
        return (encode(color.x), encode(color.y), encode(color.z))