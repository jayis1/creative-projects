"""
Delaunay-Voronoi Toolkit
========================

A pure-Python computational geometry toolkit implementing:

* Bowyer-Watson Delaunay triangulation
* Dual Voronoi diagram construction (from triangles)
* Andrew's monotone-chain convex hull
* Lloyd's relaxation (Voronoi centroid smoothing)
* Ruppert's Delaunay refinement (quality meshing)
* Spatial queries (nearest neighbour, point location, k-NN)
* Polygon utilities (area, centroid, point-in-polygon, clipping, ear-clip)
* SVG, animated SVG, and PPM rendering
* JSON serialization

All algorithms work in exact rational arithmetic (via ``fractions``)
where geometric predicates demand it, giving robust results without
floating-point degeneracies for coplanar / cocircular inputs.
"""

from .geometry import Point, Triangle, Edge, Circle, orient2d, incircle
from .delaunay import DelaunayTriangulation
from .voronoi import VoronoiDiagram
from .convex_hull import convex_hull
from .lloyd import lloyd_relaxation, generate_poisson_seed
from .refine import ruppert_refine
from .spatial import nearest_neighbor, k_nearest_neighbors, locate_point
from .polygon import (
    polygon_area, polygon_centroid, point_in_polygon,
    sutherland_hodgman_clip, ear_clip_triangulate,
)
from .render import render_svg, render_ppm
from .animate import render_animated_svg, render_lloyd_animation
from .serialize import (
    save_json, load_json, triangulation_to_dict, triangulation_from_dict,
)

__version__ = "2.0.0"

__all__ = [
    "Point", "Triangle", "Edge", "Circle",
    "orient2d", "incircle",
    "DelaunayTriangulation", "VoronoiDiagram",
    "convex_hull", "lloyd_relaxation", "generate_poisson_seed",
    "ruppert_refine",
    "nearest_neighbor", "k_nearest_neighbors", "locate_point",
    "polygon_area", "polygon_centroid", "point_in_polygon",
    "sutherland_hodgman_clip", "ear_clip_triangulate",
    "render_svg", "render_ppm",
    "render_animated_svg", "render_lloyd_animation",
    "save_json", "load_json",
    "triangulation_to_dict", "triangulation_from_dict",
    "__version__",
]