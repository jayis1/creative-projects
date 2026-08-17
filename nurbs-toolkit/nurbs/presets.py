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

    The octant is built as a surface of revolution: a quarter-circle
    profile in the XZ plane (from the north pole ``(0, 0, r)`` to the
    equator point ``(r, 0, 0)``) is revolved 90° around the Z axis.
    This is the standard NURBS construction and gives an exact sphere.

    The control net is 3×3 (biquadratic).  The profile direction (v)
    is a quarter-circle with weights ``(1, 1/√2, 1)``.  The revolution
    direction (u) is also a quarter-circle with weights
    ``(1, 1/√2, 1)``.  The pole edge (v=0) degenerates because all
    three profile-start control points are at ``(0, 0, r)`` (the
    distance from the Z axis is 0 at the pole).
    """
    w = math.sqrt(0.5)  # 1/√2
    r = radius
    rw = r * w           # r/√2
    # Profile (v-direction) quarter-circle from (0,0,r) to (r,0,0):
    #   control points: (0, 0, r), (rw, 0, rw), (r, 0, 0)
    #   weights: 1, w, 1
    #   (middle cp at tangent intersection, distance rw = r/cos(45°) * cos(45°)
    #    = r * cos(45°) ... actually rw = r * w = r/√2, which is r * cos(45°).
    #    The tangent intersection is at distance r/cos(45°) = r√2 from center,
    #    but the *control point* x-coordinate is rw = r/√2.  Wait no.
    #
    # For a quarter circle from (r,0) to (0,r) with center at origin:
    #   cp0 = (r, 0), cp1 = (r, r), cp2 = (0, r)  [tangent intersection at (r,r)]
    #   weights = 1, cos(45°)=w, 1
    # The evaluated point at t=0.5 is:
    #   (r*1*N0 + r*w*N1 + 0*1*N2, 0*1*N0 + r*w*N1 + r*1*N2) / (N0 + w*N1 + N2)
    #   = (r*(N0 + w*N1), r*(w*N1 + N2)) / (N0 + w*N1 + N2)
    #   At t=0.5: N0=N2=0.25, N1=0.5, so:
    #   = (r*(0.25 + 0.5w), r*(0.5w + 0.25)) / (0.25 + 0.5w + 0.25)
    #   = r*(0.25+0.5w) / (0.5+0.5w) = r*(0.25+0.354) / (0.5+0.354) = r*0.604/0.854 = r*0.707
    #   ✓ This gives (r/√2, r/√2) — correct!
    #
    # So the revolution control point coordinates should be:
    #   (1, 0), (1, 1), (0, 1) with weights 1, w, 1
    # NOT (1, 0), (w, w), (0, 1) — that was the bug!
    rx = [1.0, 1.0, 0.0]  # revolution x-component (tangent intersection cp)
    ry = [0.0, 1.0, 1.0]  # revolution y-component
    # Profile control points (v-direction):
    # Quarter circle from (0,0,r) to (r,0,0) in XZ plane.
    # cp0 = (0, 0, r) [pole], cp1 = (r, 0, r) [tangent intersection],
    # cp2 = (r, 0, 0) [equator], weights = 1, w, 1
    # The "distance from Z axis" for each profile cp:
    dist = [0.0, r, r]       # profile x (distance from Z axis)
    # The "height" for each profile cp:
    height = [r, r, 0.0]     # profile z (height)
    cps: List[List[List[float]]] = []
    for i in range(3):
        row: List[List[float]] = []
        for j in range(3):
            row.append([dist[j] * rx[i], dist[j] * ry[i], height[j]])
        cps.append(row)
    weights = [
        [1.0, w, 1.0],
        [w, w * w, w],
        [1.0, w, 1.0],
    ]
    ku = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
    kv = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
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