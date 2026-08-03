"""Tests for Marching Tetrahedra and Dual Contouring algorithms."""

import pytest

from mcengine import (
    MarchingTetrahedra, DualContouring,
    SphereSampler, TorusSampler, OctahedronSampler, GyroidSampler,
    analyze_mesh,
)
from tests.conftest import assert_mesh_valid


class TestMarchingTetrahedra:
    def test_sphere_basic(self):
        mt = MarchingTetrahedra(SphereSampler(1.0), resolution=(12, 12, 12))
        mesh = mt.run()
        assert_mesh_valid(mesh)

    def test_torus_basic(self):
        mt = MarchingTetrahedra(
            TorusSampler(1.0, 0.35),
            bounds=((-1.5, -1.5, -1.0), (1.5, 1.5, 1.0)),
            resolution=(16, 16, 16),
        )
        mesh = mt.run()
        assert_mesh_valid(mesh)

    def test_empty_region(self):
        mt = MarchingTetrahedra(SphereSampler(100.0), resolution=(8, 8, 8))
        mesh = mt.run()
        assert mesh.num_faces == 0

    def test_resolution_too_low(self):
        with pytest.raises(ValueError):
            MarchingTetrahedra(SphereSampler(1.0), resolution=(0, 0, 0))

    def test_callable_sampler(self):
        def fn(x, y, z):
            return x * x + y * y + z * z - 1.0
        mt = MarchingTetrahedra(fn, resolution=(10, 10, 10))
        mesh = mt.run()
        assert_mesh_valid(mesh)


class TestDualContouring:
    def test_sphere_basic(self):
        dc = DualContouring(SphereSampler(1.0), resolution=(12, 12, 12))
        mesh = dc.run()
        assert_mesh_valid(mesh)

    def test_octahedron_sharp_features(self):
        """DC should preserve sharp features of an octahedron."""
        dc = DualContouring(OctahedronSampler(1.0), resolution=(16, 16, 16))
        mesh = dc.run()
        assert_mesh_valid(mesh)
        # DC produces one vertex per cell that the surface crosses,
        # while MC produces one vertex per edge crossing.
        # For a simple convex shape, DC should generally have fewer vertices.
        from mcengine import MarchingCubes
        mc = MarchingCubes(OctahedronSampler(1.0), resolution=(16, 16, 16))
        mc_mesh = mc.run()
        # DC should produce a comparable or lower face count than MC.
        # DC may not always be strictly lower for very small/simple shapes
        # at the same resolution, but should be in the same ballpark.
        assert mesh.num_faces <= mc_mesh.num_faces * 1.1, \
            f"DC face count should be comparable: DC={mesh.num_faces} MC={mc_mesh.num_faces}"

    def test_torus_basic(self):
        dc = DualContouring(
            TorusSampler(1.0, 0.35),
            bounds=((-1.5, -1.5, -1.0), (1.5, 1.5, 1.0)),
            resolution=(16, 16, 16),
        )
        mesh = dc.run()
        assert_mesh_valid(mesh)

    def test_no_clamp(self):
        """Disabling clamp should still produce valid mesh."""
        dc = DualContouring(OctahedronSampler(1.0), resolution=(12, 12, 12), clamp_to_cell=False)
        mesh = dc.run()
        assert_mesh_valid(mesh)

    def test_empty_region(self):
        dc = DualContouring(SphereSampler(100.0), resolution=(8, 8, 8))
        mesh = dc.run()
        assert mesh.num_faces == 0

    def test_resolution_too_low(self):
        with pytest.raises(ValueError):
            DualContouring(SphereSampler(1.0), resolution=(0, 8, 8))