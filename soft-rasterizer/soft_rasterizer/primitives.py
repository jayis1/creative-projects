"""Built-in primitive mesh generators: cube, sphere, plane, cylinder, torus.

These provide ready-made geometry for testing and rendering without
needing external model files.
"""

from __future__ import annotations

import math

from .math3d import Vec3, Vec2
from .mesh import Mesh, Vertex, Triangle

__all__ = ["make_cube", "make_plane", "make_sphere", "make_cylinder",
           "make_torus", "make_tetrahedron", "make_octahedron"]


def make_cube(size: float = 1.0, name: str = "cube") -> Mesh:
    """Create a unit cube centered at the origin."""
    s = size * 0.5
    # 24 vertices (4 per face) for proper per-face normals
    face_data = [
        # +X face
        (Vec3(1, 0, 0), [Vec3(s, -s, -s), Vec3(s, s, -s),
                         Vec3(s, s, s), Vec3(s, -s, s)]),
        # -X face
        (Vec3(-1, 0, 0), [Vec3(-s, -s, s), Vec3(-s, s, s),
                          Vec3(-s, s, -s), Vec3(-s, -s, -s)]),
        # +Y face
        (Vec3(0, 1, 0), [Vec3(-s, s, -s), Vec3(-s, s, s),
                         Vec3(s, s, s), Vec3(s, s, -s)]),
        # -Y face
        (Vec3(0, -1, 0), [Vec3(-s, -s, s), Vec3(-s, -s, -s),
                          Vec3(s, -s, -s), Vec3(s, -s, s)]),
        # +Z face
        (Vec3(0, 0, 1), [Vec3(-s, -s, s), Vec3(s, -s, s),
                         Vec3(s, s, s), Vec3(-s, s, s)]),
        # -Z face
        (Vec3(0, 0, -1), [Vec3(s, -s, -s), Vec3(-s, -s, -s),
                          Vec3(-s, s, -s), Vec3(s, s, -s)]),
    ]

    uvs = [Vec2(0, 0), Vec2(1, 0), Vec2(1, 1), Vec2(0, 1)]

    vertices: list[Vertex] = []
    triangles: list[Triangle] = []
    for normal, positions in face_data:
        base = len(vertices)
        for i, pos in enumerate(positions):
            vertices.append(Vertex(pos, normal, uvs[i]))
        triangles.append(Triangle(base, base + 1, base + 2))
        triangles.append(Triangle(base, base + 2, base + 3))

    return Mesh(vertices, triangles, name=name)


def make_plane(size: float = 2.0, divisions: int = 1,
               name: str = "plane") -> Mesh:
    """Create a flat plane on the Y=0 axis."""
    if divisions < 1:
        raise ValueError("divisions must be >= 1")
    half = size * 0.5
    step = size / divisions
    vertices: list[Vertex] = []
    triangles: list[Triangle] = []

    for j in range(divisions + 1):
        for i in range(divisions + 1):
            x = -half + i * step
            z = -half + j * step
            u = i / divisions
            v = j / divisions
            vertices.append(Vertex(
                Vec3(x, 0, z),
                Vec3(0, 1, 0),
                Vec2(u, v),
            ))

    for j in range(divisions):
        for i in range(divisions):
            a = j * (divisions + 1) + i
            b = a + 1
            c = a + (divisions + 1)
            d = c + 1
            triangles.append(Triangle(a, c, b))
            triangles.append(Triangle(b, c, d))

    return Mesh(vertices, triangles, name=name)


def make_sphere(radius: float = 1.0, segments: int = 16,
                rings: int = 12, name: str = "sphere") -> Mesh:
    """Create a UV sphere.

    ``segments`` is the number of longitudinal slices, ``rings`` is the
    number of latitudinal bands.
    """
    if segments < 3 or rings < 2:
        raise ValueError("segments must be >= 3 and rings >= 2")

    vertices: list[Vertex] = []
    triangles: list[Triangle] = []

    for ring in range(rings + 1):
        phi = math.pi * ring / rings  # 0 to pi (top to bottom)
        for seg in range(segments):
            theta = 2 * math.pi * seg / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            pos = Vec3(x, y, z)
            normal = pos.normalized()
            u = seg / segments
            v = ring / rings
            vertices.append(Vertex(pos, normal, Vec2(u, v)))

    for ring in range(rings):
        for seg in range(segments):
            a = ring * segments + seg
            b = ring * segments + (seg + 1) % segments
            c = (ring + 1) * segments + seg
            d = (ring + 1) * segments + (seg + 1) % segments
            triangles.append(Triangle(a, b, d))
            triangles.append(Triangle(a, d, c))

    return Mesh(vertices, triangles, name=name)


def make_cylinder(radius: float = 1.0, height: float = 2.0,
                  segments: int = 16, name: str = "cylinder") -> Mesh:
    """Create a cylinder centered at the origin along the Y axis."""
    if segments < 3:
        raise ValueError("segments must be >= 3")
    h = height * 0.5
    vertices: list[Vertex] = []
    triangles: list[Triangle] = []

    # Side vertices (two rings)
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        x = radius * math.cos(theta)
        z = radius * math.sin(theta)
        u = i / segments
        # Top
        vertices.append(Vertex(
            Vec3(x, h, z),
            Vec3(math.cos(theta), 0, math.sin(theta)),
            Vec2(u, 0),
        ))
        # Bottom
        vertices.append(Vertex(
            Vec3(x, -h, z),
            Vec3(math.cos(theta), 0, math.sin(theta)),
            Vec2(u, 1),
        ))

    # Side triangles
    for i in range(segments):
        t0 = i * 2
        b0 = i * 2 + 1
        t1 = ((i + 1) % segments) * 2
        b1 = ((i + 1) % segments) * 2 + 1
        triangles.append(Triangle(t0, b0, b1))
        triangles.append(Triangle(t0, b1, t1))

    # Top cap
    top_center = len(vertices)
    vertices.append(Vertex(Vec3(0, h, 0), Vec3(0, 1, 0), Vec2(0.5, 0.5)))
    top_start = len(vertices)
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        vertices.append(Vertex(
            Vec3(radius * math.cos(theta), h, radius * math.sin(theta)),
            Vec3(0, 1, 0),
            Vec2(0.5 + 0.5 * math.cos(theta), 0.5 + 0.5 * math.sin(theta)),
        ))
    for i in range(segments):
        a = top_center
        b = top_start + i
        c = top_start + (i + 1) % segments
        triangles.append(Triangle(a, c, b))

    # Bottom cap
    bot_center = len(vertices)
    vertices.append(Vertex(Vec3(0, -h, 0), Vec3(0, -1, 0), Vec2(0.5, 0.5)))
    bot_start = len(vertices)
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        vertices.append(Vertex(
            Vec3(radius * math.cos(theta), -h, radius * math.sin(theta)),
            Vec3(0, -1, 0),
            Vec2(0.5 + 0.5 * math.cos(theta), 0.5 + 0.5 * math.sin(theta)),
        ))
    for i in range(segments):
        a = bot_center
        b = bot_start + i
        c = bot_start + (i + 1) % segments
        triangles.append(Triangle(a, b, c))

    return Mesh(vertices, triangles, name=name)


def make_torus(major_radius: float = 1.0, minor_radius: float = 0.3,
               major_segments: int = 24, minor_segments: int = 12,
               name: str = "torus") -> Mesh:
    """Create a torus (donut) centered at the origin."""
    if major_segments < 3 or minor_segments < 3:
        raise ValueError("segments must be >= 3")

    vertices: list[Vertex] = []
    triangles: list[Triangle] = []

    for i in range(major_segments):
        u = 2 * math.pi * i / major_segments
        for j in range(minor_segments):
            v = 2 * math.pi * j / minor_segments
            cx = major_radius * math.cos(u)
            cz = major_radius * math.sin(u)
            x = (major_radius + minor_radius * math.cos(v)) * math.cos(u)
            y = minor_radius * math.sin(v)
            z = (major_radius + minor_radius * math.cos(v)) * math.sin(u)
            pos = Vec3(x, y, z)
            # Normal points outward from the tube center
            normal = (Vec3(x - cx, y, z - cz)).normalized()
            vertices.append(Vertex(pos, normal,
                                   Vec2(i / major_segments, j / minor_segments)))

    for i in range(major_segments):
        for j in range(minor_segments):
            a = i * minor_segments + j
            b = ((i + 1) % major_segments) * minor_segments + j
            c = i * minor_segments + (j + 1) % minor_segments
            d = ((i + 1) % major_segments) * minor_segments + (j + 1) % minor_segments
            triangles.append(Triangle(a, c, b))
            triangles.append(Triangle(b, c, d))

    return Mesh(vertices, triangles, name=name)


def make_tetrahedron(size: float = 1.0, name: str = "tetrahedron") -> Mesh:
    """Create a regular tetrahedron."""
    s = size
    positions = [
        Vec3(1, 1, 1),
        Vec3(1, -1, -1),
        Vec3(-1, 1, -1),
        Vec3(-1, -1, 1),
    ]
    # Scale
    positions = [p * (s * 0.5) for p in positions]
    faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]

    vertices: list[Vertex] = []
    triangles: list[Triangle] = []
    for face in faces:
        a, b, c = face
        pa, pb, pc = positions[a], positions[b], positions[c]
        normal = (pb - pa).cross(pc - pa).normalized()
        base = len(vertices)
        vertices.append(Vertex(pa, normal, Vec2(0, 0)))
        vertices.append(Vertex(pb, normal, Vec2(1, 0)))
        vertices.append(Vertex(pc, normal, Vec2(0.5, 1)))
        triangles.append(Triangle(base, base + 1, base + 2))

    return Mesh(vertices, triangles, name=name)


def make_octahedron(size: float = 1.0, name: str = "octahedron") -> Mesh:
    """Create a regular octahedron."""
    s = size
    positions = [
        Vec3(s, 0, 0), Vec3(-s, 0, 0),
        Vec3(0, s, 0), Vec3(0, -s, 0),
        Vec3(0, 0, s), Vec3(0, 0, -s),
    ]
    faces = [
        (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
        (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5),
    ]

    vertices: list[Vertex] = []
    triangles: list[Triangle] = []
    for face in faces:
        a, b, c = face
        pa, pb, pc = positions[a], positions[b], positions[c]
        normal = (pb - pa).cross(pc - pa).normalized()
        base = len(vertices)
        vertices.append(Vertex(pa, normal, Vec2(0, 0)))
        vertices.append(Vertex(pb, normal, Vec2(1, 0)))
        vertices.append(Vertex(pc, normal, Vec2(0.5, 1)))
        triangles.append(Triangle(base, base + 1, base + 2))

    return Mesh(vertices, triangles, name=name)