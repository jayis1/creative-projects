"""Tests for VolumeSampler, config, and batch rendering."""

import json
import math
import os
import pytest

from mcengine import VolumeSampler, MarchingCubes, analyze_mesh
from mcengine.config import (
    load_config, save_config, get_preset, list_presets, normalize_job,
    _make_sampler, _parse_bounds,
)
from mcengine.batch import render_job, render_preset
from tests.conftest import make_sphere_data, temp_file, cleanup, assert_mesh_valid


class TestVolumeSampler:
    def test_construction(self):
        data = make_sphere_data(5)
        vs = VolumeSampler(data, bounds=((0, 0, 0), (4, 4, 4)))
        assert vs.nx == 5
        assert vs.ny == 5
        assert vs.nz == 5

    def test_too_small(self):
        with pytest.raises(ValueError):
            VolumeSampler([[[1.0]]])

    def test_sample_at_grid_point(self):
        data = make_sphere_data(5, radius=2.0)
        vs = VolumeSampler(data, bounds=((0, 0, 0), (4, 4, 4)))
        # At grid point (0,0,0), value should match data
        val = vs.sample(0, 0, 0)
        assert val == pytest.approx(data[0][0][0])

    def test_sample_at_center(self):
        data = make_sphere_data(9, radius=3.0)
        vs = VolumeSampler(data, bounds=((0, 0, 0), (8, 8, 8)))
        # Center of grid is (4,4,4) in index space, value = -3.0
        val = vs.sample(4, 4, 4)
        assert val == pytest.approx(-3.0)

    def test_mesh_from_volume(self):
        data = make_sphere_data(9, radius=3.0)
        vs = VolumeSampler(data, bounds=((0, 0, 0), (8, 8, 8)))
        mc = MarchingCubes(vs, bounds=((0, 0, 0), (8, 8, 8)), resolution=(16, 16, 16))
        mesh = mc.run()
        assert_mesh_valid(mesh)
        d = analyze_mesh(mesh)
        assert d.is_watertight
        assert d.euler_characteristic == 2  # sphere

    def test_gradient(self):
        data = make_sphere_data(9, radius=3.0)
        vs = VolumeSampler(data, bounds=((0, 0, 0), (8, 8, 8)))
        g = vs.gradient(4, 4, 4)
        # At center of sphere, gradient should be near zero (center of sphere)
        assert abs(g[0]) < 1.0 and abs(g[1]) < 1.0 and abs(g[2]) < 1.0

    def test_boundary_interpolation(self):
        """Trilinear interpolation at the far boundary should work correctly."""
        data = make_sphere_data(5)
        vs = VolumeSampler(data, bounds=((0, 0, 0), (4, 4, 4)))
        # Sample at the far corner — should not crash
        val = vs.sample(4, 4, 4)
        assert isinstance(val, float)


class TestConfig:
    def test_normalize_job_defaults(self):
        job = normalize_job({})
        assert job["algorithm"] == "mc"
        assert job["sampler"] == "sphere"
        assert job["resolution"] == 32

    def test_normalize_job_invalid_algorithm(self):
        with pytest.raises(ValueError):
            normalize_job({"algorithm": "invalid"})

    def test_parse_bounds_2_values(self):
        bmin, bmax = _parse_bounds("-1.5,1.5")
        assert bmin == (-1.5, -1.5, -1.5)
        assert bmax == (1.5, 1.5, 1.5)

    def test_parse_bounds_6_values(self):
        bmin, bmax = _parse_bounds("0,0,0,4,4,4")
        assert bmin == (0, 0, 0)
        assert bmax == (4, 4, 4)

    def test_parse_bounds_invalid(self):
        with pytest.raises(ValueError):
            _parse_bounds("1,2,3")

    def test_make_sampler(self):
        s = _make_sampler("sphere", {"radius": 2.0})
        assert s.r2 == 4.0

    def test_make_sampler_unknown(self):
        with pytest.raises(ValueError):
            _make_sampler("nonexistent")

    def test_list_presets(self):
        presets = list_presets()
        assert len(presets) > 0
        assert "sphere" in presets

    def test_get_preset(self):
        p = get_preset("sphere")
        assert p["algorithm"] == "mc"
        assert p["sampler"] == "sphere"

    def test_get_preset_unknown(self):
        with pytest.raises(ValueError):
            get_preset("nonexistent")

    def test_save_load_config(self):
        config = {"jobs": [{"name": "test", "sampler": "sphere", "resolution": 8}]}
        path = temp_file(".json")
        try:
            save_config(config, path)
            loaded = load_config(path)
            assert loaded["jobs"][0]["name"] == "test"
        finally:
            cleanup(path)


class TestBatchRender:
    def test_render_job(self):
        job = {
            "name": "test_sphere",
            "algorithm": "mc",
            "sampler": "sphere",
            "sampler_params": {"radius": 1.0},
            "resolution": 12,
            "bounds": [-1.5, 1.5],
        }
        result = render_job(job)
        assert result["name"] == "test_sphere"
        assert result["mesh"].num_faces > 0
        assert result["diagnostics"].num_faces > 0
        assert result["elapsed"] > 0

    def test_render_job_with_output(self):
        path = temp_file(".obj")
        job = {
            "name": "test_output",
            "algorithm": "mc",
            "sampler": "sphere",
            "resolution": 8,
            "bounds": [-1.5, 1.5],
            "output": path,
        }
        try:
            result = render_job(job)
            assert os.path.exists(path)
            assert result["output"] == path
        finally:
            cleanup(path)

    def test_render_preset(self):
        result = render_preset("sphere", preview=False)
        assert result["mesh"].num_faces > 0

    def test_render_job_with_simplify(self):
        job = {
            "name": "test_simplify",
            "algorithm": "mc",
            "sampler": "sphere",
            "resolution": 16,
            "simplify_target": 50,
        }
        result = render_job(job)
        # Simplification should reduce face count
        assert result["mesh"].num_faces > 0
        assert result["mesh"].num_faces <= 500  # should be significantly reduced from ~2000

    def test_render_job_with_subdivide(self):
        job = {
            "name": "test_subdiv",
            "algorithm": "mc",
            "sampler": "sphere",
            "resolution": 8,
            "subdivide": 1,
        }
        result = render_job(job)
        # 4x faces after 1 iteration
        assert result["mesh"].num_faces > 0

    def test_render_job_with_transform(self):
        job = {
            "name": "test_transform",
            "algorithm": "mc",
            "sampler": "sphere",
            "resolution": 8,
            "transform": {"translate": {"x": 5, "y": 0, "z": 0}},
        }
        result = render_job(job)
        mesh = result["mesh"]
        # Check mesh is translated
        xs = [v[0] for v in mesh.vertices]
        assert min(xs) > 3.0  # all shifted by +5 in x

    def test_render_job_with_preview(self):
        job = {
            "name": "test_preview",
            "algorithm": "mc",
            "sampler": "sphere",
            "resolution": 8,
            "preview": True,
        }
        result = render_job(job)
        assert "preview" in result
        assert len(result["preview"]) > 0