"""Iterated Function System (IFS) fractals.

An IFS fractal is defined by a set of affine transformations, each with an
associated probability. Starting from a point, we repeatedly pick a
transformation (weighted by its probability) and apply it, plotting the
resulting points. The classic example is the Barnsley Fern.
"""
from __future__ import annotations

import random
from typing import List, Sequence, Tuple

from .palettes import get_palette, _clamp_byte

RGB = Tuple[int, int, int]


class IFSFractal:
    """An Iterated Function System fractal.

    Parameters
    ----------
    transforms : list of (a, b, c, d, e, f, p) tuples
        Each transform is an affine map::

            x' = a·x + b·y + e
            y' = c·x + d·y + f

        with probability ``p`` of being chosen each iteration.
    """

    def __init__(self, transforms: Sequence[Tuple[float, ...]],
                 name: str = "custom"):
        self.transforms = list(transforms)
        self.name = name
        total_p = sum(t[6] for t in self.transforms)
        if total_p <= 0:
            raise ValueError("probabilities must sum to > 0")
        # Normalise probabilities
        self.transforms = [(*t[:6], t[6] / total_p) for t in self.transforms]

    def render(self, width: int = 400, height: int = 400,
               iterations: int = 100000, palette_name: str = "forest",
               palette_size: int = 256, seed=None,
               x_range=(0.0, 1.0), y_range=(0.0, 1.0),
               background: RGB = (0, 0, 0)) -> Tuple[List[RGB], dict]:
        """Render the IFS fractal using the chaos game.

        Returns a list of ``width*height`` RGB tuples.
        """
        rng = random.Random(seed)
        x, y = 0.0, 0.0
        # Accumulate hit counts for colouring by iteration depth.
        grid = [0] * (width * height)
        x_min, x_max = x_range
        y_min, y_max = y_range
        dx = (x_max - x_min)
        dy = (y_max - y_min)
        probs = [t[6] for t in self.transforms]
        # Pre-extract transform coefficients for speed
        coeffs = [(t[0], t[1], t[2], t[3], t[4], t[5]) for t in self.transforms]
        n_trans = len(coeffs)

        for i in range(iterations):
            # Pick a transform by probability
            r = rng.random()
            cum = 0.0
            idx = 0
            for j in range(n_trans):
                cum += probs[j]
                if r <= cum:
                    idx = j
                    break
            a, b, c, d, e, f = coeffs[idx]
            x, y = a * x + b * y + e, c * x + d * y + f

            if i < 20:  # skip warmup
                continue

            px = int((x - x_min) / dx * width) if dx > 0 else 0
            py = int((y - y_min) / dy * height) if dy > 0 else 0
            if 0 <= px < width and 0 <= py < height:
                grid[py * width + px] += 1

        max_val = max(grid) if grid else 1
        if max_val <= 0:
            max_val = 1
        palette = get_palette(palette_name, palette_size)
        pixels: List[RGB] = []
        for v in grid:
            if v <= 0:
                pixels.append(background)
            else:
                t = min(1.0, v / max_val)
                # Use log for better dynamic range
                t = (t ** 0.5)
                idx = max(0, min(palette_size - 1,
                                 int(t * (palette_size - 1))))
                pixels.append(palette[idx])

        return pixels, {"width": width, "height": height,
                         "kind": f"ifs-{self.name}",
                         "iterations": iterations}


# Classic IFS fractals ------------------------------------------------------ #

BARNSLEY_FERN = IFSFractal([
    (0.85, 0.04, -0.04, 0.85, 0.0, 1.6, 0.85),
    (0.20, -0.26, 0.23, 0.22, 0.0, 1.6, 0.07),
    (-0.15, 0.28, 0.26, 0.24, 0.0, 0.44, 0.07),
    (0.0, 0.0, 0.0, 0.16, 0.0, 0.0, 0.01),
], name="barnsley_fern")

SIERPINSKI_TRIANGLE = IFSFractal([
    (0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 1 / 3),
    (0.5, 0.0, 0.0, 0.5, 0.5, 0.0, 1 / 3),
    (0.5, 0.0, 0.0, 0.5, 0.25, 0.5, 1 / 3),
], name="sierpinski_triangle")

DRAGON_CURVE = IFSFractal([
    (0.824074, 0.281428, -0.212346, 0.864198, -1.88229, -0.110607, 0.787473),
    (0.088272, 0.522561, -0.463889, -0.377733, 0.035741, 0.67582, 0.212527),
], name="dragon_curve")


def render_ifs(ifs: IFSFractal, width: int = 400, height: int = 400,
               iterations: int = 100000, palette_name: str = "forest",
               **kw) -> Tuple[List[RGB], dict]:
    """Convenience wrapper for :meth:`IFSFractal.render`."""
    return ifs.render(width=width, height=height, iterations=iterations,
                       palette_name=palette_name, **kw)