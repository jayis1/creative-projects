#!/usr/bin/env python3
"""Export a Delaunay triangulation to multiple formats: OBJ, STL, PNG, JSON.

Demonstrates the exporters module.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from delaunay_voronoi import (
    DelaunayTriangulation, save_obj, save_png,
)
from delaunay_voronoi.exporters import export_ascii_stl
from delaunay_voronoi.geometry import Point
from delaunay_voronoi.lloyd import generate_poisson_seed


def main():
    box = (Point(0, 0), Point(300, 300))
    pts = generate_poisson_seed(30, box, seed=15)
    dt = DelaunayTriangulation.from_points(pts)

    out_dir = os.path.dirname(os.path.abspath(__file__))

    # OBJ
    obj_path = os.path.join(out_dir, "mesh.obj")
    save_obj(dt, obj_path)
    print(f"OBJ saved to {obj_path} ({len(dt.triangles)} triangles)")

    # STL
    stl_path = os.path.join(out_dir, "mesh.stl")
    with open(stl_path, "w") as f:
        f.write(export_ascii_stl(dt))
    print(f"STL saved to {stl_path}")

    # PNG (Voronoi flat-shaded)
    png_path = os.path.join(out_dir, "voronoi.png")
    save_png(300, 300, pts, png_path)
    print(f"PNG saved to {png_path}")


if __name__ == "__main__":
    main()