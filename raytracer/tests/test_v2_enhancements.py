"""Tests for v2.0 enhancements: textures, new primitives, integrator modes,
animation, logging, serialization, and new scene presets."""

import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from raytracer import (
    Vec3, Ray, Camera, Renderer, Sphere, Plane, Triangle,
    XYRect, XZRect, YZRect, Box, Disk, Cylinder,
    Matte, Metal, Dielectric, Emissive, Checker, Isotropic,
    BVHNode, HittableList, AABB, HitRecord,
    Texture, SolidColor, CheckerTexture, PerlinNoise, NoiseTexture,
    Turbulence, Marble, ImageTexture,
    build_three_balls, build_cornell_box, build_random_spheres,
    build_solar_system, build_marble_hall, build_nebula,
    load_scene, load_scene_file, build_material, build_object, build_texture,
    imageio,
)
from raytracer.renderer import sky_gradient, constant_background, MODES
from raytracer import material as mat_mod
from raytracer import animation


# --------------------------------------------------------------------------- #
# Textures
# --------------------------------------------------------------------------- #
class TestTextures:
    def test_solid_color(self):
        t = SolidColor(Vec3(0.5, 0.6, 0.7))
        c = t.value(0, 0, Vec3(0, 0, 0))
        assert c == Vec3(0.5, 0.6, 0.7)

    def test_solid_color_from_rgb(self):
        t = SolidColor.from_rgb(0.1, 0.2, 0.3)
        assert t.value(0, 0, Vec3(0, 0, 0)) == Vec3(0.1, 0.2, 0.3)

    def test_checker_texture(self):
        even = SolidColor(Vec3(1, 1, 1))
        odd = SolidColor(Vec3(0, 0, 0))
        t = CheckerTexture(even, odd, scale=1.0)
        c0 = t.value(0, 0, Vec3(0.5, 0.5, 0.5))
        c1 = t.value(0, 0, Vec3(1.5, 0.5, 0.5))
        assert c0 == Vec3(1, 1, 1)
        assert c1 == Vec3(0, 0, 0)

    def test_perlin_noise_range(self):
        p = PerlinNoise(seed=0, scale=1.0)
        for _ in range(20):
            v = p.noise(Vec3(0.5, 0.5, 0.5))
            assert 0.0 <= v <= 1.0
        # Deterministic for same seed.
        p2 = PerlinNoise(seed=0, scale=1.0)
        assert p.noise(Vec3(1.2, 3.4, 5.6)) == p2.noise(Vec3(1.2, 3.4, 5.6))

    def test_perlin_turbulence_range(self):
        p = PerlinNoise(seed=1, scale=2.0)
        for _ in range(10):
            v = p.turbulence(Vec3(0.1, 0.2, 0.3), depth=4)
            assert 0.0 <= v <= 1.0

    def test_noise_texture(self):
        t = NoiseTexture(Vec3(0, 0, 0), Vec3(1, 1, 1), scale=1.0, seed=0)
        c = t.value(0, 0, Vec3(0.5, 0.5, 0.5))
        # Should be somewhere between color1 and color2.
        assert 0.0 <= c.x <= 1.0
        assert 0.0 <= c.y <= 1.0
        assert 0.0 <= c.z <= 1.0

    def test_turbulence_texture(self):
        t = Turbulence(Vec3(0.5, 0.5, 0.5), scale=2.0, depth=3, seed=0)
        c = t.value(0, 0, Vec3(0.3, 0.3, 0.3))
        assert c.x >= 0.0

    def test_marble_texture(self):
        t = Marble(Vec3(0.9, 0.9, 0.95), Vec3(0.1, 0.1, 0.15), scale=2.0, seed=0)
        c = t.value(0, 0, Vec3(0.5, 0.5, 0.5))
        assert 0.0 <= c.x <= 1.0

    def test_image_texture_from_pixels(self):
        pixels = [[Vec3(0.5, 0.25, 0.0)]]
        tex = ImageTexture.from_pixels(pixels)
        c = tex.value(0, 0, Vec3(0, 0, 0))
        assert abs(c.x - 0.5) < 0.01
        assert abs(c.y - 0.25) < 0.01

    def test_image_texture_flat_bytes(self):
        flat = bytes([10, 20, 30, 40, 50, 60])
        tex = ImageTexture(flat, width=2, height=1)
        c0 = tex.value(0, 0, Vec3(0, 0, 0))
        # u=0.5 maps to the second pixel (index 1).
        c1 = tex.value(0.5, 0, Vec3(0, 0, 0))
        assert abs(c0.x - 10/255.0) < 1e-6
        assert abs(c1.x - 40/255.0) < 1e-6

    def test_build_texture_solid(self):
        t = build_texture({"type": "solid", "color": [0.3, 0.4, 0.5]})
        assert isinstance(t, SolidColor)
        assert t.value(0, 0, Vec3(0, 0, 0)) == Vec3(0.3, 0.4, 0.5)

    def test_build_texture_checker(self):
        t = build_texture({
            "type": "checker", "scale": 1.0,
            "even": {"type": "solid", "color": [1, 1, 1]},
            "odd": {"type": "solid", "color": [0, 0, 0]},
        })
        assert isinstance(t, CheckerTexture)

    def test_build_texture_noise(self):
        t = build_texture({"type": "noise", "scale": 2.0})
        assert isinstance(t, NoiseTexture)

    def test_build_texture_marble(self):
        t = build_texture({"type": "marble", "scale": 3.0})
        assert isinstance(t, Marble)

    def test_build_texture_shorthand_list(self):
        t = build_texture([0.2, 0.3, 0.4])
        assert isinstance(t, SolidColor)
        assert t.value(0, 0, Vec3(0, 0, 0)) == Vec3(0.2, 0.3, 0.4)

    def test_build_texture_unknown_raises(self):
        with pytest.raises(ValueError):
            build_texture({"type": "wood"})


# --------------------------------------------------------------------------- #
# New primitives: XZRect, YZRect, Box, Disk, Cylinder
# --------------------------------------------------------------------------- #
class TestXZRect:
    def test_hit(self):
        rect = XZRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(0, 0, 0), Vec3(0, -1, 0))
        rec = rect.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 5.0) < 1e-6

    def test_miss_outside(self):
        rect = XZRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(3, 0, 0), Vec3(0, -1, 0))
        assert rect.hit(r, 0.001, 100) is None

    def test_parallel_ray_returns_none(self):
        rect = XZRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(0, 0, 0), Vec3(1, 0, 0))
        assert rect.hit(r, 0.001, 100) is None


class TestYZRect:
    def test_hit(self):
        rect = YZRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(0, 0, 0), Vec3(-1, 0, 0))
        rec = rect.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 5.0) < 1e-6

    def test_miss_outside(self):
        rect = YZRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(0, 3, 0), Vec3(-1, 0, 0))
        assert rect.hit(r, 0.001, 100) is None

    def test_parallel_ray_returns_none(self):
        rect = YZRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
        assert rect.hit(r, 0.001, 100) is None


class TestBox:
    def test_hit_front_face(self):
        box = Box(Vec3(-1, -1, -2), Vec3(1, 1, -1))
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = box.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 1.0) < 1e-6

    def test_hit_from_outside(self):
        box = Box(Vec3(-1, -1, -5), Vec3(1, 1, -3))
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = box.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 3.0) < 1e-6

    def test_miss(self):
        box = Box(Vec3(-1, -1, -5), Vec3(1, 1, -3))
        r = Ray(Vec3(5, 5, 0), Vec3(0, 0, -1))
        assert box.hit(r, 0.001, 100) is None

    def test_bbox(self):
        box = Box(Vec3(1, 2, 3), Vec3(4, 5, 6))
        b = box.bbox()
        assert b.mn == Vec3(1, 2, 3)
        assert b.mx == Vec3(4, 5, 6)

    def test_normalized_corners(self):
        # Corners given in reverse order should still work.
        box = Box(Vec3(4, 5, 6), Vec3(1, 2, 3))
        assert box.bbox().mn == Vec3(1, 2, 3)


class TestDisk:
    def test_hit(self):
        disk = Disk(Vec3(0, 0, -5), Vec3(0, 0, 1), 1.0)
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = disk.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 5.0) < 1e-6

    def test_miss_outside(self):
        disk = Disk(Vec3(0, 0, -5), Vec3(0, 0, 1), 1.0)
        r = Ray(Vec3(3, 0, 0), Vec3(0, 0, -1))
        assert disk.hit(r, 0.001, 100) is None

    def test_parallel_ray_returns_none(self):
        disk = Disk(Vec3(0, 0, -5), Vec3(0, 0, 1), 1.0)
        r = Ray(Vec3(0, 0, 0), Vec3(1, 0, 0))
        assert disk.hit(r, 0.001, 100) is None

    def test_zero_normal_raises(self):
        with pytest.raises(ValueError):
            Disk(Vec3(0, 0, 0), Vec3(0, 0, 0), 1.0)


class TestCylinder:
    def test_hit_side(self):
        cyl = Cylinder(Vec3(0, 0, -5), 1.0, -2, 2)
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = cyl.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 4.0) < 1e-6  # 5 - 1

    def test_miss_side(self):
        cyl = Cylinder(Vec3(0, 0, -5), 0.5, -2, 2)
        r = Ray(Vec3(3, 0, 0), Vec3(0, 0, -1))
        assert cyl.hit(r, 0.001, 100) is None

    def test_hit_cap(self):
        cyl = Cylinder(Vec3(0, 0, -5), 1.0, -2, 2)
        # Ray hitting the top cap from above.
        r = Ray(Vec3(0, 5, -5), Vec3(0, -1, 0))
        rec = cyl.hit(r, 0.001, 100)
        assert rec is not None

    def test_miss_above_cap(self):
        cyl = Cylinder(Vec3(0, 0, -5), 1.0, -2, 2)
        # Ray above and to the side — should miss caps.
        r = Ray(Vec3(3, 5, -5), Vec3(0, -1, 0))
        assert cyl.hit(r, 0.001, 100) is None

    def test_uncapped(self):
        cyl = Cylinder(Vec3(0, 0, -5), 1.0, -2, 2, capped=False)
        # Ray from above — with no caps it should miss.
        r = Ray(Vec3(0, 5, -5), Vec3(0, -1, 0))
        assert cyl.hit(r, 0.001, 100) is None

    def test_ray_parallel_to_axis(self):
        cyl = Cylinder(Vec3(0, 0, -5), 1.0, -2, 2)
        # Ray inside cylinder going along axis (down).  Should hit the
        # bottom cap at y=-2.
        r = Ray(Vec3(0, 0, -5), Vec3(0, -1, 0))
        rec = cyl.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 2.0) < 1e-6  # from y=0 to y=-2

    def test_bbox(self):
        cyl = Cylinder(Vec3(1, 0, 2), 0.5, -1, 3)
        b = cyl.bbox()
        assert b.mn == Vec3(0.5, -1, 1.5)
        assert b.mx == Vec3(1.5, 3, 2.5)


# --------------------------------------------------------------------------- #
# Textured materials
# --------------------------------------------------------------------------- #
class TestTexturedMaterials:
    def test_matte_with_texture(self):
        tex = SolidColor(Vec3(0.3, 0.6, 0.9))
        m = Matte(tex)
        assert m.texture is tex

    def test_matte_with_vec3(self):
        m = Matte(Vec3(0.3, 0.6, 0.9))
        assert isinstance(m.texture, SolidColor)
        assert m.albedo == Vec3(0.3, 0.6, 0.9)

    def test_matte_scatter_uses_texture(self):
        mat_mod.seed(1)
        tex = SolidColor(Vec3(0.2, 0.4, 0.6))
        m = Matte(tex)
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = HitRecord(1.0, Vec3(0, 0, -1), Vec3(0, 0, 1), m, r)
        atten, sr = m.scatter(r, rec)
        assert atten == Vec3(0.2, 0.4, 0.6)

    def test_metal_with_texture(self):
        tex = SolidColor(Vec3(0.8, 0.8, 0.8))
        m = Metal(tex, fuzz=0.1)
        assert m.texture is tex
        assert m.fuzz == 0.1

    def test_emissive_with_texture(self):
        tex = SolidColor(Vec3(1, 0.9, 0.8))
        e = Emissive(tex, intensity=3.0)
        emit = e.emit(0, 0, Vec3(0, 0, 0))
        assert abs(emit.x - 3.0) < 1e-6
        assert abs(emit.y - 2.7) < 1e-6
        assert abs(emit.z - 2.4) < 1e-6

    def test_isotropic_scatter(self):
        mat_mod.seed(1)
        m = Isotropic(Vec3(0.5, 0.5, 0.5))
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = HitRecord(1.0, Vec3(0, 0, -1), Vec3(0, 0, 1), m, r)
        result = m.scatter(r, rec)
        assert result is not None
        atten, scattered = result
        assert atten == Vec3(0.5, 0.5, 0.5)
        assert abs(scattered.direction.length() - 1.0) < 1e-9

    def test_matte_scattering_pdf(self):
        m = Matte(Vec3(0.8, 0.8, 0.8))
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = HitRecord(1.0, Vec3(0, 0, -1), Vec3(0, 0, 1), m, r)
        # A scattered ray going straight along the normal should have PDF = 1/pi.
        scattered = Ray(rec.point, Vec3(0, 0, 1))
        pdf = m.scattering_pdf(r, rec, scattered)
        assert abs(pdf - 1.0 / math.pi) < 1e-6


# --------------------------------------------------------------------------- #
# New integrator modes
# --------------------------------------------------------------------------- #
class TestDepthMode:
    def test_depth_mode_produces_grayscale(self):
        # Use a constant black background so misses are also grayscale.
        from raytracer.renderer import constant_background
        scene = build_three_balls(aspect=2.0)
        scene.background = constant_background(Vec3(0, 0, 0))
        r = scene.make_renderer(samples=1, mode="depth", ao_distance=10.0, seed=1)
        pixels = r.render(scene.camera, 8, 4)
        for row in pixels:
            for px in row:
                assert 0.0 <= px.x <= 1.0
                assert abs(px.x - px.y) < 1e-9
                assert abs(px.y - px.z) < 1e-9

    def test_depth_mode_misses_return_background(self):
        # A scene with a single sphere, render a ray that misses.
        ball = Sphere(Vec3(10, 10, -10), 0.5)
        world = BVHNode([ball])
        from raytracer.renderer import constant_background
        r = Renderer(world, background=constant_background(Vec3(0.1, 0.2, 0.3)),
                       samples=1, mode="depth", seed=1)
        cam = Camera(Vec3(0, 0, 0), Vec3(0, 0, -1), Vec3(0, 1, 0),
                     45, 1.0, aperture=0.0, focus_dist=1.0)
        pixels = r.render(cam, 4, 4)
        # Rays mostly miss — the background should show through.
        found_bg = any(
            abs(px.x - 0.1) < 1e-6 and abs(px.y - 0.2) < 1e-6 and abs(px.z - 0.3) < 1e-6
            for row in pixels for px in row
        )
        assert found_bg


# --------------------------------------------------------------------------- #
# Render statistics
# --------------------------------------------------------------------------- #
class TestRenderStats:
    def test_stats_collected(self):
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=2, max_depth=2, seed=42)
        pixels = r.render(scene.camera, 8, 4)
        assert r.stats.rays > 0
        assert r.stats.elapsed >= 0.0
        assert r.stats.width == 8
        assert r.stats.height == 4
        d = r.stats.as_dict()
        assert "rays" in d
        assert "elapsed_s" in d

    def test_rays_per_second(self):
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=1, max_depth=1, seed=42)
        r.render(scene.camera, 4, 2)
        assert r.stats.rays_per_second() >= 0


# --------------------------------------------------------------------------- #
# Russian roulette
# --------------------------------------------------------------------------- #
class TestRussianRoulette:
    def test_rr_terminates(self):
        """With rr_start_depth > 0, very high max_depth should still terminate."""
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=1, max_depth=50, seed=42, rr_start_depth=2)
        pixels = r.render(scene.camera, 4, 2)
        assert len(pixels) == 2
        # Should complete without infinite recursion.

    def test_rr_off_by_default(self):
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=1, max_depth=3, seed=42)
        assert r.rr_start_depth == 0


# --------------------------------------------------------------------------- #
# NEE (Next Event Estimation)
# --------------------------------------------------------------------------- #
class TestNEE:
    def test_lights_forwarded(self):
        scene = build_cornell_box(aspect=1.0)
        r = scene.make_renderer(samples=1, max_depth=2, seed=42)
        assert len(r.lights) > 0

    def test_no_lights_by_default(self):
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=1, max_depth=2, seed=42)
        assert len(r.lights) == 0


# --------------------------------------------------------------------------- #
# Animation
# --------------------------------------------------------------------------- #
class TestAnimation:
    def test_orbit_path(self):
        positions = animation.orbit_path(Vec3(0, 0, 0), 5.0, 2.0, 10)
        assert len(positions) == 10
        # All positions should be at height 2.0.
        for p in positions:
            assert abs(p.y - 2.0) < 1e-9
        # All should be distance 5 from center.
        for p in positions:
            assert abs(math.sqrt(p.x ** 2 + p.z ** 2) - 5.0) < 1e-6

    def test_linear_path(self):
        positions = animation.linear_path(Vec3(0, 0, 0), Vec3(10, 0, 0), 5)
        assert len(positions) == 5
        assert positions[0] == Vec3(0, 0, 0)
        assert positions[4] == Vec3(10, 0, 0)
        assert positions[2] == Vec3(5, 0, 0)

    def test_spline_path(self):
        pts = [Vec3(0, 0, 0), Vec3(1, 1, 0), Vec3(2, 0, 0)]
        positions = animation.spline_path(pts, 10)
        assert len(positions) == 10
        # Endpoints should roughly match.
        assert abs(positions[0].x) < 0.5
        assert abs(positions[-1].x - 2.0) < 0.5

    def test_render_animation(self, tmp_path):
        scene = build_three_balls(aspect=2.0)
        positions = animation.orbit_path(Vec3(0, 0, -1), 3.0, 1.0, 3)
        paths = animation.render_animation(
            scene=scene,
            eye_positions=positions,
            out_dir=str(tmp_path / "frames"),
            width=16, height=8, samples=1, max_depth=2,
            fmt="ppm",
            progress=False,
        )
        assert len(paths) == 3
        for p in paths:
            assert os.path.exists(p)

    def test_render_animation_png(self, tmp_path):
        pytest.importorskip("PIL")
        scene = build_three_balls(aspect=2.0)
        positions = animation.linear_path(Vec3(2, 0.5, 2), Vec3(-2, 0.5, 2), 2)
        paths = animation.render_animation(
            scene=scene,
            eye_positions=positions,
            out_dir=str(tmp_path / "frames_png"),
            width=16, height=8, samples=1, max_depth=1,
            fmt="png",
            progress=False,
        )
        assert len(paths) == 2


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
class TestLogging:
    def test_configure(self):
        from raytracer.logging import configure, get_level, logger
        import logging
        configure("DEBUG")
        assert get_level() == logging.DEBUG
        configure("WARNING")
        assert get_level() == logging.WARNING

    def test_logger_has_name(self):
        from raytracer.logging import logger
        assert logger.name == "raytracer"


# --------------------------------------------------------------------------- #
# New scene presets
# --------------------------------------------------------------------------- #
class TestNewPresets:
    def test_solar_system(self):
        s = build_solar_system(aspect=2.0)
        assert s.world is not None
        assert s.camera is not None
        assert s.lights is not None and len(s.lights) > 0

    def test_marble_hall(self):
        s = build_marble_hall(aspect=2.0)
        assert s.world is not None
        assert s.camera is not None
        assert s.lights is not None and len(s.lights) > 0

    def test_nebula(self):
        s = build_nebula(aspect=2.0)
        assert s.world is not None
        assert s.camera is not None

    def test_all_presets_render(self):
        for name, builder in [
            ("three-balls", build_three_balls),
            ("cornell", build_cornell_box),
            ("random", build_random_spheres),
            ("solar-system", build_solar_system),
            ("marble-hall", build_marble_hall),
            ("nebula", build_nebula),
        ]:
            scene = builder(aspect=2.0)
            r = scene.make_renderer(samples=2, max_depth=3, seed=42)
            pixels = r.render(scene.camera, 4, 2)
            assert len(pixels) == 2
            assert all(len(row) == 4 for row in pixels)
            # At least one pixel should be nonzero (all scenes have either
            # emissive lights, a bright background, or textured objects).
            assert any(p.length_squared() > 0 for row in pixels for p in row), \
                f"Scene {name} rendered all-black"


# --------------------------------------------------------------------------- #
# Extended serialization
# --------------------------------------------------------------------------- #
class TestExtendedSerialize:
    def test_build_material_isotropic(self):
        m = build_material({"type": "isotropic", "albedo": [0.5, 0.5, 0.5]})
        assert isinstance(m, Isotropic)

    def test_build_object_box(self):
        o = build_object({"type": "box", "min": [0, 0, 0], "max": [1, 1, 1]})
        assert isinstance(o, Box)

    def test_build_object_disk(self):
        o = build_object({
            "type": "disk", "center": [0, 0, -5],
            "normal": [0, 0, 1], "radius": 1.0,
        })
        assert isinstance(o, Disk)

    def test_build_object_cylinder(self):
        o = build_object({
            "type": "cylinder", "center": [0, 0, -5], "radius": 1.0,
            "y0": -1, "y1": 1,
        })
        assert isinstance(o, Cylinder)

    def test_build_object_xzrect(self):
        o = build_object({
            "type": "xzrect", "x0": -1, "x1": 1, "z0": -1, "z1": 1, "y": 2,
        })
        assert isinstance(o, XZRect)

    def test_build_object_yzrect(self):
        o = build_object({
            "type": "yzrect", "y0": -1, "y1": 1, "z0": -1, "z1": 1, "x": 2,
        })
        assert isinstance(o, YZRect)

    def test_textured_material_in_scene(self):
        doc = {
            "camera": {"look_from": [0, 0, 5], "look_at": [0, 0, 0]},
            "objects": [
                {"type": "sphere", "center": [0, 0, -1], "radius": 1,
                 "material": {"type": "matte",
                              "albedo": {"type": "noise", "scale": 3.0}}},
            ],
        }
        scene = load_scene(doc, aspect=1.0)
        assert scene.world is not None

    def test_load_yaml_scene(self, tmp_path):
        pytest.importorskip("yaml")
        yaml_text = (
            "background: sky\n"
            "camera:\n"
            "  look_from: [0, 0, 5]\n"
            "  look_at: [0, 0, 0]\n"
            "  vfov_deg: 50\n"
            "objects:\n"
            "  - type: sphere\n"
            "    center: [0, 0, -1]\n"
            "    radius: 1\n"
            "    material:\n"
            "      type: matte\n"
            "      albedo: [0.8, 0.2, 0.2]\n"
        )
        p = tmp_path / "scene.yaml"
        p.write_text(yaml_text)
        scene = load_scene_file(str(p), aspect=1.0)
        assert scene.world is not None

    def test_load_toml_scene(self, tmp_path):
        try:
            import tomllib
        except ImportError:
            try:
                import tomli
            except ImportError:
                pytest.skip("No TOML parser available")
        toml_text = (
            '[camera]\n'
            'look_from = [0, 0, 5]\n'
            'look_at = [0, 0, 0]\n'
            'vfov_deg = 50\n'
            '\n'
            '[[objects]]\n'
            'type = "sphere"\n'
            'center = [0, 0, -1]\n'
            'radius = 1.0\n'
            '\n'
            '[objects.material]\n'
            'type = "matte"\n'
            'albedo = [0.8, 0.2, 0.2]\n'
        )
        p = tmp_path / "scene.toml"
        p.write_text(toml_text)
        scene = load_scene_file(str(p), aspect=1.0)
        assert scene.world is not None

    def test_lights_auto_detected(self):
        doc = {
            "camera": {"look_from": [0, 0, 5], "look_at": [0, 0, 0]},
            "objects": [
                {"type": "xyrect", "x0": -1, "x1": 1, "y0": -1, "y1": 1, "z": -3,
                 "material": {"type": "emissive", "color": [1, 1, 1], "intensity": 5}},
                {"type": "sphere", "center": [0, 0, -5], "radius": 1,
                 "material": {"type": "matte", "albedo": [0.8, 0.2, 0.2]}},
            ],
        }
        scene = load_scene(doc, aspect=1.0)
        assert scene.lights is not None
        assert len(scene.lights) == 1


# --------------------------------------------------------------------------- #
# New CLI commands
# --------------------------------------------------------------------------- #
class TestCLIV3:
    def test_info_mentions_new_features(self, capsys):
        from raytracer.cli import main
        rc = main(["info"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "animation" in out.lower() or "texture" in out.lower()

    def test_scenes_lists_new_presets(self, capsys):
        from raytracer.cli import main
        rc = main(["scenes"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "solar-system" in out
        assert "marble-hall" in out
        assert "nebula" in out

    def test_render_depth_mode(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "d.ppm"
        rc = main([
            "render", "--scene", "three-balls", "--mode", "depth",
            "--width", "8", "--height", "6", "--samples", "1",
            "--ao-distance", "10",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()

    def test_render_stats_flag(self, tmp_path, capsys):
        from raytracer.cli import main
        out = tmp_path / "s.ppm"
        rc = main([
            "render", "--scene", "three-balls",
            "--width", "4", "--height", "3", "--samples", "1",
            "--max-depth", "1",
            "--out", str(out), "--format", "ppm", "--quiet", "--stats",
        ])
        captured = capsys.readouterr()
        assert rc == 0
        assert '"rays"' in captured.out

    def test_stats_command(self, capsys):
        from raytracer.cli import main
        rc = main([
            "stats", "--scene", "three-balls",
            "--width", "4", "--height", "3", "--samples", "1",
            "--max-depth", "1",
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert '"rays"' in out

    def test_render_rr_start_depth(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "rr.ppm"
        rc = main([
            "render", "--scene", "three-balls",
            "--width", "4", "--height", "3", "--samples", "1",
            "--max-depth", "20", "--rr-start-depth", "3",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()

    def test_animate_orbit(self, tmp_path):
        from raytracer.cli import main
        out_dir = tmp_path / "anim"
        rc = main([
            "animate", "--scene", "three-balls", "--orbit",
            "--frames", "3", "--radius", "3", "--height", "1.0",
            "--width", "8", "--height-px", "4", "--samples", "1",
            "--max-depth", "1", "--out-dir", str(out_dir),
            "--out-format", "ppm", "--quiet",
        ])
        assert rc == 0
        files = list(out_dir.iterdir())
        assert len(files) == 3

    def test_animate_dolly(self, tmp_path):
        from raytracer.cli import main
        out_dir = tmp_path / "dolly"
        rc = main([
            "animate", "--scene", "three-balls", "--dolly",
            "--frames", "2", "--start", "2", "0", "2", "--end", "-2", "0", "2",
            "--width", "8", "--height-px", "4", "--samples", "1",
            "--max-depth", "1", "--out-dir", str(out_dir),
            "--out-format", "ppm", "--quiet",
        ])
        assert rc == 0
        files = list(out_dir.iterdir())
        assert len(files) == 2

    def test_validate_yaml(self, tmp_path, capsys):
        pytest.importorskip("yaml")
        scene_yaml = tmp_path / "s.yaml"
        scene_yaml.write_text(
            "camera:\n  look_from: [0, 0, 5]\n  look_at: [0, 0, 0]\n"
            "objects:\n  - type: sphere\n    center: [0, 0, -1]\n    radius: 1\n"
        )
        from raytracer.cli import main
        rc = main(["validate", str(scene_yaml)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "OK" in out

    def test_render_new_scene_solar_system(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "sol.ppm"
        rc = main([
            "render", "--scene", "solar-system",
            "--width", "8", "--height", "6", "--samples", "1",
            "--max-depth", "2",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()

    def test_render_new_scene_marble_hall(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "marble.ppm"
        rc = main([
            "render", "--scene", "marble-hall",
            "--width", "8", "--height", "6", "--samples", "1",
            "--max-depth", "2",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()

    def test_render_new_scene_nebula(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "neb.ppm"
        rc = main([
            "render", "--scene", "nebula",
            "--width", "8", "--height", "6", "--samples", "1",
            "--max-depth", "2",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0 and out.exists()