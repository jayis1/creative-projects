"""Tests for v1.1 enhancements: serialize, integrator modes, parallel render."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from raytracer import (
    Vec3,
    Renderer,
    build_three_balls,
    build_cornell_box,
    load_scene,
    load_scene_file,
    build_material,
    build_object,
    imageio,
)
from raytracer.material import Matte, Metal, Dielectric, Emissive, Checker
from raytracer.primitive import Sphere, Plane, Triangle, XYRect


# --------------------------------------------------------------------------- #
# Serialization
# --------------------------------------------------------------------------- #
class TestSerialize:
    def test_build_material_matte(self):
        m = build_material({"type": "matte", "albedo": [0.2, 0.3, 0.4]})
        assert isinstance(m, Matte)
        assert m.albedo == Vec3(0.2, 0.3, 0.4)

    def test_build_material_metal(self):
        m = build_material({"type": "metal", "albedo": [1, 0, 0], "fuzz": 0.3})
        assert isinstance(m, Metal)
        assert m.fuzz == 0.3

    def test_build_material_dielectric(self):
        m = build_material({"type": "dielectric", "ior": 1.33})
        assert isinstance(m, Dielectric)
        assert m.ior == 1.33

    def test_build_material_checker(self):
        m = build_material({
            "type": "checker", "scale": 2.0,
            "a": {"type": "matte", "albedo": [1, 1, 1]},
            "b": {"type": "matte", "albedo": [0, 0, 0]},
        })
        assert isinstance(m, Checker)
        assert m.scale == 2.0

    def test_build_object_sphere(self):
        o = build_object({"type": "sphere", "center": [1, 2, 3],
                          "radius": 0.5, "material": {"type": "matte"}})
        assert isinstance(o, Sphere)
        assert o.center == Vec3(1, 2, 3)
        assert o.radius == 0.5

    def test_build_object_plane(self):
        o = build_object({"type": "plane", "point": [0, 0, 0],
                          "normal": [0, 1, 0]})
        assert isinstance(o, Plane)

    def test_build_object_triangle(self):
        o = build_object({"type": "triangle", "a": [0, 0, 0],
                          "b": [1, 0, 0], "c": [0, 1, 0]})
        assert isinstance(o, Triangle)

    def test_build_object_xyrect(self):
        o = build_object({"type": "xyrect", "x0": -1, "x1": 1,
                          "y0": -1, "y1": 1, "z": 2})
        assert isinstance(o, XYRect)

    def test_load_scene_full(self):
        doc = {
            "background": "sky",
            "camera": {
                "look_from": [0, 0, 5],
                "look_at": [0, 0, 0],
                "up": [0, 1, 0],
                "vfov_deg": 50,
                "aperture": 0.1,
                "focus_dist": 5,
            },
            "objects": [
                {"type": "sphere", "center": [0, 0, -1],
                 "radius": 0.5, "material": {"type": "matte", "albedo": [0.8, 0.2, 0.2]}},
                {"type": "plane", "point": [0, -0.5, 0],
                 "normal": [0, 1, 0], "material": {"type": "matte", "albedo": [0.5, 0.5, 0.5]}},
            ],
        }
        scene = load_scene(doc, aspect=16/9)
        assert scene.world is not None
        assert scene.camera.vfov == 50

    def test_load_scene_file(self, tmp_path):
        doc = {
            "background": "black",
            "camera": {"look_from": [0, 0, 5], "look_at": [0, 0, 0]},
            "objects": [
                {"type": "sphere", "center": [0, 0, -1], "radius": 1,
                 "material": {"type": "emissive", "color": [1, 1, 1], "intensity": 2}},
            ],
        }
        p = tmp_path / "scene.json"
        p.write_text(json.dumps(doc))
        scene = load_scene_file(str(p), aspect=1.0)
        assert scene.world is not None

    def test_unknown_material_raises(self):
        with pytest.raises(ValueError):
            build_material({"type": "phong"})

    def test_unknown_object_raises(self):
        with pytest.raises(ValueError):
            build_object({"type": "torus"})


# --------------------------------------------------------------------------- #
# Integrator modes
# --------------------------------------------------------------------------- #
class TestModes:
    def test_normal_mode(self):
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=1, mode="normal", seed=1)
        pixels = r.render(scene.camera, 8, 4)
        # Normal colors should be in [0, 1] and non-constant.
        vals = set()
        for row in pixels:
            for px in row:
                assert 0.0 <= px.x <= 1.0
                assert 0.0 <= px.y <= 1.0
                assert 0.0 <= px.z <= 1.0
                vals.add((round(px.x, 2), round(px.y, 2), round(px.z, 2)))
        assert len(vals) > 1

    def test_ao_mode(self):
        # Cornell box has a black background so AO rays that miss give 0 —
        # guaranteeing a pure-greyscale result.
        scene = build_cornell_box(aspect=2.0)
        r = scene.make_renderer(samples=4, mode="ao", ao_distance=3.0, seed=1)
        pixels = r.render(scene.camera, 8, 4)
        # AO produces greyscale values in [0,1].
        for row in pixels:
            for px in row:
                assert 0.0 <= px.x <= 1.0
                assert abs(px.x - px.y) < 1e-9 and abs(px.y - px.z) < 1e-9

    def test_bad_mode_raises(self):
        scene = build_three_balls()
        with pytest.raises(ValueError):
            scene.make_renderer(mode="phong")

    def test_render_bad_dimensions(self):
        scene = build_three_balls()
        r = scene.make_renderer(samples=1)
        with pytest.raises(ValueError):
            r.render(scene.camera, 0, 10)


# --------------------------------------------------------------------------- #
# Parallel rendering
# --------------------------------------------------------------------------- #
class TestParallel:
    def test_parallel_matches_dimensions(self):
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=1, max_depth=2, seed=3)
        pixels = r.render(scene.camera, 10, 6, num_threads=2)
        assert len(pixels) == 6
        assert all(len(row) == 10 for row in pixels)


# --------------------------------------------------------------------------- #
# CLI new flags
# --------------------------------------------------------------------------- #
class TestCLIV2:
    def test_render_normal_mode(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "n.ppm"
        rc = main([
            "render", "--scene", "three-balls", "--mode", "normal",
            "--width", "8", "--height", "6", "--samples", "1",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()

    def test_render_ao_mode(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "ao.ppm"
        rc = main([
            "render", "--scene", "three-balls", "--mode", "ao",
            "--width", "8", "--height", "6", "--samples", "2",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()

    def test_render_scene_file(self, tmp_path):
        from raytracer.cli import main
        scene_json = tmp_path / "s.json"
        scene_json.write_text(json.dumps({
            "background": "sky",
            "camera": {"look_from": [0, 0, 5], "look_at": [0, 0, 0]},
            "objects": [{"type": "sphere", "center": [0, 0, -1],
                         "radius": 1, "material": {"type": "matte", "albedo": [0.8, 0.2, 0.2]}}],
        }))
        out = tmp_path / "o.ppm"
        rc = main([
            "render", "--scene-file", str(scene_json),
            "--width", "8", "--height", "6", "--samples", "1",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()

    def test_render_missing_scene_file(self):
        from raytracer.cli import main
        rc = main(["render", "--scene-file", "/no/such.json", "--out", "/tmp/x.ppm"])
        assert rc == 2

    def test_validate(self, tmp_path, capsys):
        from raytracer.cli import main
        scene_json = tmp_path / "s.json"
        scene_json.write_text(json.dumps({
            "camera": {"look_from": [0, 0, 5], "look_at": [0, 0, 0]},
            "objects": [{"type": "sphere", "center": [0, 0, -1],
                         "radius": 1, "material": {"type": "matte"}}],
        }))
        rc = main(["validate", str(scene_json)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "OK" in out

    def test_validate_bad(self, tmp_path, capsys):
        from raytracer.cli import main
        scene_json = tmp_path / "bad.json"
        scene_json.write_text("{not json")
        rc = main(["validate", str(scene_json)])
        assert rc == 1