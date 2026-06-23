"""Texture sampling utilities with mipmapping support."""

from __future__ import annotations

import math

from .math3d import Vec3, Vec2

__all__ = ["Texture", "CheckerTexture", "MipTexture"]


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

    def downsample(self) -> "Texture":
        """Create a half-resolution mipmap level (2×2 box filter)."""
        nw = max(1, self.width // 2)
        nh = max(1, self.height // 2)
        pixels = []
        for y in range(nh):
            for x in range(nw):
                sx = x * 2
                sy = y * 2
                c00 = self.pixels[min(sy, self.height - 1) * self.width + min(sx, self.width - 1)]
                c10 = self.pixels[min(sy, self.height - 1) * self.width + min(sx + 1, self.width - 1)]
                c01 = self.pixels[min(sy + 1, self.height - 1) * self.width + min(sx, self.width - 1)]
                c11 = self.pixels[min(sy + 1, self.height - 1) * self.width + min(sx + 1, self.width - 1)]
                r = (c00.x + c10.x + c01.x + c11.x) * 0.25
                g = (c00.y + c10.y + c01.y + c11.y) * 0.25
                b = (c00.z + c10.z + c01.z + c11.z) * 0.25
                pixels.append(Vec3(r, g, b))
        return Texture(nw, nh, pixels)


class MipTexture(Texture):
    """Texture with pre-computed mipmap levels for distance-based filtering.

    Automatically generates a mipmap chain at construction time.  The
    appropriate level is selected based on the pixel footprint (approximated
    by the screen-space derivatives of the UV coordinates).
    """

    __slots__ = ("levels",)

    def __init__(self, width: int, height: int, pixels: list[Vec3] | None = None):
        super().__init__(width, height, pixels)
        self.levels: list[Texture] = [self]
        # Build mipmap chain
        current = self
        while current.width > 1 or current.height > 1:
            current = current.downsample()
            self.levels.append(current)

    def sample_mipmap(self, u: float, v: float, lod: float) -> Vec3:
        """Sample with mipmap selection based on LOD (level of detail).

        ``lod`` is the log2 of the pixel-to-texel ratio.  A LOD of 0
        means 1:1 mapping (use the full-resolution texture).  Higher
        values use smaller mipmap levels.
        """
        lod = max(0.0, lod)
        level_f = lod
        level = int(level_f)
        frac = level_f - level

        if level >= len(self.levels) - 1:
            return self.levels[-1].sample_bilinear(u, v)

        c0 = self.levels[level].sample_bilinear(u, v)
        c1 = self.levels[level + 1].sample_bilinear(u, v)
        return c0.lerp(c1, frac)

    def sample(self, u: float, v: float, bilinear: bool = True,
               lod: float = 0.0) -> Vec3:
        """Sample with optional mipmap filtering."""
        if lod > 0.01:
            return self.sample_mipmap(u, v, lod)
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