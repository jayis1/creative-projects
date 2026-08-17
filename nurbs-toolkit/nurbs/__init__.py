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
* Curvature and torsion analysis
* Offset curves, curve splitting, reversal, concatenation
* Curve–curve intersection and surface trimming
* Surface fitting (least-squares tensor-product)
* Tessellation and export to OBJ/PLY/STL
* Configuration management (JSON/TOML/YAML)
* Structured logging

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
from .stl_export import export_stl, export_stl_ascii, export_stl_binary
from .fitting import fit_bspline_curve
from .surface_fitting import fit_bspline_surface
from .projection import project_point, arc_length, reparameterize_arc_length
from .curvature import (
    curvature,
    torsion,
    curvature_comb,
    find_inflections,
    curvature_plot_data,
    max_curvature,
)
from .offset import (
    offset_curve,
    reverse_curve,
    split_curve,
    concatenate_curves,
)
from .trimming import (
    intersect_curves,
    TrimmingLoop,
    trim_surface_points,
)
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
from .config import NURBSConfig, DEFAULT_CONFIG
from .logging_utils import get_logger, set_log_level, logger
from .exceptions import (
    NURBSError,
    InvalidKnotVector,
    InvalidControlPoint,
    InvalidWeight,
    SingularMatrix,
)

__version__ = "3.0.0"

__all__ = [
    # Core classes
    "BSplineBasis",
    "BSplineCurve",
    "NURBSCurve",
    "NURBSSurface",
    "BezierCurve",
    "bezier_to_bspline",
    # Basis functions
    "find_span",
    "basis_functions",
    "basis_functions_derivatives",
    # Operations
    "knot_insert",
    "knot_remove",
    "degree_elevate",
    "decompose_bezier_segments",
    # Knot vectors
    "generate_uniform_knot_vector",
    "generate_clamped_uniform_knot_vector",
    "validate_knot_vector",
    # Export
    "tessellate_curve",
    "tessellate_surface",
    "export_obj",
    "export_ply_ascii",
    "export_stl",
    "export_stl_ascii",
    "export_stl_binary",
    # Fitting
    "fit_bspline_curve",
    "fit_bspline_surface",
    # Projection & arc length
    "project_point",
    "arc_length",
    "reparameterize_arc_length",
    # Curvature
    "curvature",
    "torsion",
    "curvature_comb",
    "find_inflections",
    "curvature_plot_data",
    "max_curvature",
    # Offset & manipulation
    "offset_curve",
    "reverse_curve",
    "split_curve",
    "concatenate_curves",
    # Trimming & intersection
    "intersect_curves",
    "TrimmingLoop",
    "trim_surface_points",
    # Presets
    "make_circle",
    "make_sphere_patch",
    "make_torus",
    "make_cylinder",
    "make_cone",
    # Rendering
    "curve_to_svg",
    "surface_to_svg_wireframe",
    # Serialization
    "curve_to_dict",
    "curve_from_dict",
    "curve_to_json",
    "curve_from_json",
    "surface_to_dict",
    "surface_from_dict",
    "surface_to_json",
    "surface_from_json",
    # Config
    "NURBSConfig",
    "DEFAULT_CONFIG",
    # Logging
    "get_logger",
    "set_log_level",
    "logger",
    # Exceptions
    "NURBSError",
    "InvalidKnotVector",
    "InvalidControlPoint",
    "InvalidWeight",
    "SingularMatrix",
    # Version
    "__version__",
]