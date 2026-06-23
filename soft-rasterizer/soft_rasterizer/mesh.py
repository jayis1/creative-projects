"""Triangle meshes and OBJ file loading."""

from __future__ import annotations

from .math3d import Vec3, Vec2

__all__ = ["Vertex", "Triangle", "Mesh", "OBJLoader"]


class Vertex:
    """A vertex with position, normal, and texture coordinate."""

    __slots__ = ("pos", "normal", "uv", "color")

    def __init__(self, pos: Vec3, normal: Vec3 | None = None,
                 uv: Vec2 | None = None, color: Vec3 | None = None):
        self.pos = pos
        self.normal = normal if normal is not None else Vec3(0, 0, 1)
        self.uv = uv if uv is not None else Vec2(0, 0)
        self.color = color if color is not None else Vec3(1, 1, 1)

    def __repr__(self) -> str:
        return f"Vertex(pos={self.pos}, normal={self.normal}, uv={self.uv})"


class Triangle:
    """A triangle referencing three vertices by index into a Mesh's vertex list."""

    __slots__ = ("a", "b", "c")

    def __init__(self, a: int, b: int, c: int):
        self.a = int(a)
        self.b = int(b)
        self.c = int(c)

    def __repr__(self) -> str:
        return f"Triangle({self.a}, {self.b}, {self.c})"


class Mesh:
    """A triangle mesh: vertex list + triangle index list + optional texture."""

    __slots__ = ("vertices", "triangles", "texture", "name")

    def __init__(self, vertices: list[Vertex] | None = None,
                 triangles: list[Triangle] | None = None,
                 texture=None, name: str = "mesh"):
        self.vertices: list[Vertex] = list(vertices) if vertices else []
        self.triangles: list[Triangle] = list(triangles) if triangles else []
        self.texture = texture
        self.name = name

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    def compute_face_normals(self):
        """Compute per-vertex normals from face normals (flat shading)."""
        normals = [Vec3(0, 0, 0) for _ in self.vertices]
        for tri in self.triangles:
            va = self.vertices[tri.a].pos
            vb = self.vertices[tri.b].pos
            vc = self.vertices[tri.c].pos
            face_n = (vb - va).cross(vc - va).normalized()
            normals[tri.a] = normals[tri.a] + face_n
            normals[tri.b] = normals[tri.b] + face_n
            normals[tri.c] = normals[tri.c] + face_n
        for i in range(len(self.vertices)):
            n = normals[i]
            if n.length_squared() > 0:
                self.vertices[i].normal = n.normalized()

    def compute_smooth_normals(self):
        """Alias for :meth:`compute_face_normals` — averages face normals
        at each vertex for smooth (Gouraud) shading."""
        self.compute_face_normals()

    def bounds(self) -> tuple[Vec3, Vec3]:
        """Return (min_corner, max_corner) of the mesh's axis-aligned bounding box."""
        if not self.vertices:
            return (Vec3(0, 0, 0), Vec3(0, 0, 0))
        minp = Vec3(self.vertices[0].pos.x, self.vertices[0].pos.y, self.vertices[0].pos.z)
        maxp = Vec3(minp.x, minp.y, minp.z)
        for v in self.vertices[1:]:
            minp.x = min(minp.x, v.pos.x)
            minp.y = min(minp.y, v.pos.y)
            minp.z = min(minp.z, v.pos.z)
            maxp.x = max(maxp.x, v.pos.x)
            maxp.y = max(maxp.y, v.pos.y)
            maxp.z = max(maxp.z, v.pos.z)
        return (minp, maxp)

    def center(self) -> Vec3:
        """Return the centroid of the bounding box."""
        minp, maxp = self.bounds()
        return Vec3(
            (minp.x + maxp.x) * 0.5,
            (minp.y + maxp.y) * 0.5,
            (minp.z + maxp.z) * 0.5,
        )

    def translate(self, offset: Vec3):
        for v in self.vertices:
            v.pos = v.pos + offset

    def scale(self, factor: float):
        for v in self.vertices:
            v.pos = v.pos * factor


class OBJLoader:
    """Minimal Wavefront OBJ loader.

    Supports ``v`` (vertices), ``vt`` (texture coords), ``vn`` (normals),
    and ``f`` (faces) with formats ``v``, ``v/vt``, ``v//vn``, ``v/vt/vn``.
    Faces with more than 3 vertices are fan-triangulated.
    """

    @staticmethod
    def load(filepath: str) -> Mesh:
        """Load an OBJ file and return a :class:`Mesh`."""
        positions: list[Vec3] = []
        texcoords: list[Vec2] = []
        normals: list[Vec3] = []
        face_verts: list[tuple[int, int, int]] = []  # (pos_idx, uv_idx, norm_idx)

        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                tag = parts[0]

                if tag == "v":
                    positions.append(Vec3(
                        float(parts[1]), float(parts[2]), float(parts[3])))

                elif tag == "vt":
                    texcoords.append(Vec2(
                        float(parts[1]), float(parts[2])))

                elif tag == "vn":
                    normals.append(Vec3(
                        float(parts[1]), float(parts[2]), float(parts[3])))

                elif tag == "f":
                    face_indices = []
                    for token in parts[1:]:
                        comps = token.split("/")
                        vi = int(comps[0]) - 1
                        ti = int(comps[1]) - 1 if len(comps) > 1 and comps[1] else -1
                        ni = int(comps[2]) - 1 if len(comps) > 2 and comps[2] else -1
                        face_indices.append((vi, ti, ni))
                    # Fan triangulation
                    for i in range(1, len(face_indices) - 1):
                        face_verts.append(face_indices[0])
                        face_verts.append(face_indices[i])
                        face_verts.append(face_indices[i + 1])

        # Build vertex list — de-duplicate by (pos, uv, normal) combination
        vert_map: dict[tuple[int, int, int], int] = {}
        vertices: list[Vertex] = []
        triangles: list[Triangle] = []

        for vi, ti, ni in face_verts:
            key = (vi, ti, ni)
            if key not in vert_map:
                pos = positions[vi] if vi < len(positions) else Vec3(0, 0, 0)
                uv = texcoords[ti] if ti >= 0 and ti < len(texcoords) else Vec2(0, 0)
                normal = normals[ni] if ni >= 0 and ni < len(normals) else Vec3(0, 0, 1)
                vert_map[key] = len(vertices)
                vertices.append(Vertex(pos, normal, uv))
            idx = vert_map[key]
            triangles.append(Triangle(idx, -1, -1))  # placeholder, fix below

        # Rebuild triangles with correct indices
        final_triangles: list[Triangle] = []
        for i in range(0, len(triangles), 3):
            final_triangles.append(Triangle(
                triangles[i].a,
                triangles[i + 1].a,
                triangles[i + 2].a,
            ))

        mesh_name = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        mesh = Mesh(vertices, final_triangles, name=mesh_name)

        # If no normals were provided, compute them
        if not normals:
            mesh.compute_face_normals()

        return mesh

    @staticmethod
    def save(mesh: Mesh, filepath: str):
        """Write a mesh to OBJ format (v/vt/vn/f)."""
        with open(filepath, "w") as f:
            f.write(f"# Generated by soft-rasterizer\n")
            f.write(f"# {mesh.vertex_count} vertices, {mesh.triangle_count} triangles\n")
            for v in mesh.vertices:
                f.write(f"v {v.pos.x:.6f} {v.pos.y:.6f} {v.pos.z:.6f}\n")
            for v in mesh.vertices:
                f.write(f"vt {v.uv.x:.6f} {v.uv.y:.6f}\n")
            for v in mesh.vertices:
                f.write(f"vn {v.normal.x:.6f} {v.normal.y:.6f} {v.normal.z:.6f}\n")
            for tri in mesh.triangles:
                a, b, c = tri.a + 1, tri.b + 1, tri.c + 1
                f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")