"""Mesh data structures shared across the meshing algorithms."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator, List, Sequence, Tuple

from .vec3 import Vec3, cross, normalize


Vertex = Tuple[float, float, float]
"""A vertex is a plain ``(x, y, z)`` 3-tuple of floats."""

Face = Tuple[int, int, int]
"""A face is a triple of 0-based vertex indices, CCW when viewed from outside."""


def lerp(p0: Sequence[float], p1: Sequence[float], v0: float, v1: float,
         isolevel: float) -> Tuple[float, float, float]:
    """Linear interpolation of two corners to the isosurface.

    The interpolated position is ``p0 + t * (p1 - p0)`` where ``t`` places the
    crossing such that the interpolated field value equals *isolevel*.

    ``v0`` and ``v1`` are the field values at ``p0`` and ``p1`` respectively.
    """
    denom = v1 - v0
    if abs(denom) < 1e-12:
        t = 0.5
    else:
        t = (isolevel - v0) / denom
    # Clamp to [0,1] to guard against tiny overshoots from float noise.
    if t < 0.0: t = 0.0
    if t > 1.0: t = 1.0
    return (
        p0[0] + t * (p1[0] - p0[0]),
        p0[1] + t * (p1[1] - p0[1]),
        p0[2] + t * (p1[2] - p0[2]),
    )


def face_normal(a: Sequence[float], b: Sequence[float],
                c: Sequence[float]) -> Tuple[float, float, float]:
    """Return the unit normal of triangle ``abc`` (CCW = outward)."""
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = cross(u, v)
    return normalize(n)


@dataclass
class Mesh:
    """A triangle mesh: vertices, faces, and optional per-vertex normals."""

    vertices: List[Vertex] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)
    normals: List[Tuple[float, float, float]] = field(default_factory=list)

    # --- mutation helpers --------------------------------------------------
    def add_vertex(self, v: Vertex) -> int:
        self.vertices.append(v)
        return len(self.vertices) - 1

    def add_face(self, a: int, b: int, c: int) -> None:
        self.faces.append((a, b, c))

    # --- derived properties -----------------------------------------------
    @property
    def num_vertices(self) -> int: return len(self.vertices)
    @property
    def num_faces(self) -> int: return len(self.faces)

    def face_normals(self) -> List[Tuple[float, float, float]]:
        """Per-face unit normals (CCW outward)."""
        out: List[Tuple[float, float, float]] = []
        for (a, b, c) in self.faces:
            out.append(face_normal(self.vertices[a], self.vertices[b], self.vertices[c]))
        return out

    def compute_vertex_normals(self) -> List[Tuple[float, float, float]]:
        """Area-weighted per-vertex normals (zero for degenerate meshes)."""
        accum = [[0.0, 0.0, 0.0] for _ in range(len(self.vertices))]
        for (ia, ib, ic) in self.faces:
            a = self.vertices[ia]; b = self.vertices[ib]; c = self.vertices[ic]
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            nx = u[1] * v[2] - u[2] * v[1]
            ny = u[2] * v[0] - u[0] * v[2]
            nz = u[0] * v[1] - u[1] * v[0]
            for vi in (ia, ib, ic):
                accum[vi][0] += nx; accum[vi][1] += ny; accum[vi][2] += nz
        out: List[Tuple[float, float, float]] = []
        for n in accum:
            L = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
            if L < 1e-18:
                out.append((0.0, 0.0, 0.0))
            else:
                out.append((n[0] / L, n[1] / L, n[2] / L))
        self.normals = out
        return out

    # --- iteration ---------------------------------------------------------
    def triangles(self) -> Iterator[Tuple[Vertex, Vertex, Vertex]]:
        for (a, b, c) in self.faces:
            yield self.vertices[a], self.vertices[b], self.vertices[c]

    def __len__(self) -> int: return len(self.faces)