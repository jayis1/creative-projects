"""Tests for core mesh data structures and utilities."""

import math
import pytest

from mcengine.mesh import Mesh, lerp, face_normal


class TestLerp:
    def test_basic_midpoint(self):
        p0 = (0.0, 0.0, 0.0)
        p1 = (1.0, 0.0, 0.0)
        result = lerp(p0, p1, -1.0, 1.0, 0.0)
        assert result == pytest.approx((0.5, 0.0, 0.0))

    def test_at_p0(self):
        p0 = (0.0, 0.0, 0.0)
        p1 = (1.0, 0.0, 0.0)
        result = lerp(p0, p1, 0.0, 1.0, 0.0)
        assert result == pytest.approx((0.0, 0.0, 0.0))

    def test_at_p1(self):
        p0 = (0.0, 0.0, 0.0)
        p1 = (1.0, 0.0, 0.0)
        result = lerp(p0, p1, -1.0, 0.0, 0.0)
        assert result == pytest.approx((1.0, 0.0, 0.0))

    def test_denom_zero(self):
        """When v0 == v1, lerp should return midpoint."""
        p0 = (0.0, 0.0, 0.0)
        p1 = (2.0, 0.0, 0.0)
        result = lerp(p0, p1, 1.0, 1.0, 0.0)
        assert result == pytest.approx((1.0, 0.0, 0.0))

    def test_clamp_below(self):
        """t should be clamped to [0, 1]."""
        # v0=5, v1=1, isolevel=0: t = (0-5)/(1-5) = 1.25 -> clamp to 1.0 -> p1
        p0 = (0.0, 0.0, 0.0)
        p1 = (1.0, 0.0, 0.0)
        result = lerp(p0, p1, 5.0, 1.0, 0.0)
        assert result == pytest.approx((1.0, 0.0, 0.0))

    def test_clamp_above(self):
        # v0=0, v1=5, isolevel=0: t = (0-0)/(5-0) = 0.0 -> p0
        p0 = (0.0, 0.0, 0.0)
        p1 = (1.0, 0.0, 0.0)
        result = lerp(p0, p1, 0.0, 5.0, 0.0)
        assert result == pytest.approx((0.0, 0.0, 0.0))

    def test_3d(self):
        p0 = (0.0, 0.0, 0.0)
        p1 = (2.0, 4.0, 6.0)
        result = lerp(p0, p1, -1.0, 1.0, 0.0)
        assert result == pytest.approx((1.0, 2.0, 3.0))


class TestFaceNormal:
    def test_z_normal(self):
        a = (0, 0, 0)
        b = (1, 0, 0)
        c = (0, 1, 0)
        n = face_normal(a, b, c)
        assert n == pytest.approx((0.0, 0.0, 1.0))

    def test_degenerate(self):
        """Degenerate triangle should return zero normal."""
        a = (0, 0, 0)
        b = (1, 0, 0)
        c = (2, 0, 0)  # collinear
        n = face_normal(a, b, c)
        assert n == (0.0, 0.0, 0.0)


class TestMesh:
    def test_empty_mesh(self):
        mesh = Mesh()
        assert mesh.num_vertices == 0
        assert mesh.num_faces == 0
        assert len(mesh) == 0

    def test_add_vertex(self):
        mesh = Mesh()
        idx = mesh.add_vertex((1.0, 2.0, 3.0))
        assert idx == 0
        assert mesh.num_vertices == 1
        assert mesh.vertices[0] == (1.0, 2.0, 3.0)

    def test_add_face(self):
        mesh = Mesh()
        mesh.add_vertex((0, 0, 0))
        mesh.add_vertex((1, 0, 0))
        mesh.add_vertex((0, 1, 0))
        mesh.add_face(0, 1, 2)
        assert mesh.num_faces == 1
        assert mesh.faces[0] == (0, 1, 2)

    def test_triangles_iterator(self):
        mesh = Mesh()
        mesh.vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        mesh.faces = [(0, 1, 2)]
        tris = list(mesh.triangles())
        assert len(tris) == 1
        assert tris[0][0] == (0, 0, 0)

    def test_compute_vertex_normals(self):
        mesh = Mesh()
        mesh.vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        mesh.faces = [(0, 1, 2)]
        normals = mesh.compute_vertex_normals()
        assert len(normals) == 3
        # All normals should point in +z
        for n in normals:
            assert n[2] > 0.9

    def test_face_normals(self):
        mesh = Mesh()
        mesh.vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        mesh.faces = [(0, 1, 2)]
        normals = mesh.face_normals()
        assert len(normals) == 1
        assert normals[0] == pytest.approx((0.0, 0.0, 1.0))