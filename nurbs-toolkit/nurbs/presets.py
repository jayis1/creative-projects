"""Presets: common NURBS shapes (circle, sphere patch, torus, cone, cylinder)."""

from __future__ import annotations

import math
from typing import List, Tuple

from .nurbs_curve import NURBSCurve
from .nurbs_surface import NURBSSurface


def make_circle(
    radius: float = 1.0,
    center: Tuple[float, float] = (0.0, 0.0),
    segments: int = 4,
) -> NURBSCurve:
    """Create an exact NURBS representation of a circle.

    Parameters
    ----------
    radius : float
    center : (x, y)
    segments : int
        Number of arcs.  ``segments=4`` gives a full circle from 4
        90-degree quarter-circle arcs.  Each arc spans ``360/segments``
        degrees and must be <= 180 degrees.

    The middle control point of each arc is placed at the intersection
    of the tangent lines at the arc endpoints — *not* on the circle —
    with weight ``cos(half-arc-angle)``.  This is the standard exact
    NURBS circle construction.
    """
    if segments < 3:
        raise ValueError("segments must be >= 3 for a closed circle")
    angle_per_seg = 2 * math.pi / segments
    if angle_per_seg > math.pi:
        raise ValueError("each segment arc must be <= 180 degrees")
    half = angle_per_seg / 2
    cos_half = math.cos(half)

    cps: List[List[float]] = []
    weights: List[float] = []
    for i in range(segments):
        a0 = i * angle_per_seg
        a1 = (i + 1) * angle_per_seg
        # Start point on the circle.
        cps.append([
            center[0] + radius * math.cos(a0),
            center[1] + radius * math.sin(a0),
            0.0,
        ])
        weights.append(1.0)
        # Middle control point: intersection of tangent lines.
        # Placed at distance R/cos(half) along the bisector direction.
        am = (a0 + a1) / 2
        scale = radius / cos_half
        cps.append([
            center[0] + scale * math.cos(am),
            center[1] + scale * math.sin(am),
            0.0,
        ])
        weights.append(cos_half)
    # Close: repeat the first point (at angle 0).
    cps.append([center[0] + radius, center[1] + 0.0, 0.0])
    weights.append(1.0)

    # Knot vector: clamped, with interior knots at segment boundaries.
    p = 2
    n = len(cps) - 1
    knots: List[float] = [0.0] * (p + 1)
    for i in range(1, segments):
        knots.extend([float(i)] * 2)
    knots.extend([float(segments)] * (p + 1))
    return NURBSCurve(p, knots, cps, weights)


def make_sphere_patch(
    radius: float = 1.0,
    u_segments: int = 4,
    v_segments: int = 4,
) -> NURBSSurface:
    """Create a NURBS sphere octant patch.

    Uses a 3×3 biquadratic rational control net with the standard
    1/√2 and 1/2 weights for an exact octant representation.
    """
    w = math.sqrt(0.5)  # 1/√2
    r = radius
    # Control net for the octant in the positive octant.
    cps = [
        [[0, 0, r], [r * w, 0, r * w], [r, 0, 0]],
        [[0, r * w, r * w], [r * w, r * w, r * w], [r, r * w, 0]],
        [[0, r, 0], [r * w, r, 0], [r, r, 0]],
    ]
    weights = [
        [1.0, w, 1.0],
        [w, w * w, w],
        [1.0, w, 1.0],
    ]
    ku = [0, 0, 0, 1, 1, 1]
    kv = [0, 0, 0, 1, 1, 1]
    return NURBSSurface(2, 2, ku, kv, cps, weights)


def make_torus(
    R: float = 2.0,
    r: float = 0.5,
    u_segments: int = 4,
    v_segments: int = 4,
) -> NURBSSurface:
    """Create a NURBS torus by revolving a minor circle around the Z axis.

    Parameters
    ----------
    R : float
        Major radius (distance from center to tube center).
    r : float
        Minor radius (tube radius).
    u_segments : int
        Number of arcs in the major (revolution) direction.
    v_segments : int
        Number of arcs in the minor (tube) direction.
    """
    # Build the minor circle in the XZ plane (offset by R in x).
    # Then revolve it around Z.
    angle_per_u = 2 * math.pi / u_segments
    half_u = angle_per_u / 2
    cos_half_u = math.cos(half_u)

    angle_per_v = 2 * math.pi / v_segments
    half_v = angle_per_v / 2
    cos_half_v = math.cos(half_v)

    # Minor circle control points (in XZ plane, centered at (R, 0, 0)).
    v_cps: List[List[float]] = []
    v_weights: List[float] = []
    for j in range(v_segments):
        a0 = j * angle_per_v
        a1 = (j + 1) * angle_per_v
        am = (a0 + a1) / 2
        # Start point.
        v_cps.append([R + r * math.cos(a0), 0.0, r * math.sin(a0)])
        v_weights.append(1.0)
        # Middle point (tangent intersection).
        scale = r / cos_half_v
        v_cps.append([R + scale * math.cos(am), 0.0, scale * math.sin(am)])
        v_weights.append(cos_half_v)
    # Close.
    v_cps.append([R + r, 0.0, 0.0])
    v_weights.append(1.0)

    n_v = len(v_cps)  # control points in v direction
    n_u = 2 * u_segments + 1  # control points in u direction

    # Revolve: for each u control point, rotate all v control points.
    cps_net: List[List[List[float]]] = []
    weights_net: List[List[float]] = []
    for i in range(n_u):
        if i % 2 == 0:
            # On a segment boundary.
            a = (i // 2) * angle_per_u
            w_u = 1.0
        else:
            # Middle of a segment.
            a = ((i - 1) // 2 + 0.5) * angle_per_u
            w_u = cos_half_u
        cos_a, sin_a = math.cos(a), math.sin(a)
        row: List[List[float]] = []
        wrow: List[float] = []
        for j in range(n_v):
            px, py, pz = v_cps[j]
            x = px * cos_a - py * sin_a
            y = px * sin_a + py * cos_a
            z = pz
            row.append([x, y, z])
            wrow.append(v_weights[j] * w_u)
        cps_net.append(row)
        weights_net.append(wrow)

    # Knot vectors.
    p = 2
    ku: List[float] = [0.0] * (p + 1)
    for i in range(1, u_segments):
        ku.extend([float(i)] * 2)
    ku.extend([float(u_segments)] * (p + 1))

    kv: List[float] = [0.0] * (p + 1)
    for j in range(1, v_segments):
        kv.extend([float(j)] * 2)
    kv.extend([float(v_segments)] * (p + 1))

    return NURBSSurface(p, p, ku, kv, cps_net, weights_net)


def make_cylinder(
    radius: float = 1.0,
    height: float = 2.0,
    segments: int = 4,
) -> NURBSSurface:
    """Create a NURBS cylinder (closed circle in u, linear in v).

    The u-direction is the circular cross-section; the v-direction is
    the linear extrusion from z=0 to z=height.
    """
    circle = make_circle(radius, (0, 0), segments)
    n_circ = len(circle.control_points)  # u-direction: n_circ points

    # Grid: n_circ rows (u/circle) × 2 columns (v/height).
    cps_net: List[List[List[float]]] = []
    weights_net: List[List[float]] = []
    for i in range(n_circ):
        cp = circle.control_points[i]
        w = circle.weights[i]
        cps_net.append([
            [cp[0], cp[1], 0.0],
            [cp[0], cp[1], height],
        ])
        weights_net.append([w, w])

    ku = list(circle.knots)  # u-direction: circle knots
    kv = [0.0, 0.0, float(height), float(height)]  # v-direction: linear
    return NURBSSurface(circle.degree, 1, ku, kv, cps_net, weights_net)


def make_cone(
    radius: float = 1.0,
    height: float = 2.0,
    segments: int = 4,
) -> NURBSSurface:
    """Create a NURBS cone (circle at base, apex at top).

    The u-direction is the circular base; the v-direction goes from
    the base circle to the apex point at z=height.
    """
    circle = make_circle(radius, (0, 0), segments)
    n_circ = len(circle.control_points)

    cps_net: List[List[List[float]]] = []
    weights_net: List[List[float]] = []
    for i in range(n_circ):
        cp = circle.control_points[i]
        w = circle.weights[i]
        cps_net.append([
            [cp[0], cp[1], 0.0],
            [0.0, 0.0, height],  # apex — all u control points collapse
        ])
        weights_net.append([w, w])

    ku = list(circle.knots)
    kv = [0.0, 0.0, float(height), float(height)]
    return NURBSSurface(circle.degree, 1, ku, kv, cps_net, weights_net)