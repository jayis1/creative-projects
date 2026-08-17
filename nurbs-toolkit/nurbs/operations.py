"""Geometric operations on B-spline curves.

* Knot insertion (Boehm's algorithm)
* Knot removal
* Degree elevation
* Decomposition into Bezier segments
"""

from __future__ import annotations

from typing import Sequence, List, Tuple

from .bspline import BSplineCurve, find_span, basis_functions
from .knot_vector import generate_clamped_uniform_knot_vector


def knot_insert(
    curve: BSplineCurve, u: float, times: int = 1
) -> BSplineCurve:
    """Insert knot *u* into *curve* *times* times (Boehm's algorithm).

    Returns a new equivalent curve with an additional control point per
    insertion.
    """
    if times <= 0:
        return curve
    p = curve.degree
    U = list(curve.knots)
    P = [list(cp) for cp in curve.control_points]
    dim = curve.dim
    n = len(P) - 1

    for _ in range(times):
        k = find_span(n, p, u, U)
        # Number of existing occurrences of u in U.
        s = sum(1 for x in U if abs(x - u) < 1e-12)
        if p + s - 1 >= len(P):  # at max multiplicity
            break

        new_U = U[: k + 1] + [u] + U[k + 1:]
        new_P: List[List[float]] = [[0.0] * dim for _ in range(len(P) + 1)]
        for i in range(len(P) + 1):
            if i <= k - p:
                new_P[i] = list(P[i])
            elif k - p + 1 <= i <= k - s:
                alpha = (u - U[i]) / (U[i + p] - U[i])
                new_P[i] = [
                    alpha * P[i][d] + (1 - alpha) * P[i - 1][d]
                    for d in range(dim)
                ]
            else:
                new_P[i] = list(P[i - 1])
        U = new_U
        P = new_P
        n = len(P) - 1

    return BSplineCurve(p, U, P)


def knot_remove(
    curve: BSplineCurve, u: float, times: int = 1, tol: float = 1e-10
) -> BSplineCurve:
    """Attempt to remove knot *u* *times* times while keeping the curve
    within *tol* of the original.

    Implements a simplified knot-removal: remove if the affected control
    points can be linearly interpolated within tolerance.
    """
    if times <= 0:
        return curve
    p = curve.degree
    U = list(curve.knots)
    P = [list(cp) for cp in curve.control_points]
    dim = curve.dim

    for _ in range(times):
        # Locate the knot span.
        idx = None
        for i in range(len(U) - 1):
            if abs(U[i] - u) < 1e-12:
                idx = i
                break
        if idx is None:
            break
        # Find multiplicity.
        s = 0
        i = idx
        while i < len(U) and abs(U[i] - u) < 1e-12:
            s += 1
            i += 1
        if s <= 0:
            break
        # First and last index of the affected region.
        r = idx + s - 1  # last occurrence index
        first = r - p
        last = r - s

        # Check if removal is within tolerance.
        removable = True
        for i in range(first, last + 1):
            if i < 0 or i + 1 >= len(P):
                removable = False
                break
            # Predicted control point if knot removed.
            alpha = (u - U[i]) / (U[i + p + 1] - U[i])
            pred = [
                alpha * P[i][d] + (1 - alpha) * P[i + 1][d]
                for d in range(dim)
            ]
            # Original — simplified: compare with mid.
            actual = P[i] if i < len(P) else P[i + 1]
            if any(abs(pred[d] - actual[d]) > tol for d in range(dim)):
                removable = False
                break
        if not removable:
            break

        # Remove one knot occurrence and one control point.
        new_U = U[: idx] + U[idx + 1:]
        new_P = P[: first] + P[first + 1:]
        U = new_U
        P = new_P

    return BSplineCurve(p, U, P)


def degree_elevate(curve: BSplineCurve, t: int = 1) -> BSplineCurve:
    """Elevate the degree of *curve* by *t*.

    Uses the knot-insertion–based approach: for each interior knot,
    insert it ``t`` times then recompute control points.
    """
    if t <= 0:
        return curve
    p = curve.degree
    U = list(curve.knots)
    P = [list(cp) for cp in curve.control_points]
    dim = curve.dim
    n = len(P) - 1

    # Insert each interior knot p times to split into Bezier segments.
    # Then elevate each segment, then remove the knots.
    # Simpler full-elevation approach via formula.
    new_p = p + t
    # Collect distinct interior knots.
    interior = []
    i = p + 1
    while i < len(U) - p - 1:
        u = U[i]
        mult = 0
        while i < len(U) - p - 1 and abs(U[i] - u) < 1e-12:
            mult += 1
            i += 1
        interior.append((u, mult))

    # New knot vector: each interior knot gains t multiplicity.
    new_U: List[float] = [0.0] * (p + 1) + [U[0]] * 0
    # Build from scratch.
    knots = []
    # End knot multiplicity p+1
    knots.extend([U[0]] * (new_p + 1))
    for u, mult in interior:
        knots.extend([u] * (mult + t))
    knots.extend([U[-1]] * (new_p + 1))
    n_new = len(knots) - new_p - 1 - 1  # highest cp index

    # Compute new control points using degree-elevation formula on each
    # Bezier segment.  First decompose into segments.
    bez_segments = decompose_bezier_segments(curve)
    elevated_segments: List[List[List[float]]] = []
    for seg in bez_segments:
        cps = seg
        for _ in range(t):
            n_seg = len(cps) - 1
            new_cps = [list(cps[0])]
            for i in range(1, n_seg + 1):
                ratio = i / (n_seg + 1)
                new_cps.append([
                    ratio * cps[i - 1][d] + (1 - ratio) * cps[i][d]
                    for d in range(dim)
                ])
            new_cps.append(list(cps[-1]))
            cps = new_cps
        elevated_segments.append(cps)

    # Merge segments back: adjacent segments share an endpoint.
    merged: List[List[float]] = []
    for i, seg in enumerate(elevated_segments):
        if i == 0:
            merged.extend(seg)
        else:
            merged.extend(seg[1:])

    # Now build the full knot vector from merged segments.
    # Each segment is a Bezier of degree new_p, so the combined knot
    # vector has interior knots at segment boundaries with multiplicity
    # new_p.
    num_seg = len(elevated_segments)
    final_U: List[float] = []
    final_U.extend([0.0] * (new_p + 1))
    for i in range(1, num_seg):
        final_U.extend([float(i)] * new_p)
    final_U.extend([float(num_seg)] * (new_p + 1))

    return BSplineCurve(new_p, final_U, merged)


def decompose_bezier_segments(curve: BSplineCurve) -> List[List[List[float]]]:
    """Decompose a B-spline curve into its constituent Bezier segments.

    Returns a list of control-point lists, one per Bezier segment.
    """
    p = curve.degree
    U = list(curve.knots)
    P = [list(cp) for cp in curve.control_points]
    dim = curve.dim

    # Insert each interior knot until it has multiplicity p.
    work = BSplineCurve(p, U, P)
    interior_knots: List[float] = []
    i = p + 1
    while i < len(work.knots) - p - 1:
        u = work.knots[i]
        # Count the FULL multiplicity of this knot value across the
        # entire knot vector (not just up to the loop bound), since
        # end knots with multiplicity p+1 should not be processed.
        full_mult = 0
        for x in work.knots:
            if abs(x - u) < 1e-12:
                full_mult += 1
        if full_mult >= p + 1:
            # This is an end knot (or already at max multiplicity); skip.
            # Advance past all occurrences within the loop bound.
            j = i
            while j < len(work.knots) - p - 1 and abs(work.knots[j] - u) < 1e-12:
                j += 1
            i = j
            continue

        mult = 0
        j = i
        while j < len(work.knots) - p - 1 and abs(work.knots[j] - u) < 1e-12:
            mult += 1
            j += 1
        if mult < p:
            work = knot_insert(work, u, p - mult)
        interior_knots.append(u)
        # Advance past ALL occurrences of this knot value in the
        # updated knot vector to avoid reprocessing.
        i = p + 1
        for idx in range(len(work.knots)):
            if abs(work.knots[idx] - u) < 1e-12:
                i = idx + 1
        # i is now past the last occurrence of u; but we need to find
        # the next distinct interior knot.  Reset i to just past all
        # occurrences of u.
        i_new = p + 1
        while i_new < len(work.knots) - p - 1 and abs(work.knots[i_new] - u) < 1e-12:
            i_new += 1
        i = i_new

    # Now extract segments: each segment has p+1 control points.
    segments: List[List[List[float]]] = []
    nb = len(interior_knots) + 1  # number of bezier segments
    for seg in range(nb):
        start = seg * p
        segments.append([list(cp) for cp in work.control_points[start: start + p + 1]])
    return segments