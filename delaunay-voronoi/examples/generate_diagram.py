#!/usr/bin/env python3
"""Generate a sample Delaunay/Voronoi diagram and save it as SVG."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from delaunay_voronoi import (
    DelaunayTriangulation, VoronoiDiagram, convex_hull,
    lloyd_relaxation, render_svg,
)
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.lloyd import generate_poisson_seed

def main():
    W, H = 800, 600
    box = (Point(0, 0), Point(W, H))

    # Generate random sites and run Lloyd relaxation for even spacing
    pts = generate_poisson_seed(40, box, seed=7)
    pts = lloyd_relaxation(pts, iterations=8, clip_box=box, seed=7)

    # Build triangulation and Voronoi diagram
    dt = DelaunayTriangulation.from_points(pts)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    hull = convex_hull(pts)

    svg = render_svg(
        width=W, height=H,
        delaunay_edges=dt.edges(),
        voronoi_edges=vd.edges,
        points=pts,
        hull=hull,
    )

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagram.svg")
    with open(out, "w") as f:
        f.write(svg)
    print(f"Saved SVG to {out}")
    print(f"  Points: {len(pts)}")
    print(f"  Triangles: {len(dt.triangles)}")
    print(f"  Voronoi edges: {len(vd.edges)}")
    print(f"  Hull vertices: {len(hull)}")


if __name__ == "__main__":
    main()