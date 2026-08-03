"""Mesh file readers: import OBJ, OFF, PLY (ASCII), and STL (ASCII) files.

These are the inverse of :mod:`mcengine.export` — they parse common mesh
file formats back into :class:`Mesh` objects for inspection, transformation,
or re-export.

Only the subset of each format produced by this toolkit is guaranteed to
work, but common variants from other tools are also handled where feasible.
"""

from __future__ import annotations

import re
import struct
from typing import List, Tuple

from .mesh import Mesh


def read_obj(path: str) -> Mesh:
    """Read a Wavefront OBJ file into a :class:`Mesh`.

    Handles ``v``, ``f``, and optionally ``vn`` lines.  Faces with more than
    3 vertices are fan-triangulated.  ``v//vn`` and ``v/vt/vn`` formats are
    parsed.
    """
    vertices: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, int, int]] = []
    normals: List[Tuple[float, float, float]] = []

    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "v":
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif tag == "vn":
                normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif tag == "f":
                idx = []
                for p in parts[1:]:
                    v_idx = int(p.split("/")[0])
                    if v_idx < 0:
                        v_idx = len(vertices) + v_idx + 1
                    idx.append(v_idx - 1)  # OBJ is 1-indexed
                # Fan triangulate
                for i in range(1, len(idx) - 1):
                    faces.append((idx[0], idx[i], idx[i + 1]))

    mesh = Mesh(vertices=vertices, faces=faces)
    if normals:
        mesh.normals = normals[: len(vertices)]
    return mesh


def read_off(path: str) -> Mesh:
    """Read an OFF file into a :class:`Mesh`.

    Handles both standard OFF (with the ``OFF`` header) and the variant
    without a header line.
    """
    with open(path, "r") as fh:
        first = fh.readline().strip()
        if first == "OFF":
            header = fh.readline().strip()
        else:
            header = first
        nv, nf = (int(x) for x in header.split()[:2])
        vertices: List[Tuple[float, float, float]] = []
        for _ in range(nv):
            parts = fh.readline().split()
            vertices.append((float(parts[0]), float(parts[1]), float(parts[2])))
        faces: List[Tuple[int, int, int]] = []
        for _ in range(nf):
            parts = fh.readline().split()
            n_verts = int(parts[0])
            idx = [int(x) for x in parts[1 : 1 + n_verts]]
            for i in range(1, n_verts - 1):
                faces.append((idx[0], idx[i], idx[i + 1]))

    return Mesh(vertices=vertices, faces=faces)


def read_ply_ascii(path: str) -> Mesh:
    """Read an ASCII PLY file into a :class:`Mesh`.

    Parses vertex properties (x, y, z, and optionally nx, ny, nz) and
    triangular or polygonal faces (fan-triangulated).
    """
    with open(path, "r") as fh:
        # Parse header
        vertex_props = []
        nv = nf = 0
        in_header = True
        while in_header:
            line = fh.readline().strip()
            if line.startswith("element vertex"):
                nv = int(line.split()[-1])
            elif line.startswith("element face"):
                nf = int(line.split()[-1])
            elif line.startswith("property"):
                vertex_props.append(line.split()[-1])
            elif line == "end_header":
                in_header = False

        vertices: List[Tuple[float, float, float]] = []
        normals: List[Tuple[float, float, float]] = []
        for _ in range(nv):
            parts = fh.readline().split()
            v = (float(parts[0]), float(parts[1]), float(parts[2]))
            vertices.append(v)
            if "nx" in vertex_props:
                ni = vertex_props.index("nx")
                normals.append((float(parts[ni]), float(parts[ni + 1]), float(parts[ni + 2])))

        faces: List[Tuple[int, int, int]] = []
        for _ in range(nf):
            parts = fh.readline().split()
            n_verts = int(parts[0])
            idx = [int(x) for x in parts[1 : 1 + n_verts]]
            for i in range(1, n_verts - 1):
                faces.append((idx[0], idx[i], idx[i + 1]))

    mesh = Mesh(vertices=vertices, faces=faces)
    if normals:
        mesh.normals = normals
    return mesh


def read_stl_ascii(path: str) -> Mesh:
    """Read an ASCII STL file into a :class:`Mesh`.

    Parses ``facet normal`` / ``vertex`` blocks.  Per-face normals are
    discarded (vertex normals are recomputed from the geometry).
    """
    vertices: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, int, int]] = []
    current_face_verts: List[Tuple[float, float, float]] = []
    vert_index: dict = {}

    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("vertex"):
                parts = line.split()
                v = (float(parts[1]), float(parts[2]), float(parts[3]))
                if v not in vert_index:
                    vert_index[v] = len(vertices)
                    vertices.append(v)
                current_face_verts.append(v)
            elif line.startswith("endfacet"):
                if len(current_face_verts) >= 3:
                    idx = [vert_index[v] for v in current_face_verts[:3]]
                    faces.append((idx[0], idx[1], idx[2]))
                current_face_verts = []

    mesh = Mesh(vertices=vertices, faces=faces)
    mesh.compute_vertex_normals()
    return mesh


def read_stl_binary(path: str) -> Mesh:
    """Read a binary STL file into a :class:`Mesh`.

    Handles the standard 80-byte header + triangle count format.
    """
    vertices: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, int, int]] = []
    vert_index: dict = {}

    with open(path, "rb") as fh:
        fh.read(80)  # header
        num_faces = struct.unpack("<I", fh.read(4))[0]
        for _ in range(num_faces):
            fh.read(12)  # normal (3 floats)
            face_idx = []
            for _ in range(3):
                v = struct.unpack("<fff", fh.read(12))
                if v not in vert_index:
                    vert_index[v] = len(vertices)
                    vertices.append(v)
                face_idx.append(vert_index[v])
            fh.read(2)  # attribute byte count
            faces.append((face_idx[0], face_idx[1], face_idx[2]))

    mesh = Mesh(vertices=vertices, faces=faces)
    mesh.compute_vertex_normals()
    return mesh


def read_mesh(path: str) -> Mesh:
    """Auto-detect file format from extension and read the mesh."""
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    if ext == "obj":
        return read_obj(path)
    elif ext == "off":
        return read_off(path)
    elif ext == "ply":
        return read_ply_ascii(path)
    elif ext == "stl":
        # Try binary first, fall back to ASCII
        try:
            with open(path, "rb") as f:
                header = f.read(5)
            if header == b"solid":
                return read_stl_ascii(path)
            else:
                return read_stl_binary(path)
        except Exception:
            return read_stl_binary(path)
    else:
        raise ValueError(f"unsupported file extension: .{ext}")