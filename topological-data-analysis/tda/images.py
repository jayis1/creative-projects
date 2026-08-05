"""
Persistence images: a stable, vectorized representation of persistence
diagrams suitable for machine learning.

A persistence image transforms a persistence diagram into a 2D image (matrix)
by:
1. Transforming each point (b, d) to (b, d - b) (persistence-weighted coords).
2. Placing a Gaussian kernel at each transformed point.
3. Weighting each Gaussian by a weight function w(t) that down-weights
   low-persistence features (typically a linear or triangular weight).
4. Integrating over a grid to produce pixel values.

Reference: Adams et al., "Persistence Images: A Stable Vector Representation
of Persistent Homology" (2017).
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

from .diagram import PersistenceDiagram

Infinity = float("inf")


def persistence_image(
    diagram: PersistenceDiagram,
    resolution: int = 50,
    sigma: float = 1.0,
    weight_fn: Optional[Callable[[float], float]] = None,
    birth_range: Optional[Tuple[float, float]] = None,
    persistence_range: Optional[Tuple[float, float]] = None,
) -> Tuple[List[List[float]], Tuple[float, float], Tuple[float, float]]:
    """Compute the persistence image of a persistence diagram.

    Parameters
    ----------
    diagram : PersistenceDiagram
        The persistence diagram to transform.
    resolution : int
        Number of pixels along each axis (image is resolution x resolution).
    sigma : float
        Standard deviation of the Gaussian kernel.
    weight_fn : callable, optional
        Weight function w(persistence) -> float. Default: linear weight
        w(p) = min(p / max_persistence, 1.0).
    birth_range : (float, float), optional
        Range of birth values for the image. Default: [min, max] of births.
    persistence_range : (float, float), optional
        Range of persistence values. Default: [0, max_persistence].

    Returns
    -------
    image : list of list of float
        2D array of pixel values (row-major, persistence = y, birth = x).
    birth_range : (float, float)
    persistence_range : (float, float)
    """
    finite_pairs = [(p.birth, p.death) for p in diagram if p.death != Infinity]
    if not finite_pairs:
        # Empty image.
        return ([[0.0] * resolution for _ in range(resolution)],
                (0.0, 1.0), (0.0, 1.0))

    births = [b for b, _ in finite_pairs]
    persistences = [d - b for b, d in finite_pairs]
    max_pers = max(persistences) if persistences else 1.0

    if birth_range is None:
        b_min, b_max = min(births), max(births)
        if b_max == b_min:
            b_max = b_min + 1.0
    else:
        b_min, b_max = birth_range

    if persistence_range is None:
        p_min, p_max = 0.0, max_pers
        if p_max == 0:
            p_max = 1.0
    else:
        p_min, p_max = persistence_range

    if weight_fn is None:
        # Default linear weight: w(p) = p / max_pers (normalized).
        _max_pers = max_pers
        def _default_weight(p: float) -> float:
            return p / _max_pers if _max_pers > 0 else 1.0
        w_fn: Callable[[float], float] = _default_weight
    else:
        w_fn = weight_fn

    # Transform points to (birth, persistence) space.
    transformed = [(b, d - b) for b, d in finite_pairs]

    # Grid.
    b_step = (b_max - b_min) / resolution
    p_step = (p_max - p_min) / resolution

    image: List[List[float]] = [[0.0] * resolution for _ in range(resolution)]
    two_sigma_sq = 2.0 * sigma * sigma

    for b_val, p_val in transformed:
        w = w_fn(p_val)
        if w <= 0:
            continue
        for row in range(resolution):
            py = p_min + (row + 0.5) * p_step
            for col in range(resolution):
                px = b_min + (col + 0.5) * b_step
                dx = px - b_val
                dy = py - p_val
                dist_sq = dx * dx + dy * dy
                image[row][col] += w * math.exp(-dist_sq / two_sigma_sq)

    return image, (b_min, b_max), (p_min, p_max)


def image_to_ascii(image: List[List[float]], width: int = 40,
                   chars: str = " .:-=+*#%@") -> str:
    """Render a persistence image as an ASCII heatmap.

    Parameters
    ----------
    image : 2D list of float
        The persistence image pixel grid.
    width : int
        Output width in characters.
    chars : str
        Character ramp from low to high.
    """
    if not image:
        return ""
    rows = len(image)
    cols = len(image[0])
    if rows == 0 or cols == 0:
        return ""

    max_val = max(max(row) for row in image)
    if max_val == 0:
        max_val = 1.0

    # Sample: pick rows/cols to fit width.
    height = max(1, int(width * rows / cols * 0.5))  # ~2:1 aspect

    lines: List[str] = []
    for r in range(height):
        line = []
        for c in range(width):
            src_r = int(r / height * rows)
            src_c = int(c / width * cols)
            val = image[src_r][src_c] / max_val
            idx = min(len(chars) - 1, int(val * (len(chars) - 1)))
            line.append(chars[idx])
        lines.append("".join(line))
    return "\n".join(lines)