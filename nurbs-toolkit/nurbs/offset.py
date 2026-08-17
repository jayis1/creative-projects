"""Offset curves and curve manipulation.

Provides:
- Offset curves (parallel curves at a fixed distance)
- Curve reversal
- Curve concatenation
- Curve splitting at a parameter
"""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple

from .bspline import BSplineCurve
from .nurbs_curve import NURBSCurve

Curve = "BSplineCurve | NURBSCurve"


def offset_curve(
    curve,
    distance: float,
    samples: int = 100,
) -> List[List[float]]:
    """Compute an offset (parallel) curve at a fixed *distance*.

    For 2-D curves, the offset is along the normal direction.
    For 3-D curves, the offset is along the normal in the Frenet frame.

    This produces a *sampled* offset curve (list of points), not a
    B-spline. The samples can be re-fitted with ``fit_bspline_curve``
    if a smooth representation is needed.

    Parameters
    ----------
    curve : BSplineCurve or NURBSCurve
        The input curve (2-D or 3-D).
    distance : float
        Offset distance. Positive = left of direction of travel.
    samples : int
        Number of sample points.

    Returns
    -------
    list of points
        The offset curve as a list of 2-D or 3-D points.
    """
    u0, u1 = curve.parameter_range
    dim = len(curve.evaluate(u0))
    result: List[List[float]] = []
    for i in range(samples):
        t = i / (samples - 1) if samples > 1 else 0.0
        u = u0 + t * (u1 - u0)
        p = curve.evaluate(u)
        d1 = curve.derivative(u, 1)

        if dim == 2:
            speed = math.sqrt(d1[0] ** 2 + d1[1] ** 2)
            if speed < 1e-14:
                result.append(list(p))
                continue
            # Normal = rotate tangent 90° CCW.
            nx = -d1[1] / speed
            ny = d1[0] / speed
            result.append([p[0] + nx * distance, p[1] + ny * distance])
        elif dim == 3:
            # Use the principal normal in the osculating plane.
            d2 = curve.derivative(u, 2)
            # C' × C''
            cross = [
                d1[1] * d2[2] - d1[2] * d2[1],
                d1[2] * d2[0] - d1[0] * d2[2],
                d1[0] * d2[1] - d1[1] * d2[0],
            ]
            cross_mag = math.sqrt(sum(x * x for x in cross))
            speed = math.sqrt(sum(x * x for x in d1))
            if cross_mag < 1e-14 or speed < 1e-14:
                # Straight segment — use an arbitrary perpendicular.
                if speed > 1e-14:
                    t = [x / speed for x in d1]
                    # Pick a vector not parallel to t.
                    ref = [0.0, 0.0, 1.0] if abs(t[2]) < 0.9 else [1.0, 0.0, 0.0]
                    n = [
                        t[1] * ref[2] - t[2] * ref[1],
                        t[2] * ref[0] - t[0] * ref[2],
                        t[0] * ref[1] - t[1] * ref[0],
                    ]
                    n_mag = math.sqrt(sum(x * x for x in n))
                    if n_mag > 1e-14:
                        n = [x / n_mag for x in n]
                else:
                    n = [0.0, 0.0, 0.0]
            else:
                # Principal normal = binormal × tangent, normalized.
                binormal = [x / cross_mag for x in cross]
                tangent = [x / speed for x in d1]
                n = [
                    binormal[1] * tangent[2] - binormal[2] * tangent[1],
                    binormal[2] * tangent[0] - binormal[0] * tangent[2],
                    binormal[0] * tangent[1] - binormal[1] * tangent[0],
                ]
                n_mag = math.sqrt(sum(x * x for x in n))
                if n_mag > 1e-14:
                    n = [x / n_mag for x in n]
                else:
                    n = [0.0, 0.0, 0.0]
            result.append([p[j] + n[j] * distance for j in range(3)])
        else:
            result.append(list(p))
    return result


def reverse_curve(curve):
    """Return a new curve with reversed parameterization.

    The start becomes the end and vice versa. The knot vector is
    reversed (and re-parameterized to start at the original start).
    """
    p = curve.degree
    U = curve.knots
    cps = curve.control_points
    n = len(cps) - 1

    # Reverse control points.
    rev_cps = [list(cps[n - i]) for i in range(n + 1)]

    # Reverse knot vector: map u -> u_max - u + u_min.
    u_min = U[p]
    u_max = U[n + 1]
    rev_U = [u_min + u_max - x for x in reversed(U)]

    if isinstance(curve, NURBSCurve):
        rev_weights = list(reversed(curve.weights))
        return NURBSCurve(p, rev_U, rev_cps, rev_weights)
    else:
        return BSplineCurve(p, rev_U, rev_cps)


def split_curve(
    curve,
    u_split: float,
) -> Tuple["BSplineCurve | NURBSCurve", "BSplineCurve | NURBSCurve"]:
    """Split a B-spline/NURBS curve at parameter *u_split*.

    Uses knot insertion to raise the multiplicity of *u_split* to
    ``degree + 1``, then extracts the two halves.

    Returns
    -------
    (left, right) : tuple of curves
        Two curves whose union equals the original.
    """
    from .operations import knot_insert

    p = curve.degree
    U = curve.knots
    cps = curve.control_points
    n = len(cps) - 1
    dim = len(cps[0])

    # Determine current multiplicity of u_split.
    s = sum(1 for x in U if abs(x - u_split) < 1e-12)

    # Insert until multiplicity = p (not p+1, because we need to
    # evaluate at u_split which is the shared boundary).
    # Actually, to split we need multiplicity = p. Then the curve
    # passes through the point at u_split (C^{0} continuity).
    work = curve
    if s < p:
        work = knot_insert(work, u_split, p - s) if not isinstance(curve, NURBSCurve) else _knot_insert_nurbs(curve, u_split, p - s)

    U_new = work.knots
    cps_new = work.control_points
    weights_new = getattr(work, 'weights', None)

    # Find the index where u_split sits with multiplicity p.
    idx = 0
    for i in range(len(U_new)):
        if abs(U_new[i] - u_split) < 1e-12:
            idx = i
            break

    # Find span at u_split.
    from .bspline import find_span
    span = find_span(work.n, p, u_split, U_new)

    # The split point is control point at index span - p.
    split_cp_idx = span - p

    # Left curve: control points [0 .. split_cp_idx], knots [0 .. u_split]
    left_cps = [list(cps_new[i]) for i in range(split_cp_idx + 1)]
    left_U = [x for x in U_new if x <= u_split + 1e-12]
    # Ensure left knot vector has proper multiplicity at the end.
    while len(left_U) < len(left_cps) + p + 1:
        left_U.append(u_split)
    left_U = left_U[:len(left_cps) + p + 1]

    # Right curve: control points [split_cp_idx .. end], knots [u_split .. end]
    right_cps = [list(cps_new[i]) for i in range(split_cp_idx, len(cps_new))]
    right_U = [x for x in U_new if x >= u_split - 1e-12]
    # Ensure right knot vector has proper multiplicity at the start.
    while len(right_U) < len(right_cps) + p + 1:
        right_U.insert(0, u_split)
    right_U = right_U[:len(right_cps) + p + 1]

    if isinstance(curve, NURBSCurve):
        w = work.weights
        left_w = [w[i] for i in range(split_cp_idx + 1)]
        right_w = [w[i] for i in range(split_cp_idx, len(cps_new))]
        left = NURBSCurve(p, left_U, left_cps, left_w)
        right = NURBSCurve(p, right_U, right_cps, right_w)
    else:
        left = BSplineCurve(p, left_U, left_cps)
        right = BSplineCurve(p, right_U, right_cps)

    return left, right


def _knot_insert_nurbs(
    curve: NURBSCurve,
    u: float,
    times: int,
) -> NURBSCurve:
    """Insert a knot into a NURBS curve by working in homogeneous coords."""
    from .operations import knot_insert
    from .bspline import BSplineCurve

    p = curve.degree
    dim = curve.dim
    # Convert to homogeneous control points.
    h_cps = [
        [curve.control_points[i][d] * curve.weights[i] for d in range(dim)]
        + [curve.weights[i]]
        for i in range(len(curve.control_points))
    ]
    bs = BSplineCurve(p, curve.knots, h_cps)
    bs2 = knot_insert(bs, u, times)
    # Convert back.
    new_cps = []
    new_weights = []
    for hcp in bs2.control_points:
        w = hcp[-1]
        new_weights.append(w)
        new_cps.append([hcp[d] / w for d in range(dim)])
    return NURBSCurve(p, bs2.knots, new_cps, new_weights)


def concatenate_curves(
    curve1,
    curve2,
):
    """Concatenate two B-spline curves into one.

    The end of *curve1* must match the start of *curve2* (G0 continuity).
    Both curves must have the same degree and dimension.

    The resulting curve has C0 continuity at the junction.
    """
    if curve1.degree != curve2.degree:
        raise ValueError("Curves must have the same degree to concatenate")
    dim1 = len(curve1.control_points[0])
    dim2 = len(curve2.control_points[0])
    if dim1 != dim2:
        raise ValueError("Curves must have the same dimension")

    p = curve1.degree
    # Get parameter ranges.
    u0_1, u1_1 = curve1.parameter_range
    u0_2, u1_2 = curve2.parameter_range

    # Re-parameterize curve2 to start at u1_1.
    shift = u1_1 - u0_2
    c2_knots = [k + shift for k in curve2.knots]
    c2_cps = [list(cp) for cp in curve2.control_points]

    # Merge control points: drop the last control point of curve1
    # (shared with first of curve2).
    merged_cps = [list(cp) for cp in curve1.control_points[:-1]] + c2_cps
    n_merged = len(merged_cps) - 1

    # Build merged knot vector:
    # Take curve1's knot vector but remove the last copy of the junction
    # knot (so junction has multiplicity p, not p+1, for C0 continuity).
    # Then add curve2's interior + end knots (skip curve2's start knots
    # which are at the junction).
    merged_U = list(curve1.knots[:-1])  # drop one copy of junction knot
    merged_U += c2_knots[p + 1:]         # skip curve2's start (p+1) knots
    # Ensure correct length: n + p + 2.
    expected_len = n_merged + p + 2
    if len(merged_U) > expected_len:
        merged_U = merged_U[:expected_len]
    elif len(merged_U) < expected_len:
        while len(merged_U) < expected_len:
            merged_U.append(c2_knots[-1])

    if isinstance(curve1, NURBSCurve) and isinstance(curve2, NURBSCurve):
        w1 = list(curve1.weights)
        w2 = list(curve2.weights)
        merged_w = w1[:-1] + w2
        return NURBSCurve(p, merged_U, merged_cps, merged_w)
    else:
        return BSplineCurve(p, merged_U, merged_cps)