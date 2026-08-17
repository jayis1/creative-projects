"""JSON serialization for curves and surfaces."""

from __future__ import annotations

import json
from typing import Any, Dict

from .bspline import BSplineCurve
from .nurbs_curve import NURBSCurve
from .nurbs_surface import NURBSSurface


def curve_to_dict(curve: "BSplineCurve | NURBSCurve") -> Dict[str, Any]:
    """Serialize a curve to a dictionary."""
    d: Dict[str, Any] = {
        "type": "nurbs" if isinstance(curve, NURBSCurve) else "bspline",
        "degree": curve.degree,
        "knots": curve.knots,
        "control_points": curve.control_points,
    }
    if isinstance(curve, NURBSCurve):
        d["weights"] = curve.weights
    return d


def curve_from_dict(d: Dict[str, Any]) -> "BSplineCurve | NURBSCurve":
    """Deserialize a curve from a dictionary."""
    t = d.get("type", "bspline")
    if t == "nurbs":
        return NURBSCurve(
            d["degree"],
            d["knots"],
            d["control_points"],
            d.get("weights"),
        )
    return BSplineCurve(d["degree"], d["knots"], d["control_points"])


def curve_to_json(curve: "BSplineCurve | NURBSCurve") -> str:
    return json.dumps(curve_to_dict(curve), indent=2)


def curve_from_json(s: str) -> "BSplineCurve | NURBSCurve":
    return curve_from_dict(json.loads(s))


def surface_to_dict(surface: NURBSSurface) -> Dict[str, Any]:
    return {
        "type": "nurbs_surface",
        "degree_u": surface.degree_u,
        "degree_v": surface.degree_v,
        "knots_u": surface.knots_u,
        "knots_v": surface.knots_v,
        "control_points": surface.control_points,
        "weights": surface.weights,
    }


def surface_from_dict(d: Dict[str, Any]) -> NURBSSurface:
    return NURBSSurface(
        d["degree_u"],
        d["degree_v"],
        d["knots_u"],
        d["knots_v"],
        d["control_points"],
        d.get("weights"),
    )


def surface_to_json(surface: NURBSSurface) -> str:
    return json.dumps(surface_to_dict(surface), indent=2)


def surface_from_json(s: str) -> NURBSSurface:
    return surface_from_dict(json.loads(s))