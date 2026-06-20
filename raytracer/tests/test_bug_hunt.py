"""Bug-hunt tests: targeted probes for edge cases and known issues.

Each test below is written to FAIL against the buggy original implementation and
PASS after the fix, serving as a regression test.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from raytracer import (
    Vec3, Ray, Camera, Renderer, Sphere, Plane, Triangle, XYRect,
    Matte, Metal, Dielectric, Emissive, Checker,
    BVHNode, HittableList, AABB, HitRecord,
    build_three_balls, build_cornell_box,
)
from raytracer import material as mat_mod
from raytracer import imageio


# --------------------------------------------------------------------------- #
# Bug A: Dielectric refraction must produce a unit-length transmitted direction.
# The buggy back-face cos_i computation could yield degenerate / NaN results.
# --------------------------------------------------------------------------- #
class TestDielectricRefraction:
    def _make_rec(self, point, normal, ray):
        return HitRecord(1.0, point, normal, Dielectric(1.5), ray)

    def test_refracted_ray_is_unit_length(self):
        """A refracted scattered ray should be unit-length (Ray normalises)."""
        mat_mod.seed(123)
        d = Dielectric(1.5)
        # Front-face hit: ray going down -z, normal +z.
        ray = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = self._make_rec(Vec3(0, 0, -1), Vec3(0, 0, 1), ray)
        result = d.scatter(ray, rec)
        assert result is not None
        _, scattered = result
        assert abs(scattered.direction.length() - 1.0) < 1e-9

    def test_back_face_refraction_valid(self):
        """Ray exiting glass from inside: scattered direction must be valid
        (finite, unit-length), not NaN or zero."""
        mat_mod.seed(7)
        d = Dielectric(1.5)
        # Ray inside glass heading outward at a normal incidence.
        ray = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
        # Geometric outward normal is +y; ray going +y so dot>0 -> back face.
        # HitRecord flips normal to -y (against ray) for front_face=False.
        rec = self._make_rec(Vec3(0, 0, 0), Vec3(0, 1, 0), ray)
        result = d.scatter(ray, rec)
        assert result is not None
        _, scattered = result
        assert math.isfinite(scattered.direction.x)
        assert math.isfinite(scattered.direction.y)
        assert math.isfinite(scattered.direction.z)
        assert abs(scattered.direction.length() - 1.0) < 1e-9

    def test_refraction_at_oblique_angle_back_face(self):
        """Oblique exit ray: must still produce a valid transmitted/reflected dir."""
        mat_mod.seed(42)
        d = Dielectric(1.5)
        # Ray inside heading out at 30 degrees from normal.
        ray = Ray(Vec3(0, 0, 0), Vec3(0.5, math.sqrt(3)/2, 0))
        rec = self._make_rec(Vec3(0, 0, 0), Vec3(0, 1, 0), ray)
        result = d.scatter(ray, rec)
        assert result is not None
        _, scattered = result
        assert abs(scattered.direction.length() - 1.0) < 1e-9


# --------------------------------------------------------------------------- #
# Bug B: render_pixel jitter must stay within the pixel cell, not sample beyond
# the image plane (which causes edge bleed).
# --------------------------------------------------------------------------- #
class TestPixelJitter:
    def test_jitter_within_pixel(self):
        """The rightmost/bottom-most pixel should not sample beyond [0, 1].

        The buggy version used ``s + random()`` which for the last pixel
        (s=1.0) samples at 1.0 + random() > 1.0.
        """
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=4, max_depth=1, seed=5)
        # Spy on camera.get_ray to record sampled (s, t).
        seen_s = []
        seen_t = []
        orig_get_ray = scene.camera.get_ray

        def spy(s, t):
            seen_s.append(s)
            seen_t.append(t)
            return orig_get_ray(s, t)

        scene.camera.get_ray = spy
        r.render_pixel(scene.camera, 1.0, 1.0)  # last pixel
        assert seen_s, "no rays generated"
        # No sample should exceed the [0, 1] image bounds by more than one
        # half-pixel tolerance (the correct jitter is within the pixel cell).
        for s in seen_s:
            assert s <= 1.0 + 1e-9, f"jitter {s} exceeds image plane"
        for t in seen_t:
            assert t <= 1.0 + 1e-9, f"jitter {t} exceeds image plane"


# --------------------------------------------------------------------------- #
# Bug C: Triangle with degenerate (zero-area) vertices must not crash / divide
# by zero when computing its unit normal.
# --------------------------------------------------------------------------- #
class TestDegenerateTriangle:
    def test_zero_area_triangle_does_not_crash_on_bbox(self):
        """All three vertices coincident -> zero-area triangle.  Building it
        must not raise (it should fall back to a default normal)."""
        tri = Triangle(Vec3(1, 1, 1), Vec3(1, 1, 1), Vec3(1, 1, 1))
        # bbox should still be valid.
        b = tri.bbox()
        assert b.mn == Vec3(1 - 1e-5, 1 - 1e-5, 1 - 1e-5)

    def test_zero_area_triangle_hit_returns_none(self):
        tri = Triangle(Vec3(1, 1, 1), Vec3(1, 1, 1), Vec3(1, 1, 1))
        r = Ray(Vec3(0, 0, 0), Vec3(1, 1, 1))
        # Should not crash; either returns None or a valid record.
        rec = tri.hit(r, 0.001, 100)
        assert rec is None  # degenerate triangle cannot be hit


# --------------------------------------------------------------------------- #
# Bug D: AABB.hit with a ray whose origin lies exactly on a slab boundary and
# direction component is zero must not spuriously reject.
# --------------------------------------------------------------------------- #
class TestAABBEdgeCases:
    def test_origin_on_slab_boundary(self):
        """Ray origin exactly at the box's min face, dir parallel to that axis.
        The fix keeps origin==lo from being rejected (it's inside the slab)."""
        box = AABB(Vec3(0, -1, -1), Vec3(2, 1, 1))
        # Ray along +x starting exactly at the x=0 face.
        r = Ray(Vec3(0, 0, 0), Vec3(1, 0, 0))
        assert box.hit(r, 0.0, 100.0)

    def test_zero_dir_outside_slab_rejects(self):
        box = AABB(Vec3(0, 0, 0), Vec3(2, 2, 2))
        # Ray along x with origin y=5 (outside y slab), dir.y == 0.
        r = Ray(Vec3(0, 5, 1), Vec3(1, 0, 0))
        assert not box.hit(r, 0.0, 100.0)


# --------------------------------------------------------------------------- #
# Bug E: Sphere self-intersection / shadow acne — tmin must be respected and a
# ray spawned on a sphere surface should not immediately re-hit that surface.
# This is handled by Ray.tmin default 1e-4; verify it actually works in a render.
# --------------------------------------------------------------------------- #
class TestShadowAcne:
    def test_scattered_ray_does_not_rehit_origin_surface(self):
        """A scattered ray spawned at a hit point must not immediately re-hit
        the surface it came from (shadow acne).  Ray.tmin=1e-4 guards this;
        verify it actually works for the Matte material."""
        mat_mod.seed(3)
        s = Sphere(Vec3(0, 0, -2), 1.0, Matte(Vec3(0.9, 0.1, 0.1)))
        # Primary ray hitting the sphere front.
        ray = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = s.hit(ray, 1e-4, 100)
        assert rec is not None
        result = rec.material.scatter(ray, rec)
        assert result is not None
        _, scattered = result
        # The scattered ray, traced from the hit point, must NOT re-hit the
        # sphere at a tiny t (which would be acne).
        rehit = s.hit(scattered, scattered.tmin, 100.0)
        if rehit is not None:
            # A legitimate second hit would be on the far side (t ~ 2); acne
            # would be t < ~0.01.  Assert no acne-range hit.
            assert rehit.t > 0.01, f"shadow acne: rehit at t={rehit.t}"

    def test_matte_sphere_renders_lit_against_sky(self):
        """A matte sphere against the bright sky should not be pure black —
        scattered rays escape to the sky background and pick up its color."""
        mat_mod.seed(9)
        ball = Sphere(Vec3(0, 0, -2), 1.0, Matte(Vec3(0.9, 0.1, 0.1)))
        world = BVHNode([ball])
        cam = Camera(Vec3(0, 0, 0), Vec3(0, 0, -2), Vec3(0, 1, 0),
                     45, 2.0, aperture=0.0, focus_dist=2)
        from raytracer.renderer import sky_gradient
        r = Renderer(world, background=sky_gradient, samples=4, max_depth=3, seed=9)
        pixels = r.render(cam, 12, 8)
        # The center pixel (the sphere) should be lit (red-tinted sky color),
        # not pure black.
        px = pixels[4][6]
        assert px.length_squared() > 0


# --------------------------------------------------------------------------- #
# Bug F: Renderer with samples=1 in path mode must not double-jitter (the
# original had a leftover buggy line).
# --------------------------------------------------------------------------- #
class TestSingleSampleNoJitter:
    def test_samples1_uses_exact_center(self):
        """With samples=1, no jitter should be applied; the exact (s, t) is
        passed to the camera."""
        scene = build_three_balls(aspect=2.0)
        r = scene.make_renderer(samples=1, max_depth=1, seed=1)
        seen = []
        orig = scene.camera.get_ray
        scene.camera.get_ray = lambda s, t: seen.append((s, t)) or orig(s, t)
        r.render_pixel(scene.camera, 0.25, 0.75)
        assert seen == [(0.25, 0.75)]


# --------------------------------------------------------------------------- #
# Bug G: write_ascii must handle width larger than source image gracefully
# (no division by zero, no index errors).
# --------------------------------------------------------------------------- #
class TestAsciiEdgeCases:
    def test_ascii_empty_image(self, tmp_path):
        imageio.write_ascii(str(tmp_path / "e.txt"), [], width=10)
        assert (tmp_path / "e.txt").exists()

    def test_ascii_wide_width(self, tmp_path):
        pixels = [[Vec3(1, 1, 1)]]
        out = tmp_path / "w.txt"
        imageio.write_ascii(str(out), pixels, width=200)
        assert out.exists()
        text = out.read_text()
        assert len(text) > 0


# --------------------------------------------------------------------------- #
# Bug H: Camera with zero aperture and default focus_dist must focus at the
# look_at point (distance look_from->look_at).
# --------------------------------------------------------------------------- #
class TestCameraFocus:
    def test_default_focus_distance(self):
        cam = Camera(Vec3(0, 0, 0), Vec3(0, 0, -5), Vec3(0, 1, 0),
                     90, 2.0, aperture=0.0)
        assert abs(cam.focus_dist - 5.0) < 1e-9


# --------------------------------------------------------------------------- #
# Bug I: BVH with a single object should still hit (no crash on None child).
# --------------------------------------------------------------------------- #
class TestBVHSingleObject:
    def test_single_object(self):
        s = Sphere(Vec3(0, 0, -2), 0.5)
        bvh = BVHNode([s])
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = bvh.hit(r, 0.001, 100)
        assert rec is not None and abs(rec.t - 1.5) < 1e-6

    def test_two_objects(self):
        a = Sphere(Vec3(0, 0, -2), 0.5)
        b = Sphere(Vec3(0, 0, -4), 0.5)
        bvh = BVHNode([a, b])
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = bvh.hit(r, 0.001, 100)
        assert rec is not None and abs(rec.t - 1.5) < 1e-6


# --------------------------------------------------------------------------- #
# Bug J: XYRect.hit must not divide by zero when the ray is parallel to the
# rectangle (direction.z == 0).  This previously crashed with ZeroDivisionError.
# --------------------------------------------------------------------------- #
class TestXYRectParallelRay:
    def test_parallel_ray_returns_none(self):
        rect = XYRect(-1, 1, -1, 1, -5)
        # Ray travelling in the XY plane (dir.z == 0), parallel to the rect.
        r = Ray(Vec3(0, 0, 0), Vec3(1, 0, 0))
        # Must return None, not raise.
        assert rect.hit(r, 0.001, 100) is None

    def test_parallel_ray_in_bvh_does_not_crash(self):
        rect = XYRect(-1, 1, -1, 1, -5)
        bvh = BVHNode([rect])
        r = Ray(Vec3(0, 0, 0), Vec3(1, 0, 0))
        assert bvh.hit(r, 0.001, 100) is None

    def test_normal_hit_still_works(self):
        rect = XYRect(-1, 1, -1, 1, -5)
        r = Ray(Vec3(0, 0, 0), Vec3(0, 0, -1))
        rec = rect.hit(r, 0.001, 100)
        assert rec is not None and abs(rec.t - 5.0) < 1e-9