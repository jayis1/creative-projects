"""Curvature analysis for B-spline and NURBS curves.

Computes parametric and geometric curvature, torsion (3-D),
curvature combs, and inflection point detection.
"""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple, Optional

from .bspline import BSplineCurve
from .nurbs_curve import NURBSCurve

# Type alias: any curve object with evaluate/derivative methods.
Curve = "BSplineCurve | NURBSCurve"


def curvature(curve, u: float) -> float:
    """Compute the geometric curvature κ at parameter *u*.

    For a parametric curve C(u), the curvature is:

        κ = |C'(u) × C''(u)| / |C'(u)|³

    For 2-D curves, this simplifies to:

        κ = |x'y'' - y'x''| / (x'² + y'²)^{3/2}

    Returns 0.0 if the first derivative is zero (degenerate point).
    """
    d1 = curve.derivative(u, 1)
    d2 = curve.derivative(u, 2)
    dim = len(d1)

    if dim == 2:
        cross = d1[0] * d2[1] - d1[1] * d2[0]
        speed = math.sqrt(d1[0] ** 2 + d1[1] ** 2)
        if speed < 1e-14:
            return 0.0
        return abs(cross) / speed ** 3

    elif dim == 3:
        # |C' × C''| in 3-D.
        cross_x = d1[1] * d2[2] - d1[2] * d2[1]
        cross_y = d1[2] * d2[0] - d1[0] * d2[2]
        cross_z = d1[0] * d2[1] - d1[1] * d2[0]
        cross_mag = math.sqrt(cross_x ** 2 + cross_y ** 2 + cross_z ** 2)
        speed = math.sqrt(sum(x * x for x in d1))
        if speed < 1e-14:
            return 0.0
        return cross_mag / speed ** 3

    else:
        raise ValueError(f"Curvature not supported for {dim}-D curves")


def torsion(curve, u: float) -> float:
    """Compute the torsion τ at parameter *u* for a 3-D curve.

        τ = (C' × C'') · C''' / |C' × C''|²

    Returns 0.0 for 2-D curves (torsion is always zero in 2-D).
    """
    dim = len(curve.evaluate(u))
    if dim != 3:
        return 0.0
    d1 = curve.derivative(u, 1)
    d2 = curve.derivative(u, 2)
    d3 = curve.derivative(u, 3)
    # C' × C''
    cross_x = d1[1] * d2[2] - d1[2] * d2[1]
    cross_y = d1[2] * d2[0] - d1[0] * d2[2]
    cross_z = d1[0] * d2[1] - d1[1] * d2[0]
    cross_mag_sq = cross_x ** 2 + cross_y ** 2 + cross_z ** 2
    if cross_mag_sq < 1e-28:
        return 0.0
    # (C' × C'') · C'''
    triple = cross_x * d3[0] + cross_y * d3[1] + cross_z * d3[2]
    return triple / cross_mag_sq


def curvature_comb(
    curve,
    u: float,
    scale: float = 0.1,
) -> Tuple[List[float], List[float]]:
    """Compute a curvature comb tooth at parameter *u*.

    Returns ``(curve_point, comb_point)`` where ``comb_point`` is
    offset from the curve point by the normal direction scaled by
    the curvature.
    """
    p = curve.evaluate(u)
    kappa = curvature(curve, u)
    d1 = curve.derivative(u, 1)
    dim = len(p)
    if dim == 2:
        # Normal = rotate tangent by 90°.
        speed = math.sqrt(d1[0] ** 2 + d1[1] ** 2)
        if speed < 1e-14:
            return list(p), list(p)
        nx = -d1[1] / speed
        ny = d1[0] / speed
        comb = [p[0] + nx * kappa * scale, p[1] + ny * kappa * scale]
    elif dim == 3:
        # Normal in the osculating plane.
        speed = math.sqrt(sum(x * x for x in d1))
        if speed < 1e-14:
            return list(p), list(p)
        t = [x / speed for x in d1]
        # Normal = (T' - (T·T')T) / |T' - (T·T')T|, simplified:
        d2 = curve.derivative(u, 2)
        # C' × C''
        cross = [
            d1[1] * d2[2] - d1[2] * d2[1],
            d1[2] * d2[0] - d1[0] * d2[2],
            d1[0] * d2[1] - d1[1] * d2[0],
        ]
        cross_mag = math.sqrt(sum(x * x for x in cross))
        if cross_mag < 1e-14:
            return list(p), list(p)
        n = [x / cross_mag for x in cross]
        comb = [p[i] + n[i] * kappa * scale for i in range(3)]
    else:
        return list(p), list(p)
    return list(p), comb


def find_inflections(
    curve,
    samples: int = 500,
    tol: float = 1e-8,
) -> List[float]:
    """Find approximate inflection points (κ = 0) via sign-change detection.

    Returns a list of parameter values where curvature changes sign.
    """
    u0, u1 = curve.parameter_range
    prev_kappa: Optional[float] = None
    prev_u: Optional[float] = None
    inflections: List[float] = []
    for i in range(samples):
        t = i / (samples - 1)
        u = u0 + t * (u1 - u0)
        # Use signed curvature for 2-D, unsigned for 3-D.
        if len(curve.evaluate(u)) == 2:
            d1 = curve.derivative(u, 1)
            d2 = curve.derivative(u, 2)
            speed_sq = d1[0] ** 2 + d1[1] ** 2
            if speed_sq < 1e-28:
                continue
            kappa = (d1[0] * d2[1] - d1[1] * d2[0]) / speed_sq ** 1.5
        else:
            kappa = curvature(curve, u)  # unsigned, skip for 3-D
            prev_kappa = kappa
            prev_u = u
            continue
        if prev_kappa is not None and prev_u is not None:
            if prev_kappa * kappa < 0 and abs(prev_kappa) > tol and abs(kappa) > tol:
                # Linear interpolation for the root.
                alpha = prev_kappa / (prev_kappa - kappa)
                u_inf = prev_u + alpha * (u - prev_u)
                inflections.append(u_inf)
        prev_kappa = kappa
        prev_u = u
    return inflections


def curvature_plot_data(
    curve,
    samples: int = 200,
) -> Tuple[List[float], List[float]]:
    """Generate (u, κ) data for plotting curvature along a curve.

    Returns
    -------
    us : list of parameter values
    kappas : list of curvature values
    """
    u0, u1 = curve.parameter_range
    us: List[float] = []
    kappas: List[float] = []
    for i in range(samples):
        t = i / (samples - 1) if samples > 1 else 0.0
        u = u0 + t * (u1 - u0)
        us.append(u)
        kappas.append(curvature(curve, u))
    return us, kappas


def max_curvature(curve, samples: int = 500) -> Tuple[float, float]:
    """Find the maximum curvature on a curve.

    Returns
    -------
    (u_max, kappa_max) : tuple
        Parameter and value of maximum curvature.
    """
    u0, u1 = curve.parameter_range
    best_u = u0
    best_k = 0.0
    for i in range(samples):
        t = i / (samples - 1) if samples > 1 else 0.0
        u = u0 + t * (u1 - u0)
        k = curvature(curve, u)
        if k > best_k:
            best_k = k
            best_u = u
    return best_u, best_k