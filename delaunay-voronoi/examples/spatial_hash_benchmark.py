#!/usr/bin/env python3
"""Demonstrate the spatial hash grid for fast nearest-neighbour queries.

Compares brute-force vs grid-accelerated lookup on a large point set.
"""

import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from delaunay_voronoi.geometry import Point
from delaunay_voronoi.spatial_hash import SpatialHashGrid


def main():
    rng = random.Random(42)
    pts = [Point(rng.uniform(0, 1000), rng.uniform(0, 1000)) for _ in range(500)]
    queries = [Point(rng.uniform(0, 1000), rng.uniform(0, 1000)) for _ in range(1000)]

    # Brute force
    t0 = time.perf_counter()
    for q in queries:
        min(pts, key=lambda p: p.distance_to(q))
    t_brute = time.perf_counter() - t0

    # Grid
    grid = SpatialHashGrid.from_points(pts, cell_size=50)
    t0 = time.perf_counter()
    for q in queries:
        grid.nearest(q)
    t_grid = time.perf_counter() - t0

    print(f"Points: {len(pts)}, Queries: {len(queries)}")
    print(f"Brute force: {t_brute:.4f}s")
    print(f"Spatial hash: {t_grid:.4f}s")
    print(f"Speedup: {t_brute / t_grid:.1f}x")


if __name__ == "__main__":
    main()