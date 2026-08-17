"""Tessellation and mesh export utilities."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .bspline import BSplineCurve
from .nurbs_curve import NURBSCurve
from .nurbs_surface import NURBSSurface


def tessellate_curve(
    curve: "BSplineCurve | NURBSCurve", samples: int = 100
) -> List[List[float]]:
    """Sample *curve* at *samples* evenly-spaced parameter values."""
    if samples < 2:
        raise ValueError("samples must be >= 2")
    u0, u1 = curve.parameter_range
    pts: List[List[float]] = []
    for i in range(samples):
        t = i / (samples - 1)
        u = u0 + t * (u1 - u0)
        pts.append(curve.evaluate(u))
    return pts


def tessellate_surface(
    surface: NURBSSurface,
    samples_u: int = 50,
    samples_v: int = 50,
) -> Tuple[List[List[float]], List[List[int]]]:
    """Tessellate *surface* into a triangle mesh.

    Returns
    -------
    vertices : list[list[float]]
        List of 3-D points.
    faces : list[list[int]]
        List of triangles (indices into *vertices*).
    """
    if samples_u < 2 or samples_v < 2:
        raise ValueError("samples must be >= 2")
    (u0, u1), (v0, v1) = surface.parameter_range
    vertices: List[List[float]] = []
    for i in range(samples_u):
        for j in range(samples_v):
            u = u0 + (i / (samples_u - 1)) * (u1 - u0)
            v = v0 + (j / (samples_v - 1)) * (v1 - v0)
            vertices.append(surface.evaluate(u, v))
    faces: List[List[int]] = []
    for i in range(samples_u - 1):
        for j in range(samples_v - 1):
            a = i * samples_v + j
            b = a + 1
            c = a + samples_v
            d = c + 1
            faces.append([a, c, b])
            faces.append([b, c, d])
    return vertices, faces


def export_obj(
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
) -> str:
    """Serialize a mesh to Wavefront OBJ text."""
    lines: List[str] = []
    for v in vertices:
        lines.append(f"v {' '.join(f'{x:.6f}' for x in v)}")
    for f in faces:
        # OBJ uses 1-based indices.
        lines.append("f " + " ".join(str(i + 1) for i in f))
    return "\n".join(lines) + "\n"


def export_ply_ascii(
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
) -> str:
    """Serialize a mesh to ASCII PLY text."""
    header = (
        "ply\n"
        "format ascii 1.0\n"
        f"element vertex {len(vertices)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        f"element face {len(faces)}\n"
        "property list uchar int vertex_index\n"
        "end_header\n"
    )
    body: List[str] = []
    for v in vertices:
        body.append(" ".join(f"{x:.6f}" for x in v))
    for f in faces:
        body.append(f"{len(f)} " + " ".join(str(i) for i in f))
    return header + "\n".join(body) + "\n"