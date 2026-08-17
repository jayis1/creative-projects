"""NURBS & B-spline Computer-Aided Geometric Design Toolkit.

A pure-Python implementation of NURBS (Non-Uniform Rational B-Splines)
surfaces and curves, supporting:

* B-spline basis functions via the Cox–de Boor recursion
* Clamped/unclamped/open/uniform knot vectors
* Bezier curves (special case of B-splines) with de Casteljau
* NURBS curves and tensor-product surfaces
* Knot insertion (Boehm's algorithm) & knot removal
* Degree elevation
* Curve/surface evaluation, derivatives, and projection
* Tessellation and export to OBJ/PLY/STL

The toolkit is self-contained (Python standard library only) and exposes
both an importable API and an ``argparse`` based command-line interface.
"""

from .bspline import (
    BSplineBasis,
    BSplineCurve,
    find_span,
    basis_functions,
    basis_functions_derivatives,
)
from .nurbs_curve import NURBSCurve
from .nurbs_surface import NURBSSurface
from .bezier import BezierCurve, bezier_to_bspline
from .operations import (
    knot_insert,
    knot_remove,
    degree_elevate,
    decompose_bezier_segments,
)
from .knot_vector import (
    generate_uniform_knot_vector,
    generate_clamped_uniform_knot_vector,
    validate_knot_vector,
)
from .export import tessellate_curve, tessellate_surface, export_obj, export_ply_ascii

__version__ = "1.0.0"

__all__ = [
    "BSplineBasis",
    "BSplineCurve",
    "NURBSCurve",
    "NURBSSurface",
    "BezierCurve",
    "bezier_to_bspline",
    "find_span",
    "basis_functions",
    "basis_functions_derivatives",
    "knot_insert",
    "knot_remove",
    "degree_elevate",
    "decompose_bezier_segments",
    "generate_uniform_knot_vector",
    "generate_clamped_uniform_knot_vector",
    "validate_knot_vector",
    "tessellate_curve",
    "tessellate_surface",
    "export_obj",
    "export_ply_ascii",
    "__version__",
]