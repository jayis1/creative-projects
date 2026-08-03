"""Mesh subdivision: Loop subdivision scheme for triangle meshes.

Loop subdivision (Loop 1987) splits each triangle into 4 sub-triangles by
inserting vertices at edge midpoints, then smooths vertex positions using
a weighted average of neighbouring vertices.  Boundary edges use a special
1D subdivision rule.

This is a single-iteration implementation; call repeatedly for finer
subdivision.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from .mesh import Mesh


def loop_subdivide(mesh: Mesh) -> Mesh:
    """Perform one iteration of Loop subdivision on *mesh*.

    Returns a new :class:`Mesh` with ~4× the triangle count and smoother
    geometry.
    """
    if mesh.num_faces == 0:
        return Mesh()

    # Build edge -> adjacent faces map
    edge_faces: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for fi, (a, b, c) in enumerate(mesh.faces):
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            edge_faces[key].append(fi)

    # Build vertex -> adjacent vertices map (for odd vertex computation)
    vert_neighbors: Dict[int, Set[int]] = defaultdict(set)
    for (a, b, c) in mesh.faces:
        vert_neighbors[a].update({b, c})
        vert_neighbors[b].update({a, c})
        vert_neighbors[c].update({a, b})

    # Compute edge midpoints (odd vertices)
    # For interior edges: new_pos = 3/8 * (p0 + p1) + 1/8 * (p2 + p3)
    # where p2, p3 are the opposite vertices of the two faces sharing the edge
    edge_point: Dict[Tuple[int, int], Tuple[float, float, float]] = {}
    for (u, v), face_list in edge_faces.items():
        p0 = mesh.vertices[u]
        p1 = mesh.vertices[v]
        if len(face_list) == 2:
            # Find the two opposite vertices
            f0, f1 = face_list
            opp0 = _opposite_vertex(mesh.faces[f0], u, v)
            opp1 = _opposite_vertex(mesh.faces[f1], u, v)
            p2 = mesh.vertices[opp0]
            p3 = mesh.vertices[opp1]
            new_pos = (
                0.375 * (p0[0] + p1[0]) + 0.125 * (p2[0] + p3[0]),
                0.375 * (p0[1] + p1[1]) + 0.125 * (p2[1] + p3[1]),
                0.375 * (p0[2] + p1[2]) + 0.125 * (p2[2] + p3[2]),
            )
        else:
            # Boundary edge: simple midpoint
            new_pos = (
                0.5 * (p0[0] + p1[0]),
                0.5 * (p0[1] + p1[1]),
                0.5 * (p0[2] + p1[2]),
            )
        key = (u, v) if u < v else (v, u)
        edge_point[key] = new_pos

    # Compute updated even vertex positions
    # For interior vertex of valence n:
    #   beta = (5/8 - (3 + 2*cos(2*pi/n))/8)^2  (simplified: 3/(8n))
    #   new_pos = (1 - n*beta) * old + beta * sum(neighbors)
    # For boundary vertex:
    #   new_pos = 1/8 * (neighbor1 + neighbor2) + 3/4 * old
    boundary_edges: Set[Tuple[int, int]] = set()
    for key, face_list in edge_faces.items():
        if len(face_list) == 1:
            boundary_edges.add(key)

    boundary_verts: Set[int] = set()
    for (u, v) in boundary_edges:
        boundary_verts.add(u)
        boundary_verts.add(v)

    boundary_neighbors: Dict[int, List[int]] = defaultdict(list)
    for (u, v) in boundary_edges:
        boundary_neighbors[u].append(v)
        boundary_neighbors[v].append(u)

    new_even_pos: Dict[int, Tuple[float, float, float]] = {}
    for vi in range(len(mesh.vertices)):
        old = mesh.vertices[vi]
        if vi in boundary_verts:
            bn = boundary_neighbors[vi]
            if len(bn) >= 2:
                p_a = mesh.vertices[bn[0]]
                p_b = mesh.vertices[bn[1]]
                new_pos = (
                    0.75 * old[0] + 0.125 * (p_a[0] + p_b[0]),
                    0.75 * old[1] + 0.125 * (p_a[1] + p_b[1]),
                    0.75 * old[2] + 0.125 * (p_a[2] + p_b[2]),
                )
            else:
                new_pos = old
        else:
            neighbors = list(vert_neighbors[vi])
            n = len(neighbors)
            if n == 0:
                new_pos = old
            else:
                beta = 3.0 / (8.0 * n)
                sx = sum(mesh.vertices[nb][0] for nb in neighbors)
                sy = sum(mesh.vertices[nb][1] for nb in neighbors)
                sz = sum(mesh.vertices[nb][2] for nb in neighbors)
                new_pos = (
                    (1 - n * beta) * old[0] + beta * sx,
                    (1 - n * beta) * old[1] + beta * sy,
                    (1 - n * beta) * old[2] + beta * sz,
                )
        new_even_pos[vi] = new_pos

    # Build the new mesh
    # Old vertices get new positions; edge midpoints are appended
    new_vertices: List[Tuple[float, float, float]] = []
    old_to_new: Dict[int, int] = {}
    for vi in range(len(mesh.vertices)):
        old_to_new[vi] = len(new_vertices)
        new_vertices.append(new_even_pos[vi])

    # Assign indices to edge midpoints
    edge_to_idx: Dict[Tuple[int, int], int] = {}
    for key, pos in edge_point.items():
        edge_to_idx[key] = len(new_vertices)
        new_vertices.append(pos)

    # Build new faces: each triangle -> 4 sub-triangles
    new_faces: List[Tuple[int, int, int]] = []
    for (a, b, c) in mesh.faces:
        eab = edge_to_idx[(a, b) if a < b else (b, a)]
        ebc = edge_to_idx[(b, c) if b < c else (c, b)]
        eca = edge_to_idx[(c, a) if c < a else (a, c)]
        na, nb, nc = old_to_new[a], old_to_new[b], old_to_new[c]
        new_faces.append((na, eab, eca))
        new_faces.append((nb, ebc, eab))
        new_faces.append((nc, eca, ebc))
        new_faces.append((eab, ebc, eca))

    result = Mesh(vertices=new_vertices, faces=new_faces)
    result.compute_vertex_normals()
    return result


def _opposite_vertex(face: Tuple[int, int, int], u: int, v: int) -> int:
    """Return the vertex in *face* that is neither *u* nor *v*."""
    for vtx in face:
        if vtx != u and vtx != v:
            return vtx
    raise ValueError("no opposite vertex found — degenerate face")


def subdivide_n(mesh: Mesh, iterations: int = 1) -> Mesh:
    """Apply Loop subdivision *iterations* times."""
    result = mesh
    for _ in range(iterations):
        result = loop_subdivide(result)
    return result