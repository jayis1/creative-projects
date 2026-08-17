"""STL mesh export (ASCII and binary).

Adds STL output alongside the existing OBJ/PLY exporters.
"""

from __future__ import annotations

import struct
from typing import Sequence, List, Tuple

from .export import tessellate_surface


def export_stl_ascii(
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
) -> str:
    """Serialize a mesh to ASCII STL text."""
    lines: List[str] = ["solid nurbs_mesh"]
    for face in faces:
        if len(face) < 3:
            continue
        v0 = vertices[face[0]]
        v1 = vertices[face[1]]
        v2 = vertices[face[2]]
        # Compute face normal.
        e1 = [v1[i] - v0[i] for i in range(3)]
        e2 = [v2[i] - v0[i] for i in range(3)]
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        mag = (nx * nx + ny * ny + nz * nz) ** 0.5
        if mag > 1e-14:
            nx /= mag
            ny /= mag
            nz /= mag
        else:
            nx = ny = nz = 0.0
        lines.append(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}")
        lines.append("    outer loop")
        for idx in face[:3]:
            v = vertices[idx]
            lines.append(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid nurbs_mesh")
    return "\n".join(lines) + "\n"


def export_stl_binary(
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
) -> bytes:
    """Serialize a mesh to binary STL format."""
    # Header: 80 bytes + 4 byte face count.
    header = b"NURBS Toolkit Binary STL" + b"\0" * (80 - 24)
    num_faces = sum(1 for f in faces if len(f) >= 3)
    data = header + struct.pack("<I", num_faces)
    for face in faces:
        if len(face) < 3:
            continue
        v0 = vertices[face[0]]
        v1 = vertices[face[1]]
        v2 = vertices[face[2]]
        # Compute face normal.
        e1 = [v1[i] - v0[i] for i in range(3)]
        e2 = [v2[i] - v0[i] for i in range(3)]
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        mag = (nx * nx + ny * ny + nz * nz) ** 0.5
        if mag > 1e-14:
            nx /= mag
            ny /= mag
            nz /= mag
        else:
            nx = ny = nz = 0.0
        # Pack: normal (3f), v0 (3f), v1 (3f), v2 (3f), attribute (H)
        data += struct.pack(
            "<12fH",
            nx, ny, nz,
            v0[0], v0[1], v0[2],
            v1[0], v1[1], v1[2],
            v2[0], v2[1], v2[2],
            0,
        )
    return data


def export_stl(
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    binary: bool = False,
) -> "str | bytes":
    """Serialize a mesh to STL format.

    Parameters
    ----------
    binary : bool
        If True, return binary STL bytes; otherwise return ASCII text.
    """
    if binary:
        return export_stl_binary(vertices, faces)
    return export_stl_ascii(vertices, faces)