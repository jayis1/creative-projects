"""Smoke test: verify the toolkit runs end-to-end."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delaunay_voronoi import DelaunayTriangulation, VoronoiDiagram, convex_hull, render_svg
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.lloyd import generate_poisson_seed, lloyd_relaxation

def main():
    box = (Point(0, 0), Point(400, 300))
    pts = generate_poisson_seed(20, box, seed=42)
    print("Points:", len(pts))
    dt = DelaunayTriangulation.from_points(pts)
    print("Triangles:", len(dt.triangles))
    print("Edges:", len(dt.edges()))
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    print("Voronoi edges:", len(vd.edges))
    hull = convex_hull(pts)
    print("Hull:", len(hull))
    relaxed = lloyd_relaxation(pts, iterations=5, clip_box=box, seed=42)
    print("Relaxed:", len(relaxed))
    svg = render_svg(width=400, height=300, delaunay_edges=dt.edges(),
                     voronoi_edges=vd.edges, points=pts, hull=hull)
    assert svg.startswith("<svg")
    print("SVG length:", len(svg))
    print("OK")

if __name__ == "__main__":
    main()