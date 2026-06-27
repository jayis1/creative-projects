"""
Delaunay-Voronoi Toolkit
========================

A pure-Python computational geometry toolkit implementing:

* Bowyer-Watson Delaunay triangulation
* Dual Voronoi diagram construction (from triangles)
* Andrew's monotone-chain convex hull
* Lloyd's relaxation (Voronoi centroid smoothing)
* SVG and PPM raster rendering

All algorithms work in exact rational arithmetic (via ``fractions``)
where geometric predicates demand it, giving robust results without
floating-point degeneracies for coplanar / cocircular inputs.
"""

from .geometry import Point, Triangle, Edge, Circle, orient2d, incircle
from .delaunay import DelaunayTriangulation
from .voronoi import VoronoiDiagram
from .convex_hull import convex_hull
from .lloyd import lloyd_relaxation
from .render import render_svg, render_ppm

__version__ = "1.0.0"

__all__ = [
    "Point",
    "Triangle",
    "Edge",
    "Circle",
    "orient2d",
    "incircle",
    "DelaunayTriangulation",
    "VoronoiDiagram",
    "convex_hull",
    "lloyd_relaxation",
    "render_svg",
    "render_ppm",
    "__version__",
]