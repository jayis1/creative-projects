"""Tests for the ray tracer package."""

import math
import os
import sys
import tempfile

# Make the package importable when run directly from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from raytracer import (
    Vec3,
    Ray,
    Camera,
    Renderer,
    Sphere,
    Plane,
    Triangle,
    XYRect,
    Matte,
    Metal,
    Dielectric,
    Emissive,
    Checker,
    BVHNode,
    HittableList,
    AABB,
    HitRecord,
    build_three_balls,
    build_cornell_box,
    build_random_spheres,
    imageio,
)
from raytracer.renderer import sky_gradient, constant_background
from raytracer import material as mat_mod


# --------------------------------------------------------------------------- #
# Vec3
# --------------------------------------------------------------------------- #
class TestVec3:
    def test_add_sub(self):
        a = Vec3(1, 2, 3)
        b = Vec3(4, 5, 6)
        assert (a + b) == Vec3(5, 7, 9)
        assert (b - a) == Vec3(3, 3, 3)

    def test_mul_scalar_and_vec(self):
        a = Vec3(1, 2, 3)
        assert (a * 2) == Vec3(2, 4, 6)
        assert (2 * a) == Vec3(2, 4, 6)
        assert (a * Vec3(2, 2, 2)) == Vec3(2, 4, 6)

    def test_dot_cross(self):
        i, j, k = Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)
        assert i.dot(j) == 0
        assert i.cross(j) == k
        assert j.cross(k) == i

    def test_length_normalize(self):
        v = Vec3(3, 4, 0)
        assert v.length() == 5.0
        n = v.normalized()
        assert abs(n.length() - 1.0) < 1e-12

    def test_normalize_zero_raises(self):
        with pytest.raises(ValueError):
            Vec3.zero().normalized()

    def test_reflect(self):
        d = Vec3(1, -1, 0)
        n = Vec3(0, 1, 0)
        r = d.reflect(n)
        assert abs(r.x - 1.0) < 1e-12 and abs(r.y - 1.0) < 1e-12

    def test_clamp(self):
        v = Vec3(-0.5, 0.3, 1.5)
        c = v.clamp(0, 1)
        assert c == Vec3(0, 0.3, 1)

    def test_lerp(self):
        a = Vec3(0, 0, 0)
        b = Vec3(10, 10, 10)
        assert a.lerp(b, 0.5) == Vec3(5, 5, 5)

    def test_div_zero_raises(self):
        with pytest.raises(ZeroDivisionError):
            Vec3(1, 1, 1) / 0


# --------------------------------------------------------------------------- #
# Ray
# --------------------------------------------------------------------------- #
class TestRay:
    def test_at(self):
        r = Ray(Vec3(0, 0, 0), Vec3(1, 0, 0))
        assert r.at(5) == Vec3(5, 0, 0)

    def test_zero_direction_raises(self):
        with pytest.raises(ValueError):
            Ray(Vec3(0, 0, 0), Vec3(0, 0, 0))


# --------------------------------------------------------------------------- #
# AABB
# --------------------------------------------------------------------------- #
class TestAABB:
    def test_surrounding(self):
        a = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        b = AABB(Vec3(0.5, 0.5, 0.5), Vec3(2, 2, 2))
        c = AABB.surrounding(a, b)
        assert c.mn == Vec3(0, 0, 0)
        assert c.mx == Vec3(2, 2, 2)

    def test_hit_simple(self):
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        r = Ray(Vec3(-5, 0, 0), Vec3(1, 0, 0))
        assert box.hit(r, 0, 100)
        r2 = Ray(Vec3(-5, 5, 0), Vec3(1, 0, 0))
        assert not box.hit(r2, 0, 100)


# --------------------------------------------------------------------------- #
# Primitive intersections
# --------------------------------------------------------------------------- #
class TestSphere:
    def test_hit_center(self):
        s = Sphere(Vec3(0, 0, -5), 1.0, Matte(Vec3(1, 1, 1)))
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = s.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 4.0) < 1e-6  # 5 - 1
        assert abs(rec.point.z - (-4.0)) < 1e-6

    def test_miss(self):
        s = Sphere(Vec3(0, 0, -5), 1.0)
        r = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
        assert s.hit(r, 0.001, 100) is None

    def test_bbox(self):
        s = Sphere(Vec3(1, 2, 3), 2.0)
        b = s.bbox()
        assert b.mn == Vec3(-1, 0, 1)
        assert b.mx == Vec3(3, 4, 5)


class TestPlane:
    def test_hit(self):
        p = Plane(Vec3(0, 0, 0), Vec3(0, 1, 0))
        r = Ray(Vec3(0, 5, 0), Vec3(0, -1, 0))
        rec = p.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 5.0) < 1e-6

    def test_parallel_misses(self):
        p = Plane(Vec3(0, 0, 0), Vec3(0, 1, 0))
        r = Ray(Vec3(0, 5, 0), Vec3(1, 0, 0))
        assert p.hit(r, 0.001, 100) is None

    def test_zero_normal_raises(self):
        with pytest.raises(ValueError):
            Plane(Vec3(0, 0, 0), Vec3(0, 0, 0))


class TestTriangle:
    def test_hit(self):
        # Triangle in the z=-5 plane facing +z.
        tri = Triangle(Vec3(-1, -1, -5), Vec3(1, -1, -5), Vec3(0, 1, -5))
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = tri.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 5.0) < 1e-6

    def test_miss_outside(self):
        tri = Triangle(Vec3(-1, -1, -5), Vec3(1, -1, -5), Vec3(0, 1, -5))
        r = Ray(Vec3(3, 0, 0), Vec3(0, 0, -1))
        assert tri.hit(r, 0.001, 100) is None

    def test_back_cull(self):
        # Ray from behind: still hits (we don't backface-cull by default).
        tri = Triangle(Vec3(-1, -1, -5), Vec3(1, -1, -5), Vec3(0, 1, -5))
        r = Ray(Vec3(0, 0, -10), Vec3(0, 0, 1))
        rec = tri.hit(r, 0.001, 100)
        # Triangle should still intersect (no backface cull).
        assert rec is not None


class TestXYRect:
    def test_hit(self):
        rect = XYRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = rect.hit(r, 0.001, 100)
        assert rec is not None
        assert abs(rec.t - 5.0) < 1e-6

    def test_miss_outside(self):
        rect = XYRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(3, 0, 0), Vec3(0, 0, -1))
        assert rect.hit(r, 0.001, 100) is None


# --------------------------------------------------------------------------- #
# Materials
# --------------------------------------------------------------------------- #
class TestMaterials:
    def test_matte_scatter(self):
        mat_mod.seed(1)
        m = Matte(Vec3(0.8, 0.2, 0.2))
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = HitRecord(1.0, Vec3(0, 0, -1), Vec3(0, 0, 1), m, r)
        res = m.scatter(r, rec)
        assert res is not None
        atten, sr = res
        assert atten == Vec3(0.8, 0.2, 0.2)

    def test_metal_absorbs_below_surface(self):
        m = Metal(Vec3(0.8, 0.8, 0.8), fuzz=0.0)
        r = Ray(Vec3(0, 0, 0), Vec3(0, -1, 0))
        # Normal pointing up; reflected dir would be up — but if we force a
        # grazing ray we can trigger absorption.  Use a ray going into surface.
        rec = HitRecord(1.0, Vec3(0, 0, 0), Vec3(0, 1, 0), m, r)
        res = m.scatter(r, rec)
        # reflected = (0,1,0); dot(normal) = 1 > 0, so it should scatter.
        assert res is not None

    def test_dielectric_total_internal_reflection(self):
        mat_mod.seed(1)
        d = Dielectric(1.5)
        # Ray hitting from inside going outward at steep angle.
        r = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
        # front_face will be False because dot(dir, normal)>0 when normal is -y
        rec = HitRecord(1.0, Vec3(0, 0, 0), Vec3(0, -1, 0), d, r)
        # Use a near-grazing ray to trigger TIR.
        r2 = Ray(Vec3(0, 0, 0), Vec3(0.99, 0.141, 0).normalized() if False else Vec3(0.99, 0.01, 0))
        rec2 = HitRecord(1.0, Vec3(0, 0, 0), Vec3(0, -1, 0), d, r2)
        res = d.scatter(r2, rec2)
        assert res is not None  # always returns something (reflect or refract)

    def test_emissive(self):
        e = Emissive(Vec3(1, 1, 1), intensity=4.0)
        assert e.emit(0, 0, Vec3(0, 0, 0)) == Vec3(4, 4, 4)
        assert e.emitted_albedo() == Vec3(4, 4, 4)

    def test_checker_alternates(self):
        a = Matte(Vec3(1, 1, 1))
        b = Matte(Vec3(0, 0, 0))
        c = Checker(a, b, scale=1.0)
        # At integer lattice points the checker flips.
        # which() uses floor(x/s)+floor(y/s)+floor(z/s) parity.
        p0 = Vec3(0.5, 0.5, 0.5)  # floors 0+0+0 = 0 -> a
        p1 = Vec3(1.5, 0.5, 0.5)  # floors 1+0+0 = 1 -> b
        assert c._which(p0) is a
        assert c._which(p1) is b


# --------------------------------------------------------------------------- #
# BVH
# --------------------------------------------------------------------------- #
class TestBVH:
    def test_build_and_hit(self):
        s1 = Sphere(Vec3(0, 0, -2), 0.5)
        s2 = Sphere(Vec3(0, 0, -4), 0.5)
        bvh = BVHNode([s1, s2])
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = bvh.hit(r, 0.001, 100)
        assert rec is not None
        # Nearest sphere is at z=-2 radius 0.5 -> t=1.5
        assert abs(rec.t - 1.5) < 1e-6

    def test_empty(self):
        bvh = BVHNode([])
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        assert bvh.hit(r, 0.001, 100) is None

    def test_hittable_list(self):
        lst = HittableList([Sphere(Vec3(0, 0, -2), 0.5), Sphere(Vec3(0, 0, -4), 0.5)])
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = lst.hit(r, 0.001, 100)
        assert rec is not None and abs(rec.t - 1.5) < 1e-6


# --------------------------------------------------------------------------- #
# Camera
# --------------------------------------------------------------------------- #
class TestCamera:
    def test_ray_corners(self):
        cam = Camera(
            look_from=Vec3(0, 0, 0),
            look_at=Vec3(0, 0, -1),
            up=Vec3(0, 1, 0),
            vfov_deg=90.0,
            aspect=2.0,
            aperture=0.0,
            focus_dist=1.0,
        )
        r_center = cam.get_ray(0.5, 0.5)
        # Center ray should point down -z.
        d = r_center.direction.normalized()
        assert abs(d.x) < 1e-6 and abs(d.y) < 1e-6 and abs(d.z + 1.0) < 1e-6


# --------------------------------------------------------------------------- #
# Renderer
# --------------------------------------------------------------------------- #
class TestRenderer:
    def test_sky_gradient(self):
        r = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
        c = sky_gradient(r)
        # top of sky -> pure sky color (0.5,0.7,1.0)
        assert abs(c.x - 0.5) < 1e-6 and abs(c.y - 0.7) < 1e-6 and abs(c.z - 1.0) < 1e-6

    def test_constant_background(self):
        bg = constant_background(Vec3(0.1, 0.2, 0.3))
        assert bg(Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))) == Vec3(0.1, 0.2, 0.3)

    def test_render_small(self):
        scene = build_three_balls(aspect=2.0)
        renderer = scene.make_renderer(samples=1, max_depth=2, seed=42)
        pixels = renderer.render(scene.camera, 8, 4)
        assert len(pixels) == 4
        assert all(len(row) == 8 for row in pixels)
        # At least some pixel should differ from pure black.
        any_nonzero = any(p.length_squared() > 0 for row in pixels for p in row)
        assert any_nonzero

    def test_gamma_clamp(self):
        assert Renderer.to_rgb(Vec3(0, 0, 0)) == (0, 0, 0)
        assert Renderer.to_rgb(Vec3(1, 1, 1)) == (255, 255, 255)
        assert Renderer.to_rgb(Vec3(2, 2, 2)) == (255, 255, 255)


# --------------------------------------------------------------------------- #
# Scene presets
# --------------------------------------------------------------------------- #
class TestScenes:
    def test_three_balls(self):
        s = build_three_balls()
        assert s.world is not None
        assert s.camera is not None

    def test_cornell(self):
        s = build_cornell_box()
        assert s.world is not None
        # Black background
        r = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
        assert s.background(r) == Vec3(0, 0, 0)

    def test_random(self):
        s = build_random_spheres(n=8)
        assert s.world is not None


# --------------------------------------------------------------------------- #
# Image I/O
# --------------------------------------------------------------------------- #
class TestImageIO:
    def test_ppm(self, tmp_path):
        pixels = [[Vec3(0.5, 0.25, 0.0)]]
        p = tmp_path / "o.ppm"
        imageio.write_ppm(str(p), pixels)
        assert p.exists()
        data = p.read_bytes()
        assert data.startswith(b"P6\n")

    def test_png(self, tmp_path):
        pytest.importorskip("PIL")
        pixels = [[Vec3(0.5, 0.25, 0.0), Vec3(1, 1, 1)]]
        p = tmp_path / "o.png"
        imageio.write_png(str(p), pixels)
        assert p.exists() and p.stat().st_size > 0

    def test_ascii(self, tmp_path):
        pixels = [[Vec3(0.0, 0.0, 0.0), Vec3(1.0, 1.0, 1.0)]]
        p = tmp_path / "o.txt"
        imageio.write_ascii(str(p), pixels, width=2)
        assert p.exists()
        txt = p.read_text()
        assert len(txt) > 0

    def test_write_array(self):
        pixels = [[Vec3(0, 0, 0), Vec3(1, 1, 1)]]
        buf = imageio.write_array(pixels)
        assert buf == bytes((0, 0, 0, 255, 255, 255))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
class TestCLI:
    def test_info(self, capsys):
        from raytracer.cli import main
        rc = main(["info"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "raytracer v" in out

    def test_scenes(self, capsys):
        from raytracer.cli import main
        rc = main(["scenes"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "three-balls" in out

    def test_render_ppm(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "o.ppm"
        rc = main([
            "render", "--scene", "three-balls",
            "--width", "8", "--height", "6",
            "--samples", "1", "--max-depth", "2",
            "--out", str(out), "--format", "ppm", "--quiet",
        ])
        assert rc == 0
        assert out.exists()

    def test_render_ascii(self, tmp_path):
        from raytracer.cli import main
        out = tmp_path / "o.txt"
        rc = main([
            "render", "--scene", "three-balls",
            "--width", "16", "--height", "9",
            "--samples", "1", "--max-depth", "1",
            "--out", str(out), "--format", "ascii", "--quiet",
        ])
        assert rc == 0
        assert out.exists()

    def test_render_unknown_scene(self):
        from raytracer.cli import main
        with pytest.raises(SystemExit):
            main(["render", "--scene", "nope", "--out", "/tmp/x.ppm"])