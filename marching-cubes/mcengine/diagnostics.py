"""Mesh diagnostics: bounding box, Euler characteristic, watertightness, area."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from .mesh import Mesh


def compute_bounding_box(mesh: Mesh) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Return ((xmin,ymin,zmin),(xmax,ymax,zmax)).  Zero-size if empty."""
    if not mesh.vertices:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    xs = [v[0] for v in mesh.vertices]
    ys = [v[1] for v in mesh.vertices]
    zs = [v[2] for v in mesh.vertices]
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


def euler_characteristic(mesh: Mesh) -> int:
    """Compute the Euler characteristic χ = V - E + F.

    Uses the fact that for a manifold triangle mesh χ = 2 - 2g (closed orientable
    genus-g surface), so a sphere gives 2, a torus 0, etc.
    """
    V = mesh.num_vertices
    F = mesh.num_faces
    E = 0
    seen: Set[Tuple[int, int]] = set()
    for (a, b, c) in mesh.faces:
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            if key not in seen:
                seen.add(key)
                E += 1
    return V - E + F


@dataclass
class MeshDiagnostics:
    """Summary statistics about a mesh."""

    num_vertices: int = 0
    num_faces: int = 0
    num_edges: int = 0
    euler_characteristic: int = 0
    is_watertight: bool = False
    num_boundary_edges: int = 0
    num_non_manifold_edges: int = 0
    surface_area: float = 0.0
    bounding_box: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = (
        (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    min_edge_length: float = 0.0
    max_edge_length: float = 0.0
    degenerate_faces: int = 0

    @property
    def genus(self) -> int:
        """Estimated genus (only meaningful for watertight orientable meshes)."""
        if not self.is_watertight:
            return -1
        # χ = 2 - 2g  =>  g = (2 - χ) / 2
        chi = self.euler_characteristic
        if (2 - chi) % 2 != 0:
            return -1
        return (2 - chi) // 2

    def summary(self) -> str:
        lines = [
            f"Vertices:              {self.num_vertices}",
            f"Faces:                 {self.num_faces}",
            f"Edges:                 {self.num_edges}",
            f"Euler characteristic:  {self.euler_characteristic}",
            f"Watertight:            {self.is_watertight}",
            f"Boundary edges:        {self.num_boundary_edges}",
            f"Non-manifold edges:    {self.num_non_manifold_edges}",
            f"Degenerate faces:      {self.degenerate_faces}",
            f"Surface area:          {self.surface_area:.6f}",
            f"Min edge length:       {self.min_edge_length:.6f}",
            f"Max edge length:       {self.max_edge_length:.6f}",
            f"Bounding box min:      {self.bounding_box[0]}",
            f"Bounding box max:      {self.bounding_box[1]}",
        ]
        if self.is_watertight:
            lines.append(f"Estimated genus:       {self.genus}")
        return "\n".join(lines)


def analyze_mesh(mesh: Mesh) -> MeshDiagnostics:
    """Compute and return a :class:`MeshDiagnostics` for *mesh*."""
    d = MeshDiagnostics()
    d.num_vertices = mesh.num_vertices
    d.num_faces = mesh.num_faces

    # edges + manifold/watertight analysis
    edge_count: Dict[Tuple[int, int], int] = defaultdict(int)
    for (a, b, c) in mesh.faces:
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            edge_count[key] += 1
    d.num_edges = len(edge_count)
    boundary = 0
    non_manifold = 0
    for cnt in edge_count.values():
        if cnt == 1:
            boundary += 1
        elif cnt > 2:
            non_manifold += 1
    d.num_boundary_edges = boundary
    d.num_non_manifold_edges = non_manifold
    d.is_watertight = (boundary == 0 and non_manifold == 0 and mesh.num_faces > 0)
    d.euler_characteristic = d.num_vertices - d.num_edges + d.num_faces

    # surface area, degenerate faces, edge lengths
    area = 0.0
    min_e = math.inf
    max_e = 0.0
    degen = 0
    for (a, b, c) in mesh.faces:
        va = mesh.vertices[a]; vb = mesh.vertices[b]; vc = mesh.vertices[c]
        ux, uy, uz = vb[0] - va[0], vb[1] - va[1], vb[2] - va[2]
        vx, vy, vz = vc[0] - va[0], vc[1] - va[1], vc[2] - va[2]
        cx = uy * vz - uz * vy
        cy = uz * vx - ux * vz
        cz = ux * vy - uy * vx
        tri_area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
        if tri_area < 1e-14:
            degen += 1
        area += tri_area
        for p0, p1 in ((va, vb), (vb, vc), (vc, va)):
            el = math.sqrt((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2 + (p0[2] - p1[2]) ** 2)
            if el < min_e: min_e = el
            if el > max_e: max_e = el
    d.surface_area = area
    d.degenerate_faces = degen
    d.min_edge_length = 0.0 if min_e == math.inf else min_e
    d.max_edge_length = max_e
    d.bounding_box = compute_bounding_box(mesh)
    return d