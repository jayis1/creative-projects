"""texture.py — Procedural and image-based textures for materials.

A *texture* maps a surface coordinate (u, v) and/or world-space point (p) to
a color (:class:`Vec3`).  Materials delegate their ``albedo`` to a texture so
that surfaces can show procedural patterns (solid color, checkerboard, Perlin
noise, turbulence, marble) or image-based maps without changing the shading
math.

Textures are picklable so they work with multi-process rendering.

Classes
-------
* :class:`Texture`          – abstract base
* :class:`SolidColor`       – constant color (the default)
* :class:`CheckerTexture`   – 3-D checkerboard (world-space, unlike Checker material)
* :class:`PerlinNoise`      – value-noise gradient interpolation
* :class:`NoiseTexture`     – Perlin-based smooth noise color map
* :class:`Turbulence`       – fractal-sum-of-abs-noise (turbulence)
* :class:`Marble`           – sinusoidal marble streaks modulated by turbulence
* :class:`ImageTexture`     – sample colors from an in-memory image buffer
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from .vec import Vec3

__all__ = [
    "Texture",
    "SolidColor",
    "CheckerTexture",
    "PerlinNoise",
    "NoiseTexture",
    "Turbulence",
    "Marble",
    "ImageTexture",
]


class Texture:
    """Abstract base class.  Subclasses implement :meth:`value`."""

    def value(self, u: float, v: float, p: Vec3) -> Vec3:
        raise NotImplementedError


class SolidColor(Texture):
    """A texture that always returns the same color."""

    __slots__ = ("color",)

    def __init__(self, color: Vec3) -> None:
        self.color = color

    @classmethod
    def from_rgb(cls, r: float, g: float, b: float) -> "SolidColor":
        return cls(Vec3(r, g, b))

    def value(self, u: float, v: float, p: Vec3) -> Vec3:
        return self.color

    def __repr__(self) -> str:
        return f"SolidColor({self.color!r})"


class CheckerTexture(Texture):
    """A 3-D checkerboard in *world space* (unlike the Checker material which
    delegates to two child *materials*).

    ``scale`` controls the cell size: larger values make smaller checks.
    """

    __slots__ = ("even", "odd", "scale")

    def __init__(
        self,
        even: Texture,
        odd: Texture,
        scale: float = 1.0,
    ) -> None:
        self.even = even
        self.odd = odd
        self.scale = max(1e-6, float(scale))

    def value(self, u: float, v: float, p: Vec3) -> Vec3:
        s = 1.0 / self.scale
        n = (
            int(math.floor(p.x * s))
            + int(math.floor(p.y * s))
            + int(math.floor(p.z * s))
        )
        return self.even.value(u, v, p) if (n & 1) == 0 else self.odd.value(u, v, p)


# --------------------------------------------------------------------------- #
# Perlin noise (value noise with smoothstep interpolation)
# --------------------------------------------------------------------------- #
class PerlinNoise:
    """A compact value-noise generator using a fixed permutation table.

    Produces smooth [0, 1) noise in 3-D.  Seeded for reproducibility and
    picklable for multi-process rendering.
    """

    __slots__ = ("perm", "scale")

    def __init__(self, seed: int = 0, scale: float = 1.0) -> None:
        import random as _r

        rng = _r.Random(seed)
        perm = list(range(256))
        rng.shuffle(perm)
        # Duplicate so we can index without masking.
        self.perm = perm + perm
        self.scale = max(1e-6, float(scale))

    def _hash(self, xi: int, yi: int, zi: int) -> float:
        """Return a pseudo-random gradient value in [0, 1) for a lattice cell."""
        return self.perm[(self.perm[(self.perm[xi & 255] + yi) & 255] + zi) & 255] / 255.0

    @staticmethod
    def _fade(t: float) -> float:
        """Quintic smoothstep: 6t⁵ − 15t⁴ + 10t³ (Perlin's improved fade)."""
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    def noise(self, p: Vec3) -> float:
        """Smooth 3-D value noise at point *p*, in [0, 1)."""
        s = self.scale
        x, y, z = p.x * s, p.y * s, p.z * s
        xi, yi, zi = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))
        fx, fy, fz = x - xi, y - yi, z - zi
        u = self._fade(fx)
        v = self._fade(fy)
        w = self._fade(fz)

        # 8 corner hashes
        c000 = self._hash(xi, yi, zi)
        c100 = self._hash(xi + 1, yi, zi)
        c010 = self._hash(xi, yi + 1, zi)
        c110 = self._hash(xi + 1, yi + 1, zi)
        c001 = self._hash(xi, yi, zi + 1)
        c101 = self._hash(xi + 1, yi, zi + 1)
        c011 = self._hash(xi, yi + 1, zi + 1)
        c111 = self._hash(xi + 1, yi + 1, zi + 1)

        # Trilinear interpolation of the corner values.
        x0 = c000 * (1 - u) + c100 * u
        x1 = c010 * (1 - u) + c110 * u
        y0 = x0 * (1 - v) + x1 * v
        x0b = c001 * (1 - u) + c101 * u
        x1b = c011 * (1 - u) + c111 * u
        y1 = x0b * (1 - v) + x1b * v
        return y0 * (1 - w) + y1 * w

    def turbulence(self, p: Vec3, depth: int = 7) -> float:
        """Fractal Brownian motion (sum of abs(noise) with decreasing amplitude)."""
        total = 0.0
        amp = 1.0
        freq = 1.0
        for _ in range(depth):
            total += amp * abs(self.noise(p * freq) - 0.5) * 2.0
            amp *= 0.5
            freq *= 2.0
        return min(1.0, total)


class NoiseTexture(Texture):
    """Smooth Perlin noise mapped to a color range."""

    __slots__ = ("color1", "color2", "perlin")

    def __init__(
        self,
        color1: Optional[Vec3] = None,
        color2: Optional[Vec3] = None,
        scale: float = 4.0,
        seed: int = 0,
    ) -> None:
        self.color1 = color1 if color1 is not None else Vec3(0.2, 0.2, 0.2)
        self.color2 = color2 if color2 is not None else Vec3(0.8, 0.8, 0.8)
        self.perlin = PerlinNoise(seed=seed, scale=scale)

    def value(self, u: float, v: float, p: Vec3) -> Vec3:
        t = self.perlin.noise(p)
        return self.color1.lerp(self.color2, t)


class Turbulence(Texture):
    """Turbulent noise texture (fractal Brownian motion)."""

    __slots__ = ("color", "perlin", "depth")

    def __init__(
        self,
        color: Optional[Vec3] = None,
        scale: float = 4.0,
        depth: int = 7,
        seed: int = 0,
    ) -> None:
        self.color = color if color is not None else Vec3(0.5, 0.5, 0.5)
        self.perlin = PerlinNoise(seed=seed, scale=scale)
        self.depth = depth

    def value(self, u: float, v: float, p: Vec3) -> Vec3:
        t = self.perlin.turbulence(p, depth=self.depth)
        return self.color * t


class Marble(Texture):
    """Procedural marble — sinusoidal veins modulated by turbulence."""

    __slots__ = ("color1", "color2", "perlin", "scale", "depth")

    def __init__(
        self,
        color1: Optional[Vec3] = None,
        color2: Optional[Vec3] = None,
        scale: float = 4.0,
        depth: int = 7,
        seed: int = 0,
    ) -> None:
        self.color1 = color1 if color1 is not None else Vec3(0.9, 0.9, 0.95)
        self.color2 = color2 if color2 is not None else Vec3(0.1, 0.1, 0.15)
        self.perlin = PerlinNoise(seed=seed, scale=scale)
        self.scale = scale
        self.depth = depth

    def value(self, u: float, v: float, p: Vec3) -> Vec3:
        turb = self.perlin.turbulence(p, depth=self.depth)
        marble = 0.5 * (1.0 + math.sin(self.scale * p.x + 2.0 * turb))
        return self.color1.lerp(self.color2, marble)


class ImageTexture(Texture):
    """Sample colors from an in-memory image buffer.

    The buffer is a 2-D list of :class:`Vec3` (linear float colors) or a flat
    ``bytes`` RGB buffer with the given ``width``/``height``.  Coordinates wrap
    with a repeat mode (fractional part) by default.
    """

    __slots__ = ("width", "height", "_data", "_flat")

    def __init__(self, data, width: int, height: int) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        if isinstance(data, (bytes, bytearray)):
            self._flat = True
            self._data = bytes(data)
        else:
            self._flat = False
            self._data = list(data)

    @classmethod
    def from_pixels(cls, pixels: "list[list[Vec3]]") -> "ImageTexture":
        height = len(pixels)
        width = len(pixels[0]) if height else 1
        flat = bytearray()
        for row in pixels:
            for px in row:
                r = max(0, min(255, int(px.x * 255)))
                g = max(0, min(255, int(px.y * 255)))
                b = max(0, min(255, int(px.z * 255)))
                flat += bytes((r, g, b))
        return cls(bytes(flat), width, height)

    def value(self, u: float, v: float, p: Vec3) -> Vec3:
        # Repeat wrap via fractional part.
        u = u - math.floor(u)
        v = v - math.floor(v)
        x = min(self.width - 1, int(u * self.width))
        y = min(self.height - 1, int(v * self.height))
        if self._flat:
            idx = (y * self.width + x) * 3
            return Vec3(
                self._data[idx] / 255.0,
                self._data[idx + 1] / 255.0,
                self._data[idx + 2] / 255.0,
            )
        px = self._data[y][x]
        return Vec3(px.x, px.y, px.z)