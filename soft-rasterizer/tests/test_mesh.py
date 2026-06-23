"""Tests for mesh operations and OBJ loading."""

import os
import tempfile
import pytest
from soft_rasterizer.math3d import Vec3, Vec2
from soft_rasterizer.mesh import Vertex, Triangle, Mesh, OBJLoader
from soft_rasterizer.primitives import make_cube, make_sphere, make_plane


class TestVertex:
    def test_default(self):
        v = Vertex(Vec3(1, 2, 3))
        assert v.pos == Vec3(1, 2, 3)
        assert v.normal == Vec3(0, 0, 1)
        assert v.uv == Vec2(0, 0)
        assert v.color == Vec3(1, 1, 1)

    def test_full(self):
        v = Vertex(Vec3(1, 0, 0), Vec3(1, 0, 0), Vec2(0.5, 0.5),
                   Vec3(0.8, 0.2, 0.2))
        assert v.normal == Vec3(1, 0, 0)
        assert v.color == Vec3(0.8, 0.2, 0.2)


class TestTriangle:
    def test_construction(self):
        t = Triangle(0, 1, 2)
        assert t.a == 0 and t.b == 1 and t.c == 2


class TestMesh:
    def test_empty(self):
        m = Mesh()
        assert m.vertex_count == 0
        assert m.triangle_count == 0

    def test_bounds(self):
        m = make_cube(2.0)
        minp, maxp = m.bounds()
        assert abs(minp.x + 1.0) < 1e-10
        assert abs(maxp.x - 1.0) < 1e-10

    def test_bounds_empty(self):
        m = Mesh()
        minp, maxp = m.bounds()
        assert minp == Vec3(0, 0, 0)
        assert maxp == Vec3(0, 0, 0)

    def test_center(self):
        m = make_cube(2.0)
        c = m.center()
        assert abs(c.x) < 1e-10
        assert abs(c.y) < 1e-10

    def test_translate(self):
        m = make_cube(2.0)
        m.translate(Vec3(5, 0, 0))
        c = m.center()
        assert abs(c.x - 5.0) < 1e-10

    def test_scale(self):
        m = make_cube(2.0)
        m.scale(2.0)
        minp, maxp = m.bounds()
        assert abs(maxp.x - 2.0) < 1e-10  # was 1.0, now 2.0

    def test_compute_face_normals(self):
        m = make_cube(2.0)
        # Cube should already have normals; recompute should not crash
        m.compute_face_normals()
        for v in m.vertices:
            assert v.normal.length() > 0.99

    def test_merge(self):
        m1 = make_cube(1.0)
        m2 = make_cube(1.0)
        v1, t1 = m1.vertex_count, m1.triangle_count
        m1.merge(m2)
        assert m1.vertex_count == v1 * 2
        assert m1.triangle_count == t1 * 2


class TestOBJLoader:
    def _write_obj(self, content):
        fd, path = tempfile.mkstemp(suffix=".obj")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path

    def test_load_basic(self):
        path = self._write_obj(
            "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        m = OBJLoader.load(path)
        assert m.vertex_count == 3
        assert m.triangle_count == 1
        os.unlink(path)

    def test_load_with_uvs(self):
        path = self._write_obj(
            "v 0 0 0\nv 1 0 0\nv 0 1 0\n"
            "vt 0 0\nvt 1 0\nvt 0 1\n"
            "f 1/1 2/2 3/3\n")
        m = OBJLoader.load(path)
        assert m.vertex_count == 3
        assert m.vertices[0].uv == Vec2(0, 0)
        os.unlink(path)

    def test_load_with_normals(self):
        path = self._write_obj(
            "v 0 0 0\nv 1 0 0\nv 0 1 0\n"
            "vn 0 0 1\nvn 0 0 1\nvn 0 0 1\n"
            "f 1//1 2//2 3//3\n")
        m = OBJLoader.load(path)
        assert m.vertices[0].normal == Vec3(0, 0, 1)
        os.unlink(path)

    def test_load_full(self):
        path = self._write_obj(
            "v 0 0 0\nv 1 0 0\nv 0 1 0\n"
            "vt 0 0\nvt 1 0\nvt 0 1\n"
            "vn 0 0 1\nvn 0 0 1\nvn 0 0 1\n"
            "f 1/1/1 2/2/2 3/3/3\n")
        m = OBJLoader.load(path)
        assert m.vertices[0].uv == Vec2(0, 0)
        assert m.vertices[0].normal == Vec3(0, 0, 1)
        os.unlink(path)

    def test_fan_triangulation(self):
        path = self._write_obj(
            "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n"
            "f 1 2 3 4\n")
        m = OBJLoader.load(path)
        # Quad → 2 triangles
        assert m.triangle_count == 2
        os.unlink(path)

    def test_comments_and_empty(self):
        path = self._write_obj(
            "# This is a comment\n\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        m = OBJLoader.load(path)
        assert m.vertex_count == 3
        os.unlink(path)

    def test_auto_normals(self):
        path = self._write_obj(
            "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        m = OBJLoader.load(path)
        # Should auto-compute normals since none were in the file
        for v in m.vertices:
            assert v.normal.length() > 0.99
        os.unlink(path)

    def test_save_and_reload(self):
        m1 = make_cube(1.0)
        fd, path = tempfile.mkstemp(suffix=".obj")
        os.close(fd)
        OBJLoader.save(m1, path)
        m2 = OBJLoader.load(path)
        assert m2.vertex_count == m1.vertex_count
        assert m2.triangle_count == m1.triangle_count
        os.unlink(path)