"""Tests for mesh diagnostics."""

import pytest

from mcengine import (
    MarchingCubes, SphereSampler, TorusSampler,
    analyze_mesh, euler_characteristic, compute_bounding_box,
)
from mcengine.mesh import Mesh


@pytest.fixture
def sphere_mesh():
    mc = MarchingCubes(SphereSampler(1.0), resolution=(20, 20, 20))
    return mc.run()


class TestBoundingBox:
    def test_sphere_bounds(self, sphere_mesh):
        bmin, bmax = compute_bounding_box(sphere_mesh)
        # Sphere of radius 1, bounds (-1.5, 1.5) — surface near ±1
        assert bmin[0] > -1.2 and bmin[0] < -0.8
        assert bmax[0] < 1.2 and bmax[0] > 0.8

    def test_empty_mesh(self):
        mesh = Mesh()
        bmin, bmax = compute_bounding_box(mesh)
        assert bmin == (0.0, 0.0, 0.0)
        assert bmax == (0.0, 0.0, 0.0)


class TestEulerCharacteristic:
    def test_sphere_chi_2(self, sphere_mesh):
        chi = euler_characteristic(sphere_mesh)
        assert chi == 2

    def test_empty_mesh(self):
        mesh = Mesh()
        assert euler_characteristic(mesh) == 0


class TestAnalyzeMesh:
    def test_sphere_diagnostics(self, sphere_mesh):
        d = analyze_mesh(sphere_mesh)
        assert d.num_vertices > 0
        assert d.num_faces > 0
        assert d.is_watertight
        assert d.euler_characteristic == 2
        assert d.genus == 0
        assert d.surface_area > 0
        assert d.degenerate_faces == 0

    def test_torus_diagnostics(self):
        mc = MarchingCubes(
            TorusSampler(1.0, 0.35),
            bounds=((-1.5, -1.5, -1.0), (1.5, 1.5, 1.0)),
            resolution=(24, 24, 24),
        )
        mesh = mc.run()
        d = analyze_mesh(mesh)
        assert d.is_watertight
        assert d.euler_characteristic == 0
        assert d.genus == 1

    def test_summary_string(self, sphere_mesh):
        d = analyze_mesh(sphere_mesh)
        s = d.summary()
        assert "Vertices:" in s
        assert "Faces:" in s
        assert "Watertight:" in s
        assert "Euler characteristic:" in s

    def test_empty_mesh_diagnostics(self):
        mesh = Mesh()
        d = analyze_mesh(mesh)
        assert d.num_vertices == 0
        assert d.num_faces == 0
        assert d.is_watertight == False  # noqa: E712

    def test_genus_property_non_watertight(self):
        d = analyze_mesh(Mesh())
        assert d.genus == -1  # not meaningful for non-watertight