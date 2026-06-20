"""renderer.py — Core recursive ray-tracing integrator.

Provides four rendering modes selectable at render time:

* ``"path"``   — a recursive Whitted-style path tracer.  Direct illumination is
  handled implicitly through emissive ``Material.emit()`` and indirect bounces
  accumulate attenuation multiplicatively.  Bounded by ``max_depth``.  Russian
  roulette path termination kicks in after ``rr_start_depth`` bounces.
* ``"ao"``    — ambient occlusion: for each hit point, sample the hemisphere and
  count occluded rays, shading grey by visibility.  Fast, no-light preview.
* ``"normal"`` — a debug mode that shades each hit by its surface normal
  mapped into [0, 1] RGB.  Useful for validating geometry / camera setups.
* ``"depth"`` — encodes the ray-hit distance as a grayscale, useful for
  debugging the scene scale and camera placement.

Common features across modes:

* Anti-aliasing via uniform jittered supersampling (``samples``).
* Per-pixel gamma correction (configurable gamma).
* Progress callback for CLI / REPL feedback.
* Deterministic rendering via an optional RNG seed.
* Optional multi-threaded, tile-based rendering using a process pool so the
  heavy ray work fans out across CPU cores.
* Optional Next Event Estimation (direct light sampling) for the path
  integrator when a list of emissive primitives is provided.
* Render statistics (rays cast, bounces, elapsed time) collected during a
  render and available via :attr:`Renderer.stats`.
"""

from __future__ import annotations

import math
import time
from typing import Callable, Optional, Iterable, List

from .vec import Vec3
from .ray import Ray
from .bvh import _Hittable, HittableList
from . import material as _mat
from .material import Emissive
from .logging import logger

__all__ = [
    "Renderer",
    "RenderStats",
    "sky_gradient",
    "constant_background",
    "ConstantBackground",
    "MODES",
]

MODES = ("path", "ao", "normal", "depth")


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


class RenderStats:
    """Lightweight render-statistics counter."""

    __slots__ = ("rays", "bounces", "hits", "misses", "elapsed", "width", "height")

    def __init__(self) -> None:
        self.rays: int = 0
        self.bounces: int = 0
        self.hits: int = 0
        self.misses: int = 0
        self.elapsed: float = 0.0
        self.width: int = 0
        self.height: int = 0

    def __repr__(self) -> str:
        return (
            f"RenderStats(rays={self.rays}, bounces={self.bounces}, "
            f"hits={self.hits}, misses={self.misses}, "
            f"elapsed={self.elapsed:.3f}s, "
            f"{self.width}x{self.height})"
        )

    def rays_per_second(self) -> float:
        return self.rays / self.elapsed if self.elapsed > 0 else 0.0

    def as_dict(self) -> dict:
        return {
            "rays": self.rays,
            "bounces": self.bounces,
            "hits": self.hits,
            "misses": self.misses,
            "elapsed_s": round(self.elapsed, 4),
            "width": self.width,
            "height": self.height,
            "rays_per_second": round(self.rays_per_second(), 1),
        }


class Renderer:
    """Recursive path-tracing renderer with selectable integrator modes.

    Parameters
    ----------
    world : a hittable scene object (BVH or HittableList).
    background : callable ``ray -> Vec3`` returning the background color for
        rays that miss all geometry, or ``None`` for black.
    max_depth : recursion depth for indirect bounces (path mode).
    samples : number of samples per pixel (supersampling / AO samples).
    mode : integrator mode — ``"path"``, ``"ao"``, ``"normal"``, or ``"depth"``.
    ao_distance : maximum ray length for AO occlusion tests.
    gamma : display gamma applied during tone mapping.
    seed : optional integer seed for deterministic output.
    rr_start_depth : Russian-roulette path termination starts after this many
        bounces (only in path mode).  0 disables it.
    lights : optional list of emissive hittables for Next Event Estimation
        (direct light sampling) in path mode.  If non-empty, each diffuse
        bounce samples a random light source explicitly.
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
        rr_start_depth: int = 0,
        lights: Optional[List[_Hittable]] = None,
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
        self.rr_start_depth = max(0, int(rr_start_depth))
        self.lights: List[_Hittable] = list(lights) if lights else []
        self.stats = RenderStats()
        if seed is not None:
            _mat.seed(seed)

    # ------------------------------------------------------------------ #
    # Integrators
    # ------------------------------------------------------------------ #
    def ray_color(self, ray: Ray, depth: int) -> Vec3:
        """Recursive path-tracer integrator (mode == 'path').

        Supports Russian-roulette path termination (after ``rr_start_depth``
        bounces) and Next Event Estimation when ``self.lights`` is non-empty.
        """
        self.stats.rays += 1
        # Base case: recursion budget exhausted.
        if depth <= 0:
            return Vec3.zero()
        hit = self.world.hit(ray, ray.tmin, ray.tmax)
        if hit is None:
            self.stats.misses += 1
            return self.background(ray)
        self.stats.hits += 1
        self.stats.bounces += 1
        result = hit.material.scatter(ray, hit)
        emitted = hit.material.emit(hit.u, hit.v, hit.point)

        # Next Event Estimation: explicit light sampling for diffuse surfaces.
        # Only applies when the hit material is not itself emissive and we have
        # a light list to sample from.  We compute the direct lighting
        # contribution and add it to the emitted term.
        direct_light = Vec3.zero()
        if self.lights and not isinstance(hit.material, Emissive):
            direct_light = self._sample_lights(hit)

        if result is None:
            # Absorbing material (e.g. metal below surface) — only emit.
            return emitted + direct_light
        attenuation, scattered = result

        # Russian roulette: after rr_start_depth bounces, terminate the path
        # with probability (1 - p) and scale survivors by 1/p so the estimate
        # stays unbiased.  p is tied to the luminance of the attenuation.
        if self.rr_start_depth > 0 and depth < (self.max_depth - self.rr_start_depth):
            lum = 0.2126 * attenuation.x + 0.7152 * attenuation.y + 0.0722 * attenuation.z
            p = max(0.05, min(0.95, lum))
            if _mat._drand48() > p:
                return emitted + direct_light
            scale = 1.0 / p
            return (emitted + direct_light
                    + attenuation * self.ray_color(scattered, depth - 1) * scale)
        return emitted + direct_light + attenuation * self.ray_color(scattered, depth - 1)

    def _sample_lights(self, hit) -> Vec3:
        """Sample one random light from ``self.lights`` for NEE.

        Returns the direct radiance contribution from that light toward the
        hit point.  Uses a simple uniform pick + cosine term.  Shadow rays are
        cast to test visibility.
        """
        if not self.lights:
            return Vec3.zero()
        import random as _r
        light = self.lights[_r.Random().randrange(len(self.lights))]
        # Sample a point on the light's bounding box (approximation; for area
        # lights this is conservative).
        aabb = light.bbox()
        c = aabb.center()
        direction = c - hit.point
        dist = direction.length()
        if dist < 1e-9:
            return Vec3.zero()
        direction = direction / dist
        # Shadow ray.
        shadow_ray = Ray(hit.point + hit.normal * 1e-4, direction, tmax=dist - 1e-4)
        if self.world.hit(shadow_ray, 1e-4, dist - 1e-4) is not None:
            return Vec3.zero()  # occluded
        # Material emissive contribution.
        # Find a hit on the light to read its emission.
        light_hit = light.hit(shadow_ray, 1e-4, dist)
        if light_hit is None:
            return Vec3.zero()
        emit = light_hit.material.emit(light_hit.u, light_hit.v, light_hit.point)
        cos_theta = max(0.0, direction.dot(hit.normal))
        return emit * cos_theta

    def _ao_color(self, ray: Ray, n_samples: int) -> Vec3:
        """Ambient-occlusion integrator: white where the hemisphere is open."""
        self.stats.rays += 1
        hit = self.world.hit(ray, ray.tmin, ray.tmax)
        if hit is None:
            self.stats.misses += 1
            return self.background(ray)
        self.stats.hits += 1
        occluded = 0
        for _ in range(n_samples):
            # Cosine-weighted hemisphere sample around the surface normal.
            s = _mat._random_in_unit_sphere()
            if s.dot(hit.normal) < 0.0:
                s = -s
            ao_ray = Ray(hit.point + hit.normal * 1e-4, s, tmax=self.ao_distance)
            self.stats.rays += 1
            if self.world.hit(ao_ray, 1e-4, self.ao_distance) is not None:
                occluded += 1
        vis = 1.0 - occluded / float(n_samples)
        return Vec3(vis, vis, vis)

    def _normal_color(self, ray: Ray) -> Vec3:
        """Debug integrator: encode the surface normal as a color."""
        self.stats.rays += 1
        hit = self.world.hit(ray, ray.tmin, ray.tmax)
        if hit is None:
            self.stats.misses += 1
            return self.background(ray)
        self.stats.hits += 1
        n = hit.normal
        return Vec3(0.5 * n.x + 0.5, 0.5 * n.y + 0.5, 0.5 * n.z + 0.5)

    def _depth_color(self, ray: Ray) -> Vec3:
        """Debug integrator: encode the hit distance as a grayscale value.

        Distances are normalized by ``self.ao_distance`` when it is finite,
        otherwise by 20.0 (a reasonable default for indoor scenes).
        """
        self.stats.rays += 1
        hit = self.world.hit(ray, ray.tmin, ray.tmax)
        if hit is None:
            self.stats.misses += 1
            return self.background(ray)
        self.stats.hits += 1
        max_dist = self.ao_distance if self.ao_distance < 1e8 else 20.0
        t = max(0.0, min(1.0, hit.t / max_dist))
        return Vec3(t, t, t)

    def _shade_primary(self, ray: Ray) -> Vec3:
        """Dispatch the configured integrator on a single primary ray."""
        if self.mode == "path":
            return self.ray_color(ray, self.max_depth)
        if self.mode == "ao":
            return self._ao_color(ray, self.samples)
        if self.mode == "normal":
            return self._normal_color(ray)
        if self.mode == "depth":
            return self._depth_color(ray)
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
        self.stats = RenderStats()
        self.stats.width = width
        self.stats.height = height
        t0 = time.time()
        if num_threads > 1:
            rows = self._render_parallel(camera, width, height, progress, num_threads)
        else:
            rows = self._render_serial(camera, width, height, progress)
        self.stats.elapsed = time.time() - t0
        logger.debug(
            "render done: %dx%d, %d rays, %.2fs (%.0f r/s)",
            width, height, self.stats.rays, self.stats.elapsed,
            self.stats.rays_per_second(),
        )
        return rows

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