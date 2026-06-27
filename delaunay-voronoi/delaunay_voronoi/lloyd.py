"""
Lloyd's relaxation algorithm.

Repeatedly:

1. Build the Delaunay triangulation of the sites.
2. Build the (clipped) Voronoi diagram.
3. Move each site to the centroid of its Voronoi cell.

This converges towards a *centroidal Voronoi tessellation* where sites
coincide with cell centroids, producing evenly-spaced blue-noise-like
point distributions.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .delaunay import DelaunayTriangulation
from .geometry import Point, bounding_box
from .voronoi import VoronoiDiagram


def lloyd_relaxation(
    points: List[Point],
    iterations: int = 10,
    clip_box: Optional[Tuple[Point, Point]] = None,
    seed: Optional[int] = None,
) -> List[Point]:
    """Run Lloyd's relaxation for *iterations* steps and return new sites."""
    if not points:
        return []
    if iterations <= 0:
        return list(points)

    if clip_box is None:
        clip_box = bounding_box(points)

    rng = random.Random(seed)
    current = list(points)
    for _ in range(iterations):
        dt = DelaunayTriangulation.from_points(current)
        vd = VoronoiDiagram.from_delaunay(dt, clip_box=clip_box)
        new_points: List[Point] = []
        for site in current:
            cell = vd.cells.get(site)
            if cell is not None and len(cell.vertices) >= 3:
                c = cell.centroid()
                # Clamp to clip box so sites stay inside
                c = Point(
                    min(max(c.x, clip_box[0].x), clip_box[1].x),
                    min(max(c.y, clip_box[0].y), clip_box[1].y),
                )
                new_points.append(c)
            else:
                # Perturb slightly to break degeneracies
                new_points.append(site)
        current = new_points
    return current


def generate_poisson_seed(
    n: int, clip_box: Tuple[Point, Point], seed: Optional[int] = None
) -> List[Point]:
    """Generate *n* uniform random sites within *clip_box*."""
    rng = random.Random(seed)
    min_p, max_p = clip_box
    return [
        Point(
            rng.uniform(min_p.x, max_p.x),
            rng.uniform(min_p.y, max_p.y),
        )
        for _ in range(n)
    ]