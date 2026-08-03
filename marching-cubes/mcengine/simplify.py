"""Mesh simplification via edge collapse.

Reduces triangle count by iteratively collapsing the shortest edges whose
endpoints have similar normals.  Each collapse merges two vertices into
one, removing 2 triangles (for interior edges) and updating the remaining
faces.

This is a simple, topology-preserving simplifier — not as sophisticated as
quadric-error-metric simplification, but fast and effective for reducing
Marching Cubes output.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from .mesh import Mesh


def simplify_mesh(mesh: Mesh, target_faces: int = 0, max_error: float = 0.15) -> Mesh:
    """Simplify *mesh* by collapsing short edges with similar normals.

    Parameters
    ----------
    target_faces : int
        Stop when the mesh has at most this many faces (0 = use max_error only).
    max_error : float
        Maximum normal deviation (radians) allowed for a collapse.
    """
    if mesh.num_faces <= max(target_faces, 0):
        return mesh

    # Build vertex -> faces index
    vert_faces: Dict[int, List[int]] = defaultdict(list)
    for fi, (a, b, c) in enumerate(mesh.faces):
        vert_faces[a].append(fi)
        vert_faces[b].append(fi)
        vert_faces[c].append(fi)

    # Build edge list (sorted vertex pairs)
    edges: Set[Tuple[int, int]] = set()
    for (a, b, c) in mesh.faces:
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            edges.add(key)

    # Compute vertex normals
    vnormals = mesh.compute_vertex_normals() if not mesh.normals else mesh.normals

    # Build mutable structures
    vertices = list(mesh.vertices)
    faces = [list(f) for f in mesh.faces]
    alive = [True] * len(faces)
    vert_alive = [True] * len(vertices)

    # Iteratively collapse shortest valid edges
    while edges and (target_faces == 0 or sum(alive) > target_faces):
        # Find the shortest valid edge
        best_edge = None
        best_len = math.inf
        for (u, v) in edges:
            if not vert_alive[u] or not vert_alive[v]:
                continue
            dx = vertices[u][0] - vertices[v][0]
            dy = vertices[u][1] - vertices[v][1]
            dz = vertices[u][2] - vertices[v][2]
            el = math.sqrt(dx * dx + dy * dy + dz * dz)
            if el < best_len:
                # Check normal similarity
                nu = vnormals[u]; nv = vnormals[v]
                dot = max(-1.0, min(1.0, nu[0] * nv[0] + nu[1] * nv[1] + nu[2] * nv[2]))
                if math.acos(dot) > max_error:
                    continue
                best_len = el
                best_edge = (u, v)

        if best_edge is None:
            break

        u, v = best_edge
        # Collapse v into u: replace v with u in all faces, kill degenerate
        for fi in vert_faces[v]:
            if not alive[fi]:
                continue
            face = faces[fi]
            for j in range(3):
                if face[j] == v:
                    face[j] = u
            # Check for degenerate (two same vertices)
            if face[0] == face[1] or face[1] == face[2] or face[0] == face[2]:
                alive[fi] = False

        # Update vert_faces: move v's faces to u
        for fi in vert_faces[v]:
            if fi not in vert_faces[u]:
                vert_faces[u].append(fi)
        vert_faces[v] = []

        # Mark v as dead
        vert_alive[v] = False

        # Remove edges involving v
        new_edges = set()
        for (a, b) in edges:
            if a == v or b == v:
                continue
            new_edges.add((a, b))
        edges = new_edges

        # Re-add edges from u's still-alive faces
        for fi in vert_faces[u]:
            if not alive[fi]:
                continue
            face = faces[fi]
            for j in range(3):
                a, b = face[j], face[(j + 1) % 3]
                if a != b:
                    key = (a, b) if a < b else (b, a)
                    edges.add(key)

    # Build the simplified mesh
    # Compact vertices
    old_to_new: Dict[int, int] = {}
    new_verts: List[Tuple[float, float, float]] = []
    for i, v in enumerate(vertices):
        if vert_alive[i]:
            old_to_new[i] = len(new_verts)
            new_verts.append(v)

    new_faces: List[Tuple[int, int, int]] = []
    for fi in range(len(faces)):
        if not alive[fi]:
            continue
        a, b, c = faces[fi]
        na = old_to_new.get(a)
        nb = old_to_new.get(b)
        nc = old_to_new.get(c)
        if na is not None and nb is not None and nc is not None:
            if na != nb and nb != nc and na != nc:
                new_faces.append((na, nb, nc))

    result = Mesh(vertices=new_verts, faces=new_faces)
    result.compute_vertex_normals()
    return result