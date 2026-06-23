"""Texture sampling utilities."""

from __future__ import annotations

import math

from .math3d import Vec3, Vec2

__all__ = ["Texture", "CheckerTexture"]


class Texture:
    """A 2D RGBA texture stored as a list of ``Vec3`` colours (0..1).

    Supports nearest-neighbour and bilinear sampling with clamp-to-edge
    wrapping.
    """

    __slots__ = ("width", "height", "pixels")

    def __init__(self, width: int, height: int, pixels: list[Vec3] | None = None):
        if width <= 0 or height <= 0:
            raise ValueError(f"Texture dimensions must be positive, got {width}x{height}")
        self.width = int(width)
        self.height = int(height)
        if pixels is None:
            self.pixels = [Vec3(0, 0, 0)] * (self.width * self.height)
        else:
            if len(pixels) != width * height:
                raise ValueError(
                    f"Pixel list length {len(pixels)} != {width}x{height} = {width * height}")
            self.pixels = list(pixels)

    def _clamp_coord(self, c: float, size: int) -> int:
        """Clamp a floating-point texel coordinate to [0, size-1]."""
        ic = int(math.floor(c))
        if ic < 0:
            return 0
        if ic >= size:
            return size - 1
        return ic

    def sample_nearest(self, u: float, v: float) -> Vec3:
        """Nearest-neighbour sampling with clamp-to-edge.

        UV coordinates use the convention (0, 0) = top-left, (1, 1) =
        bottom-right, matching most rasterizer conventions.
        """
        x = u * self.width - 0.5
        y = v * self.height - 0.5
        ix = self._clamp_coord(x, self.width)
        iy = self._clamp_coord(y, self.height)
        return self.pixels[iy * self.width + ix]

    def sample_bilinear(self, u: float, v: float) -> Vec3:
        """Bilinear filtering with clamp-to-edge."""
        x = u * self.width - 0.5
        y = v * self.height - 0.5
        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        fx = x - x0
        fy = y - y0

        x0i = max(0, min(self.width - 1, x0))
        x1i = max(0, min(self.width - 1, x0 + 1))
        y0i = max(0, min(self.height - 1, y0))
        y1i = max(0, min(self.height - 1, y0 + 1))

        c00 = self.pixels[y0i * self.width + x0i]
        c10 = self.pixels[y0i * self.width + x1i]
        c01 = self.pixels[y1i * self.width + x0i]
        c11 = self.pixels[y1i * self.width + x1i]

        top = c00.lerp(c10, fx)
        bot = c01.lerp(c11, fx)
        return top.lerp(bot, fy)

    def sample(self, u: float, v: float, bilinear: bool = True) -> Vec3:
        """Sample the texture at UV coordinates (u, v)."""
        if bilinear:
            return self.sample_bilinear(u, v)
        return self.sample_nearest(u, v)


class CheckerTexture(Texture):
    """Procedural checkerboard texture."""

    def __init__(self, squares: int = 8,
                 color_a: Vec3 | None = None,
                 color_b: Vec3 | None = None):
        if squares < 1:
            raise ValueError("squares must be >= 1")
        self.squares = squares
        self.color_a = color_a or Vec3(0.9, 0.9, 0.9)
        self.color_b = color_b or Vec3(0.2, 0.2, 0.3)
        # Build a backing texture for bilinear sampling at the edges
        res = squares * 16
        pixels = []
        for y in range(res):
            for x in range(res):
                cx = (x * squares) // res
                cy = (y * squares) // res
                if (cx + cy) % 2 == 0:
                    pixels.append(self.color_a)
                else:
                    pixels.append(self.color_b)
        super().__init__(res, res, pixels)