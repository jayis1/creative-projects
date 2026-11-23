"""Greedy surface meshing for small voxel solids; dependency-free Python."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, order=True)
class Face:
    """A quad on the integer grid, identified by axis, plane, and rectangle."""
    axis: int
    sign: int
    plane: int
    u: int
    v: int
    width: int
    height: int
    material: int


class VoxelModel:
    """Sparse voxel grid with positive integer material IDs."""
    def __init__(self, voxels: Iterable[tuple[int, int, int] | tuple[int, int, int, int]]):
        self.voxels: dict[tuple[int, int, int], int] = {}
        for item in voxels:
            if len(item) not in (3, 4):
                raise ValueError("voxel must be (x,y,z) or (x,y,z,material)")
            xyz = (item[0], item[1], item[2])
            if any(type(n) is not int for n in xyz):
                raise ValueError("voxel coordinates must be integers")
            material = item[3] if len(item) == 4 else 1
            if type(material) is not int or material < 1:
                raise ValueError("material must be a positive integer")
            if xyz in self.voxels:
                raise ValueError(f"duplicate voxel at {xyz}")
            self.voxels[xyz] = material

    def faces(self) -> list[Face]:
        """Return exposed unit faces, in deterministic axis/coordinate order."""
        result = []
        for (x, y, z), material in sorted(self.voxels.items()):
            for axis, delta in enumerate(((1, 0, 0), (0, 1, 0), (0, 0, 1))):
                for sign in (-1, 1):
                    neighbor = (x + sign * delta[0], y + sign * delta[1], z + sign * delta[2])
                    if neighbor not in self.voxels:
                        coords = (x, y, z)
                        u, v = ((y, z) if axis == 0 else (x, z) if axis == 1 else (x, y))
                        plane = coords[axis] + (1 if sign > 0 else 0)
                        result.append(Face(axis, sign, plane, u, v, 1, 1, material))
        return result

    def greedy_faces(self) -> list[Face]:
        """Merge coplanar same-material unit faces into maximal rectangles."""
        unit = self.faces()
        groups: dict[tuple[int, int, int, int], set[tuple[int, int]]] = {}
        for f in unit:
            groups.setdefault((f.axis, f.sign, f.plane, f.material), set()).add((f.u, f.v))
        merged = []
        for (axis, sign, plane, material), cells in sorted(groups.items()):
            while cells:
                u0, v0 = min(cells, key=lambda p: (p[1], p[0]))
                width = 1
                while (u0 + width, v0) in cells:
                    width += 1
                height = 1
                while all((u, v0 + height) in cells for u in range(u0, u0 + width)):
                    height += 1
                for v in range(v0, v0 + height):
                    for u in range(u0, u0 + width):
                        cells.remove((u, v))
                merged.append(Face(axis, sign, plane, u0, v0, width, height, material))
        return sorted(merged)

    def to_stl(self, *, name: str = "voxel_model") -> str:
        """Export greedy quads as an ASCII STL triangle mesh."""
        if not name or any(char in name for char in "\\r\\n"):
            raise ValueError("STL name must be non-empty and contain no newlines")
        lines = [f"solid {name}"]
        for face in self.greedy_faces():
            corners = [(face.u, face.v), (face.u + face.width, face.v),
                       (face.u + face.width, face.v + face.height),
                       (face.u, face.v + face.height)]
            points = []
            for u, v in corners:
                if face.axis == 0:
                    point = (face.plane, u, v)
                elif face.axis == 1:
                    point = (u, face.plane, v)
                else:
                    point = (u, v, face.plane)
                points.append(point)
            orientation = -1 if face.axis == 1 else 1
            if face.sign * orientation < 0:
                points.reverse()
            normal = [0, 0, 0]
            normal[face.axis] = face.sign
            for triangle in ((points[0], points[1], points[2]),
                             (points[0], points[2], points[3])):
                lines.append(f"  facet normal {normal[0]} {normal[1]} {normal[2]}")
                lines.append("    outer loop")
                lines.extend(f"      vertex {x} {y} {z}" for x, y, z in triangle)
                lines.extend(("    endloop", "  endfacet"))
        lines.append(f"endsolid {name}")
        return "\n".join(lines) + "\n"

    def to_obj(self) -> str:
        """Export greedy quads as a compact, indexed Wavefront OBJ mesh."""
        vertices: list[tuple[int, int, int]] = []
        indices: dict[tuple[int, int, int], int] = {}
        lines = ["# voxel-mesher OBJ"]
        for face in self.greedy_faces():
            # Map each face's (u,v) coordinates back to XYZ, preserving winding.
            corners = [(face.u, face.v), (face.u + face.width, face.v),
                       (face.u + face.width, face.v + face.height),
                       (face.u, face.v + face.height)]
            points = []
            for u, v in corners:
                if face.axis == 0:
                    p = (face.plane, u, v)
                elif face.axis == 1:
                    p = (u, face.plane, v)
                else:
                    p = (u, v, face.plane)
                points.append(p)
            # The (u,v) basis for Y faces maps to -Y; compensate for that
            # handedness before applying the requested outward normal sign.
            orientation = -1 if face.axis == 1 else 1
            if face.sign * orientation < 0:
                points.reverse()
            face_indices = []
            for point in points:
                if point not in indices:
                    indices[point] = len(vertices) + 1
                    vertices.append(point)
                face_indices.append(indices[point])
            lines.append(f"usemtl material_{face.material}")
            lines.append("f " + " ".join(map(str, face_indices)))
        vertex_lines = [f"v {x} {y} {z}" for x, y, z in vertices]
        return "\n".join([lines[0], *vertex_lines, *lines[1:]]) + "\n"
