#!/usr/bin/env python3
"""Generate a quality mesh report and print it.

Demonstrates the mesh quality metrics module.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from delaunay_voronoi import DelaunayTriangulation, compute_mesh_report, ruppert_refine
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.lloyd import generate_poisson_seed
from delaunay_voronoi.convex_hull import convex_hull


def main():
    box = (Point(0, 0), Point(400, 400))
    pts = generate_poisson_seed(25, box, seed=10)

    # Before refinement
    print("=" * 60)
    print("  BEFORE REFINEMENT")
    print("=" * 60)
    dt = DelaunayTriangulation.from_points(pts)
    hull = convex_hull(pts)
    report = compute_mesh_report(dt, hull_vertices=len(hull))
    print(report.to_text())

    # After refinement
    print("\n\n")
    print("=" * 60)
    print("  AFTER RUPPERT REFINEMENT (min_angle=25°)")
    print("=" * 60)
    refined = ruppert_refine(pts, min_angle_deg=25.0, max_points=500)
    dt2 = DelaunayTriangulation.from_points(refined)
    hull2 = convex_hull(refined)
    report2 = compute_mesh_report(dt2, hull_vertices=len(hull2))
    print(report2.to_text())


if __name__ == "__main__":
    main()