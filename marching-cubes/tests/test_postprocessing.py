"""Tests for mesh transforms, subdivision, simplification, and preview."""

import math
import pytest

from mcengine import (
    MarchingCubes, SphereSampler,
    translate, scale, scale_uniform, rotate_x, rotate_y, rotate_z,
    mirror, center, normalize_size, merge_meshes,
    simplify_mesh, loop_subdivide, subdivide_n,
    render_ascii_preview,
)
from mcengine.mesh import Mesh
from tests.conftest import assert_mesh_valid


@pytest.fixture
def sphere_mesh():
    mc = MarchingCubes(SphereSampler(1.0), resolution=(16, 16, 16))
    return mc.run()


class TestTranslate:
    def test_translation(self, sphere_mesh):
        moved = translate(sphere_mesh, 5, 0, 0)
        assert moved.num_vertices == sphere_mesh.num_vertices
        assert moved.num_faces == sphere_mesh.num_faces
        # Check first vertex is shifted
        assert moved.vertices[0][0] == pytest.approx(sphere_mesh.vertices[0][0] + 5)

    def test_zero_translation(self, sphere_mesh):
        result = translate(sphere_mesh, 0, 0, 0)
        assert result.vertices[0] == sphere_mesh.vertices[0]


class TestScale:
    def test_uniform_scale(self, sphere_mesh):
        scaled = scale_uniform(sphere_mesh, 2.0)
        assert scaled.vertices[0][0] == pytest.approx(sphere_mesh.vertices[0][0] * 2)

    def test_nonuniform_scale(self, sphere_mesh):
        scaled = scale(sphere_mesh, 2, 3, 4)
        v0 = sphere_mesh.vertices[0]
        assert scaled.vertices[0] == pytest.approx((v0[0] * 2, v0[1] * 3, v0[2] * 4))


class TestRotate:
    def test_rotate_x_90(self, sphere_mesh):
        rotated = rotate_x(sphere_mesh, math.pi / 2)
        assert rotated.num_vertices == sphere_mesh.num_vertices
        # Check that rotation happened: a point on +y should go to +z
        # (y*cos - z*sin, y*sin + z*cos) with angle=pi/2 => (-z, y)
        v0 = sphere_mesh.vertices[0]
        r0 = rotated.vertices[0]
        assert r0[1] == pytest.approx(-v0[2], abs=1e-6)
        assert r0[2] == pytest.approx(v0[1], abs=1e-6)

    def test_rotate_y_180(self, sphere_mesh):
        rotated = rotate_y(sphere_mesh, math.pi)
        v0 = sphere_mesh.vertices[0]
        r0 = rotated.vertices[0]
        assert r0[0] == pytest.approx(-v0[0], abs=1e-6)
        assert r0[2] == pytest.approx(-v0[2], abs=1e-6)

    def test_rotate_z_0(self, sphere_mesh):
        rotated = rotate_z(sphere_mesh, 0.0)
        assert rotated.vertices[0] == sphere_mesh.vertices[0]


class TestMirror:
    def test_mirror_x(self, sphere_mesh):
        mirrored = mirror(sphere_mesh, "x")
        v0 = sphere_mesh.vertices[0]
        m0 = mirrored.vertices[0]
        assert m0[0] == pytest.approx(-v0[0])
        assert m0[1] == v0[1]
        assert m0[2] == v0[2]

    def test_mirror_invalid(self, sphere_mesh):
        with pytest.raises(ValueError):
            mirror(sphere_mesh, "w")

    def test_mirror_flips_winding(self, sphere_mesh):
        mirrored = mirror(sphere_mesh, "x")
        # Check that face winding is reversed (a,b,c -> a,c,b)
        assert mirrored.faces[0] == (sphere_mesh.faces[0][0],
                                      sphere_mesh.faces[0][2],
                                      sphere_mesh.faces[0][1])


class TestCenter:
    def test_center_empty(self):
        mesh = Mesh()
        result = center(mesh)
        assert result.num_vertices == 0

    def test_centers_at_origin(self, sphere_mesh):
        centered = center(sphere_mesh)
        cx = sum(v[0] for v in centered.vertices) / len(centered.vertices)
        cy = sum(v[1] for v in centered.vertices) / len(centered.vertices)
        cz = sum(v[2] for v in centered.vertices) / len(centered.vertices)
        assert cx == pytest.approx(0.0, abs=1e-6)
        assert cy == pytest.approx(0.0, abs=1e-6)
        assert cz == pytest.approx(0.0, abs=1e-6)


class TestNormalizeSize:
    def test_normalize(self, sphere_mesh):
        result = normalize_size(sphere_mesh, target_size=4.0)
        xs = [v[0] for v in result.vertices]
        ys = [v[1] for v in result.vertices]
        zs = [v[2] for v in result.vertices]
        max_dim = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        assert max_dim == pytest.approx(4.0, abs=1e-3)

    def test_normalize_empty(self):
        result = normalize_size(Mesh(), 2.0)
        assert result.num_vertices == 0


class TestMergeMeshes:
    def test_merge_two(self, sphere_mesh):
        merged = merge_meshes([sphere_mesh, sphere_mesh])
        assert merged.num_vertices == 2 * sphere_mesh.num_vertices
        assert merged.num_faces == 2 * sphere_mesh.num_faces

    def test_merge_empty(self):
        result = merge_meshes([])
        assert result.num_vertices == 0


class TestSimplify:
    def test_simplify_reduces_faces(self, sphere_mesh):
        target = max(10, sphere_mesh.num_faces // 4)
        simplified = simplify_mesh(sphere_mesh, target_faces=target, max_error=1.0)
        assert simplified.num_faces < sphere_mesh.num_faces
        # Should get reasonably close to target (may not reach it if max_error prevents collapses)
        assert simplified.num_faces <= sphere_mesh.num_faces * 0.8

    def test_simplify_already_small(self, sphere_mesh):
        """If target > current, should return unchanged."""
        result = simplify_mesh(sphere_mesh, target_faces=999999)
        assert result.num_faces == sphere_mesh.num_faces


class TestSubdivision:
    def test_loop_subdivide_4x_faces(self, sphere_mesh):
        subdivided = loop_subdivide(sphere_mesh)
        # Each triangle -> 4, so 4x faces
        assert subdivided.num_faces == 4 * sphere_mesh.num_faces

    def test_subdivide_n(self, sphere_mesh):
        result = subdivide_n(sphere_mesh, 2)
        # 4^2 = 16x faces
        assert result.num_faces == 16 * sphere_mesh.num_faces

    def test_subdivide_empty(self):
        result = loop_subdivide(Mesh())
        assert result.num_faces == 0


class TestAsciiPreview:
    def test_renders_sphere(self, sphere_mesh):
        art = render_ascii_preview(sphere_mesh, width=30, height=12)
        assert isinstance(art, str)
        assert len(art) > 0
        # Should have multiple lines
        assert art.count("\n") >= 10

    def test_empty_mesh(self):
        art = render_ascii_preview(Mesh(), width=20, height=10)
        assert art == "(empty mesh)"

    def test_different_views(self, sphere_mesh):
        for view in ("xy", "xz", "yz"):
            art = render_ascii_preview(sphere_mesh, width=20, height=10, view=view)
            assert isinstance(art, str)

    def test_invalid_view(self, sphere_mesh):
        with pytest.raises(ValueError):
            render_ascii_preview(sphere_mesh, view="abc")