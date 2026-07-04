"""Tests for collision detection: circles, polygons, circle-polygon."""
import math
import pytest
from rigidbody.core.collision import collide, point_in_polygon, Manifold
from rigidbody.core.shapes import Circle, Polygon
from rigidbody.core.vec2 import Vec2


class TestCircleCircle:
    def test_overlap(self):
        a = Circle(1.0)
        b = Circle(1.0)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(1.5, 0), 0)
        assert m is not None
        assert m.contact_count == 1
        assert m.penetration == pytest.approx(0.5)
        # Normal points A→B = (1,0)
        assert m.normal.almost_eq(Vec2(1, 0))

    def test_no_overlap(self):
        a = Circle(1.0)
        b = Circle(1.0)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(3, 0), 0)
        assert m is None

    def test_coincident(self):
        a = Circle(1.0)
        b = Circle(1.0)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(0, 0), 0)
        assert m is not None
        assert m.penetration == pytest.approx(2.0)


class TestPolygonPolygon:
    def test_box_on_box(self):
        a = Polygon.box(2, 2)
        b = Polygon.box(2, 2)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(1.5, 0), 0)
        assert m is not None
        assert m.penetration == pytest.approx(0.5)

    def test_separated(self):
        a = Polygon.box(2, 2)
        b = Polygon.box(2, 2)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(5, 0), 0)
        assert m is None

    def test_rotated_overlap(self):
        a = Polygon.box(2, 2)
        b = Polygon.box(2, 2)
        m = collide(a, b, Vec2(0, 0), 0.3, Vec2(1.0, 0.5), -0.2)
        assert m is not None

    def test_normal_direction(self):
        # B above A → normal should point up (+y)
        a = Polygon.box(4, 1)
        b = Polygon.box(2, 1)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(0, 0.8), 0)
        assert m is not None
        assert m.normal.y > 0


class TestCirclePolygon:
    def test_circle_above_box(self):
        c = Circle(0.5)
        p = Polygon.box(4, 1)
        m = collide(c, p, Vec2(0, 0.7), 0, Vec2(0, 0), 0)
        assert m is not None
        assert m.penetration > 0

    def test_circle_miss(self):
        c = Circle(0.5)
        p = Polygon.box(1, 1)
        m = collide(c, p, Vec2(0, 5), 0, Vec2(0, 0), 0)
        assert m is None

    def test_circle_inside_polygon(self):
        c = Circle(0.1)
        p = Polygon.box(4, 4)
        m = collide(c, p, Vec2(0, 0), 0, Vec2(0, 0), 0)
        assert m is not None
        # Inside → penetration = radius + distance to edge
        assert m.penetration > 0


class TestPointInPolygon:
    def test_inside(self):
        p = Polygon.box(4, 4)
        assert point_in_polygon(Vec2(0, 0), p, Vec2(0, 0), 0)

    def test_outside(self):
        p = Polygon.box(4, 4)
        assert not point_in_polygon(Vec2(5, 0), p, Vec2(0, 0), 0)

    def test_rotated(self):
        p = Polygon.box(4, 2)
        # Rotate 90° → box is now 2 wide, 4 tall
        assert point_in_polygon(Vec2(0, 1.5), p, Vec2(0, 0), math.pi / 2)
        assert not point_in_polygon(Vec2(1.5, 0), p, Vec2(0, 0), math.pi / 2)