"""renderer.py — Core recursive ray-tracing integrator.

Provides three rendering modes selectable at render time:

* ``"path"`` — a recursive Whitted-style path tracer.  Direct illumination is
  handled implicitly through emissive ``Material.emit()`` and indirect bounces
  accumulate attenuation multiplicatively.  Bounded by ``max_depth``.
* ``"ao"`` — ambient occlusion: for each hit point, sample the hemisphere and
  count occluded rays, shading grey by visibility.  Fast, no-light preview.
* ``"normal"`` — a debug mode that shades each hit by its surface normal
  mapped into [0, 1] RGB.  Useful for validating geometry / camera setups.

Common features across modes:

* Anti-aliasing via uniform jittered supersampling (``samples``).
* Per-pixel gamma correction (configurable gamma).
* Progress callback for CLI / REPL feedback.
* Deterministic rendering via an optional RNG seed.
* Optional multi-threaded, tile-based rendering using a process pool so the
  heavy ray work fans out across CPU cores.
"""

from __future__ import annotations

import math
from typing import Callable, Optional, Iterable

from .vec import Vec3
from .ray import Ray
from .bvh import _Hittable
from . import material as _mat

__all__ = [
    "Renderer",
    "sky_gradient",
    "constant_background",
    "MODES",
]

MODES = ("path", "ao", "normal")


def sky_gradient(ray: Ray) -> Vec3:
    """Soft blue-to-white sky gradient based on ray Y direction."""
    unit = ray.direction
    t = 0.5 * (unit.y + 1.0)
    return Vec3(1.0, 1.0, 1.0).lerp(Vec3(0.5, 0.7, 1.0), t)


class ConstantBackground:
    """A picklable background callable that always returns a fixed color.

    Used in place of a closure so scene objects remain picklable for
    multi-process rendering.
    """

    __slots__ = ("color",)

    def __init__(self, color: Vec3) -> None:
        self.color = color

    def __call__(self, ray: Ray) -> Vec3:
        return self.color

    def __repr__(self) -> str:
        return f"ConstantBackground({self.color!r})"


def constant_background(color: Vec3):
    """Return a picklable callable that always returns *color*."""
    return ConstantBackground(color)


class Renderer:
    """Recursive path-tracing renderer with selectable integrator modes.

    Parameters
    ----------
    world : a hittable scene object (BVH or HittableList).
    background : callable ``ray -> Vec3`` returning the background color for
        rays that miss all geometry, or ``None`` for black.
    max_depth : recursion depth for indirect bounces (path mode).
    samples : number of samples per pixel (supersampling / AO samples).
    mode : integrator mode — ``"path"``, ``"ao"``, or ``"normal"``.
    ao_distance : maximum ray length for AO occlusion tests.
    gamma : display gamma applied during tone mapping.
    seed : optional integer seed for deterministic output.
    """

    def __init__(
        self,
        world: _Hittable,
        background: Optional[Callable[[Ray], Vec3]] = None,
        max_depth: int = 8,
        samples: int = 16,
        mode: str = "path",
        ao_distance: float = 1e9,
        gamma: float = 2.0,
        seed: Optional[int] = None,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown render mode '{mode}'; choose from {MODES}")
        self.world = world
        self.background = (
            background if background is not None else constant_background(Vec3(0, 0, 0))
        )
        self.max_depth = max(1, int(max_depth))
        self.samples = max(1, int(samples))
        self.mode = mode
        self.ao_distance = float(ao_distance)
        self.gamma = max(0.1, float(gamma))
        if seed is not None:
            _mat.seed(seed)

    # ------------------------------------------------------------------ #
    # Integrators
    # ------------------------------------------------------------------ #
    def ray_color(self, ray: Ray, depth: int) -> Vec3:
        """Recursive path-tracer integrator (mode == 'path')."""
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

    def _ao_color(self, ray: Ray, n_samples: int) -> Vec3:
        """Ambient-occlusion integrator: white where the hemisphere is open."""
        hit = self.world.hit(ray, ray.tmin, ray.tmax)
        if hit is None:
            return self.background(ray)
        occluded = 0
        for _ in range(n_samples):
            # Cosine-weighted hemisphere sample around the surface normal.
            s = _mat._random_in_unit_sphere()
            if s.dot(hit.normal) < 0.0:
                s = -s
            ao_ray = Ray(hit.point + hit.normal * 1e-4, s, tmax=self.ao_distance)
            if self.world.hit(ao_ray, 1e-4, self.ao_distance) is not None:
                occluded += 1
        vis = 1.0 - occluded / float(n_samples)
        return Vec3(vis, vis, vis)

    def _normal_color(self, ray: Ray) -> Vec3:
        """Debug integrator: encode the surface normal as a color."""
        hit = self.world.hit(ray, ray.tmin, ray.tmax)
        if hit is None:
            return self.background(ray)
        n = hit.normal
        return Vec3(0.5 * n.x + 0.5, 0.5 * n.y + 0.5, 0.5 * n.z + 0.5)

    def _shade_primary(self, ray: Ray) -> Vec3:
        """Dispatch the configured integrator on a single primary ray."""
        if self.mode == "path":
            return self.ray_color(ray, self.max_depth)
        if self.mode == "ao":
            return self._ao_color(ray, self.samples)
        if self.mode == "normal":
            return self._normal_color(ray)
        # Unreachable — validated in __init__.
        raise AssertionError(f"bad mode {self.mode!r}")

    # ------------------------------------------------------------------ #
    # Pixel + image
    # ------------------------------------------------------------------ #
    def render_pixel(
        self,
        camera,
        s: float,
        t: float,
        pixel_width: float = 0.0,
        pixel_height: float = 0.0,
    ) -> Vec3:
        """Render a single pixel at normalized coord (s, t) in [0, 1]^2.

        Anti-aliasing: ``samples`` jittered rays within the pixel cell are
        averaged.  The jitter is centred on the pixel centre (s, t) and bounded
        to ``±pixel_width/2`` / ``±pixel_height/2`` so samples never leave the
        pixel cell — this prevents edge bleed where the last pixel would
        otherwise sample beyond the image plane.

        For AO mode the per-pixel sample count instead controls the hemisphere
        occlusion samples (the primary ray itself is not supersampled in AO to
        keep it cheap); pass ``--samples`` accordingly.
        """
        if self.mode == "ao":
            # One primary ray; hemisphere sampling count == samples.
            return self._ao_color(camera.get_ray(s, t), self.samples)
        if self.samples == 1:
            return self._shade_primary(camera.get_ray(s, t))
        color = Vec3.zero()
        inv = 1.0 / float(self.samples)
        half_w = pixel_width * 0.5
        half_h = pixel_height * 0.5
        for _ in range(self.samples):
            # Jitter within the pixel cell, centred on (s, t).
            ss = s + (_mat._drand48() - 0.5) * pixel_width
            tt = t + (_mat._drand48() - 0.5) * pixel_height
            color = color + self._shade_primary(camera.get_ray(ss, tt))
        return color * inv

    def render(
        self,
        camera,
        width: int,
        height: int,
        progress: Optional[Callable[[int, int], None]] = None,
        num_threads: int = 1,
    ) -> "list[list[Vec3]]":
        """Render the whole image, returning a 2-D list of Vec3 colors.

        ``progress(done_rows, total_rows)`` is invoked once per row if given.
        ``num_threads > 1`` enables multi-process tile rendering.
        """
        if width < 1 or height < 1:
            raise ValueError("width and height must be >= 1")
        if num_threads > 1:
            return self._render_parallel(camera, width, height, progress, num_threads)
        return self._render_serial(camera, width, height, progress)

    def _render_serial(
        self, camera, width: int, height: int, progress
    ) -> "list[list[Vec3]]":
        # Pixel-cell extents in normalized image space (so jitter stays inside
        # the pixel and never samples beyond the [0, 1] image plane).
        pw = 1.0 / width
        ph = 1.0 / height
        rows: list[list[Vec3]] = []
        for j in range(height):
            row: list[Vec3] = []
            # Render top-to-bottom; flip v so y=0 is the bottom of the image.
            # Use pixel *centres*: (i+0.5)/width keeps every sample in [0, 1].
            v_center = 1.0 - (j + 0.5) / height
            for i in range(width):
                u_center = (i + 0.5) / width
                row.append(self.render_pixel(camera, u_center, v_center, pw, ph))
            rows.append(row)
            if progress is not None:
                progress(j + 1, height)
        return rows

    def _render_parallel(
        self, camera, width: int, height: int, progress, num_threads: int
    ) -> "list[list[Vec3]]":
        """Render rows across a process pool.

        Each worker receives the picklable renderer (world + config) plus the
        camera and a slice of row indices, returning finished rows.  The
        process pool is created per call and torn down afterwards so memory is
        reclaimed between renders.
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed

        rows_per_job = max(1, height // num_threads)
        jobs = []
        for start in range(0, height, rows_per_job):
            end = min(start + rows_per_job, height)
            jobs.append((start, end))

        result: dict[int, list[Vec3]] = {}
        done = 0
        with ProcessPoolExecutor(max_workers=num_threads) as pool:
            futures = {
                pool.submit(_render_rows, self, camera, width, height, s, e): (s, e)
                for (s, e) in jobs
            }
            for fut in as_completed(futures):
                s, e = futures[fut]
                rendered = fut.result()
                for idx, row in enumerate(rendered):
                    result[s + idx] = row
                done += (e - s)
                if progress is not None:
                    progress(done, height)
        return [result[j] for j in range(height)]

    # ------------------------------------------------------------------ #
    # Tone mapping
    # ------------------------------------------------------------------ #
    def to_rgb(self, color: Vec3) -> tuple:
        """Apply gamma correction and clamp to 8-bit integer RGB (instance)."""
        return _encode_gamma(color, self.gamma)

    @staticmethod
    def encode(color: Vec3, gamma: float = 2.0) -> tuple:
        """Apply gamma correction and clamp to 8-bit integer RGB.

        Kept as a staticmethod so callers without a Renderer instance (e.g.
        :mod:`imageio`) can still tone-map colors.
        """
        return _encode_gamma(color, gamma)


def _encode_gamma(color: Vec3, gamma: float) -> tuple:
    inv = 1.0 / gamma

    def encode(c: float) -> int:
        if c <= 0.0:
            return 0
        if c >= 1.0:
            return 255
        return int(255.0 * (c ** inv))

    return (encode(color.x), encode(color.y), encode(color.z))


# --------------------------------------------------------------------------- #
# Worker function for parallel rendering (module-level for picklability).
# --------------------------------------------------------------------------- #
def _render_rows(renderer: Renderer, camera, width: int, height: int,
                 start: int, end: int) -> "list[list[Vec3]]":
    """Render rows ``[start, end)`` of the image — module-level for pickling."""
    pw = 1.0 / width
    ph = 1.0 / height
    out: list[list[Vec3]] = []
    for j in range(start, end):
        # Top-to-bottom display; v=0 is the bottom of the image.
        v_center = 1.0 - (j + 0.5) / height
        row: list[Vec3] = []
        for i in range(width):
            u_center = (i + 0.5) / width
            row.append(renderer.render_pixel(camera, u_center, v_center, pw, ph))
        out.append(row)
    return out