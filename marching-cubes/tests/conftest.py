"""Test fixtures and shared utilities."""

import sys
import os
import math
import tempfile
from typing import List, Tuple

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def make_sphere_data(n: int = 9, radius: float = 3.0) -> List[List[List[float]]]:
    """Create a 3D scalar field for a sphere, as nested lists."""
    cx = cy = cz = (n - 1) / 2.0
    data = []
    for i in range(n):
        plane = []
        for j in range(n):
            row = []
            for k in range(n):
                val = math.sqrt((i - cx) ** 2 + (j - cy) ** 2 + (k - cz) ** 2) - radius
                row.append(val)
            plane.append(row)
        data.append(plane)
    return data


def temp_file(suffix: str = ".obj") -> str:
    """Return a temporary file path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def cleanup(path: str) -> None:
    """Remove a file if it exists."""
    if os.path.exists(path):
        os.remove(path)


def assert_mesh_valid(mesh, min_verts: int = 1, min_faces: int = 1):
    """Assert that a mesh has valid geometry."""
    assert mesh.num_vertices >= min_verts, f"Expected >= {min_verts} vertices, got {mesh.num_vertices}"
    assert mesh.num_faces >= min_faces, f"Expected >= {min_faces} faces, got {mesh.num_faces}"
    # Check all face indices are valid
    nv = mesh.num_vertices
    for (a, b, c) in mesh.faces:
        assert 0 <= a < nv, f"Invalid vertex index {a}"
        assert 0 <= b < nv, f"Invalid vertex index {b}"
        assert 0 <= c < nv, f"Invalid vertex index {c}"
        assert a != b and b != c and a != c, f"Degenerate face: ({a}, {b}, {c})"