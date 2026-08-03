"""Tests for the Marching Cubes algorithm."""

import pytest

from mcengine import MarchingCubes, SphereSampler, TorusSampler, analyze_mesh
from mcengine.tables import MC_TRIANGLE_TABLE, MC_EDGE_TABLE
from tests.conftest import assert_mesh_valid


class TestMarchingCubes:
    def test_sphere_basic(self):
        mc = MarchingCubes(SphereSampler(1.0), resolution=(16, 16, 16))
        mesh = mc.run()
        assert_mesh_valid(mesh, min_verts=10, min_faces=10)

    def test_sphere_euler_characteristic(self):
        """A sphere should have Euler characteristic 2 (genus 0)."""
        mc = MarchingCubes(SphereSampler(1.0), resolution=(24, 24, 24))
        mesh = mc.run()
        d = analyze_mesh(mesh)
        assert d.euler_characteristic == 2, f"Expected chi=2, got {d.euler_characteristic}"

    def test_sphere_watertight(self):
        """Marching Cubes with vertex sharing should produce watertight meshes."""
        mc = MarchingCubes(SphereSampler(1.0), resolution=(16, 16, 16))
        mesh = mc.run()
        d = analyze_mesh(mesh)
        assert d.is_watertight, "Sphere mesh should be watertight"

    def test_torus_euler_characteristic(self):
        """A torus should have Euler characteristic 0 (genus 1)."""
        mc = MarchingCubes(
            TorusSampler(1.0, 0.35),
            bounds=((-1.5, -1.5, -1.0), (1.5, 1.5, 1.0)),
            resolution=(32, 32, 32),
        )
        mesh = mc.run()
        d = analyze_mesh(mesh)
        assert d.euler_characteristic == 0, f"Expected chi=0, got {d.euler_characteristic}"

    def test_torus_genus(self):
        mc = MarchingCubes(
            TorusSampler(1.0, 0.35),
            bounds=((-1.5, -1.5, -1.0), (1.5, 1.5, 1.0)),
            resolution=(32, 32, 32),
        )
        mesh = mc.run()
        d = analyze_mesh(mesh)
        assert d.genus == 1, f"Expected genus=1, got {d.genus}"

    def test_empty_region(self):
        """If the surface doesn't cross the grid, mesh should be empty."""
        # Sphere of radius 100, but bounds are small — no crossing
        mc = MarchingCubes(SphereSampler(100.0), resolution=(8, 8, 8))
        mesh = mc.run()
        assert mesh.num_faces == 0
        assert mesh.num_vertices == 0

    def test_resolution_too_low(self):
        with pytest.raises(ValueError):
            MarchingCubes(SphereSampler(1.0), resolution=(0, 8, 8))

    def test_callable_sampler(self):
        """Plain callable should work as a sampler."""
        def sphere_fn(x, y, z):
            return x * x + y * y + z * z - 1.0
        mc = MarchingCubes(sphere_fn, resolution=(12, 12, 12))
        mesh = mc.run()
        assert_mesh_valid(mesh)

    def test_isolevel_nonzero(self):
        """Non-zero isolevel should still produce valid mesh."""
        mc = MarchingCubes(SphereSampler(1.0), resolution=(12, 12, 12), isolevel=0.5)
        mesh = mc.run()
        assert_mesh_valid(mesh)

    def test_vertex_sharing(self):
        """Vertex sharing should produce fewer vertices than no-sharing."""
        mc = MarchingCubes(SphereSampler(1.0), resolution=(16, 16, 16))
        mesh = mc.run()
        # With sharing, V should be significantly less than F * 3
        assert mesh.num_vertices < mesh.num_faces * 3

    def test_resolution_affects_detail(self):
        """Higher resolution should produce more faces."""
        mc_low = MarchingCubes(SphereSampler(1.0), resolution=(8, 8, 8))
        mesh_low = mc_low.run()
        mc_high = MarchingCubes(SphereSampler(1.0), resolution=(24, 24, 24))
        mesh_high = mc_high.run()
        assert mesh_high.num_faces > mesh_low.num_faces


class TestTableConsistency:
    def test_triangle_table_256_entries(self):
        assert len(MC_TRIANGLE_TABLE) == 256

    def test_edge_table_256_entries(self):
        assert len(MC_EDGE_TABLE) == 256

    def test_case_0_no_crossing(self):
        """Case 0 (all corners outside) should have no edge crossings."""
        assert MC_EDGE_TABLE[0] == 0

    def test_case_255_complement(self):
        """Case 255 (all inside) should also have no edge crossings."""
        assert MC_EDGE_TABLE[255] == 0

    def test_symmetry(self):
        """Case k and 255-k should cross the same edges (complementary)."""
        for k in range(256):
            assert MC_EDGE_TABLE[k] == MC_EDGE_TABLE[255 - k], \
                f"Asymmetry at case {k} vs {255 - k}"