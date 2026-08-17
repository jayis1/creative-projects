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
from .fitting import fit_bspline_curve
from .projection import project_point, arc_length, reparameterize_arc_length
from .presets import (
    make_circle,
    make_sphere_patch,
    make_torus,
    make_cylinder,
    make_cone,
)
from .svg_render import curve_to_svg, surface_to_svg_wireframe
from .serialization import (
    curve_to_dict,
    curve_from_dict,
    curve_to_json,
    curve_from_json,
    surface_to_dict,
    surface_from_dict,
    surface_to_json,
    surface_from_json,
)
from .exceptions import (
    NURBSError,
    InvalidKnotVector,
    InvalidControlPoint,
    InvalidWeight,
    SingularMatrix,
)

__version__ = "2.0.0"

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
    "fit_bspline_curve",
    "project_point",
    "arc_length",
    "reparameterize_arc_length",
    "make_circle",
    "make_sphere_patch",
    "make_torus",
    "make_cylinder",
    "make_cone",
    "curve_to_svg",
    "surface_to_svg_wireframe",
    "curve_to_dict",
    "curve_from_dict",
    "curve_to_json",
    "curve_from_json",
    "surface_to_dict",
    "surface_from_dict",
    "surface_to_json",
    "surface_from_json",
    "NURBSError",
    "InvalidKnotVector",
    "InvalidControlPoint",
    "InvalidWeight",
    "SingularMatrix",
    "__version__",
]