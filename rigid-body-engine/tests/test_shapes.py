"""Tests for collision shapes."""
import math
import pytest
from rigidbody.core.shapes import Circle, Polygon, AABB
from rigidbody.core.vec2 import Vec2


class TestCircle:
    def test_mass(self):
        c = Circle(2.0)
        mass, inertia = c.compute_mass(1.0)
        assert abs(mass - math.pi * 4) < 1e-6
        assert abs(inertia - 0.5 * mass * 4) < 1e-6

    def test_offset_mass(self):
        c = Circle(1.0, offset=Vec2(3, 0))
        mass, inertia = c.compute_mass(1.0)
        # I = 0.5 m r^2 + m d^2
        expected = 0.5 * mass * 1.0 + mass * 9.0
        assert abs(inertia - expected) < 1e-6

    def test_invalid_radius(self):
        with pytest.raises(ValueError):
            Circle(0)
        with pytest.raises(ValueError):
            Circle(-1)

    def test_aabb(self):
        c = Circle(1.0)
        aabb = c.compute_aabb(Vec2(5, 5), 0.0)
        assert aabb.min == Vec2(4, 4)
        assert aabb.max == Vec2(6, 6)


class TestPolygon:
    def test_box(self):
        box = Polygon.box(4, 6)
        assert len(box.vertices) == 4
        mass, inertia = box.compute_mass(1.0)
        assert abs(mass - 24.0) < 1e-6

    def test_invalid_box(self):
        with pytest.raises(ValueError):
            Polygon.box(0, 1)
        with pytest.raises(ValueError):
            Polygon.box(-1, 1)

    def test_regular_polygon(self):
        p = Polygon.regular_polygon(6, 2.0)
        assert len(p.vertices) == 6
        assert len(p.normals) == 6

    def test_invalid_polygon(self):
        with pytest.raises(ValueError):
            Polygon([Vec2(0, 0), Vec2(1, 1)])

    def test_convexity_check(self):
        with pytest.raises(ValueError):
            # Concave polygon: vertices zig-zag
            Polygon([Vec2(0, 0), Vec2(2, 2), Vec2(0, 2), Vec2(2, 4)])

    def test_centroid_recentre(self):
        # box at origin already; recentring should be a no-op
        box = Polygon.box(2, 2)
        cx = sum(v.x for v in box.vertices) / 4
        cy = sum(v.y for v in box.vertices) / 4
        assert abs(cx) < 1e-9 and abs(cy) < 1e-9

    def test_aabb(self):
        box = Polygon.box(2, 4)
        aabb = box.compute_aabb(Vec2(0, 0), 0.0)
        assert aabb.min == Vec2(-1, -2)
        assert aabb.max == Vec2(1, 2)


class TestAABB:
    def test_overlaps(self):
        a = AABB(Vec2(0, 0), Vec2(2, 2))
        b = AABB(Vec2(1, 1), Vec2(3, 3))
        assert a.overlaps(b)
        c = AABB(Vec2(5, 5), Vec2(6, 6))
        assert not a.overlaps(c)

    def test_contains(self):
        a = AABB(Vec2(0, 0), Vec2(4, 4))
        assert a.contains(Vec2(2, 2))
        assert not a.contains(Vec2(5, 5))

    def test_combine(self):
        a = AABB(Vec2(0, 0), Vec2(2, 2))
        b = AABB(Vec2(1, 1), Vec2(5, 5))
        c = a.combine(b)
        assert c.min == Vec2(0, 0)
        assert c.max == Vec2(5, 5)

    def test_width_height_center(self):
        a = AABB(Vec2(0, 0), Vec2(4, 6))
        assert a.width == 4
        assert a.height == 6
        assert a.center == Vec2(2, 3)

    def test_surface_area(self):
        a = AABB(Vec2(0, 0), Vec2(3, 4))
        assert a.surface_area() == 14.0