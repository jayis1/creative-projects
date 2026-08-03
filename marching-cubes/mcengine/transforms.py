"""Mesh transformation operations: translate, scale, rotate, mirror, center.

All operations return a **new** :class:`Mesh` — the original is never mutated.
Transformations are applied to vertex positions only; faces and normals are
recomputed as needed.

Pure Python, no external dependencies.
"""

from __future__ import annotations

import math
from typing import Tuple

from .mesh import Mesh


def translate(mesh: Mesh, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> Mesh:
    """Return a new mesh translated by ``(dx, dy, dz)``."""
    new_verts = [(v[0] + dx, v[1] + dy, v[2] + dz) for v in mesh.vertices]
    result = Mesh(vertices=new_verts, faces=list(mesh.faces))
    result.compute_vertex_normals()
    return result


def scale(mesh: Mesh, sx: float = 1.0, sy: float = 1.0, sz: float = 1.0) -> Mesh:
    """Return a new mesh scaled by ``(sx, sy, sz)`` about the origin."""
    new_verts = [(v[0] * sx, v[1] * sy, v[2] * sz) for v in mesh.vertices]
    result = Mesh(vertices=new_verts, faces=list(mesh.faces))
    result.compute_vertex_normals()
    return result


def scale_uniform(mesh: Mesh, s: float) -> Mesh:
    """Return a new mesh uniformly scaled by *s* about the origin."""
    return scale(mesh, s, s, s)


def rotate_x(mesh: Mesh, angle_rad: float) -> Mesh:
    """Rotate mesh around the X-axis by *angle_rad* (radians)."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    new_verts = [
        (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c)
        for v in mesh.vertices
    ]
    result = Mesh(vertices=new_verts, faces=list(mesh.faces))
    result.compute_vertex_normals()
    return result


def rotate_y(mesh: Mesh, angle_rad: float) -> Mesh:
    """Rotate mesh around the Y-axis by *angle_rad* (radians)."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    new_verts = [
        (v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c)
        for v in mesh.vertices
    ]
    result = Mesh(vertices=new_verts, faces=list(mesh.faces))
    result.compute_vertex_normals()
    return result


def rotate_z(mesh: Mesh, angle_rad: float) -> Mesh:
    """Rotate mesh around the Z-axis by *angle_rad* (radians)."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    new_verts = [
        (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])
        for v in mesh.vertices
    ]
    result = Mesh(vertices=new_verts, faces=list(mesh.faces))
    result.compute_vertex_normals()
    return result


def mirror(mesh: Mesh, axis: str = "x") -> Mesh:
    """Mirror mesh across a coordinate plane.

    Parameters
    ----------
    axis : str
        ``"x"`` mirrors across the YZ plane (negate X),
        ``"y"`` mirrors across the XZ plane (negate Y),
        ``"z"`` mirrors across the XY plane (negate Z).
    """
    if axis not in ("x", "y", "z"):
        raise ValueError(f"axis must be 'x', 'y', or 'z', got {axis!r}")
    idx = {"x": 0, "y": 1, "z": 2}[axis]
    new_verts = []
    for v in mesh.vertices:
        nv = list(v)
        nv[idx] = -nv[idx]
        new_verts.append(tuple(nv))
    # Flip face winding to keep normals outward after mirroring
    new_faces = [(a, c, b) for (a, b, c) in mesh.faces]
    result = Mesh(vertices=new_verts, faces=new_faces)
    result.compute_vertex_normals()
    return result


def center(mesh: Mesh) -> Mesh:
    """Translate the mesh so its centroid is at the origin."""
    if not mesh.vertices:
        return Mesh()
    n = len(mesh.vertices)
    cx = sum(v[0] for v in mesh.vertices) / n
    cy = sum(v[1] for v in mesh.vertices) / n
    cz = sum(v[2] for v in mesh.vertices) / n
    return translate(mesh, -cx, -cy, -cz)


def normalize_size(mesh: Mesh, target_size: float = 2.0) -> Mesh:
    """Scale mesh so its largest bounding-box dimension equals *target_size*,
    then center it at the origin.
    """
    if not mesh.vertices:
        return Mesh()
    xs = [v[0] for v in mesh.vertices]
    ys = [v[1] for v in mesh.vertices]
    zs = [v[2] for v in mesh.vertices]
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs) - min(zs)
    max_dim = max(dx, dy, dz)
    if max_dim < 1e-12:
        return center(mesh)
    s = target_size / max_dim
    return center(scale_uniform(mesh, s))


def merge_meshes(meshes: list) -> Mesh:
    """Merge multiple meshes into one, concatenating vertices and offsetting
    face indices.
    """
    result = Mesh()
    offset = 0
    for m in meshes:
        for v in m.vertices:
            result.vertices.append(v)
        for (a, b, c) in m.faces:
            result.faces.append((a + offset, b + offset, c + offset))
        offset += len(m.vertices)
    result.compute_vertex_normals()
    return result