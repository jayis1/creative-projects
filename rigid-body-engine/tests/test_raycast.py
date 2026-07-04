"""Tests for the ray casting module."""
import pytest
from rigidbody import World, RigidBody, Vec2, Circle, Polygon
from rigidbody.raycast import ray_cast, ray_cast_body


class TestRayVsCircle:
    def test_hit(self):
        body = RigidBody(Circle(1), Vec2(5, 0), body_type=RigidBody.STATIC)
        body.update_aabb()
        frac = ray_cast_body(body, Vec2(0, 0), Vec2(1, 0), 100)
        assert frac is not None
        assert frac > 0

    def test_miss(self):
        body = RigidBody(Circle(1), Vec2(5, 5), body_type=RigidBody.STATIC)
        body.update_aabb()
        frac = ray_cast_body(body, Vec2(0, 0), Vec2(1, 0), 100)
        assert frac is None

    def test_origin_inside(self):
        body = RigidBody(Circle(2), Vec2(0, 0), body_type=RigidBody.STATIC)
        body.update_aabb()
        frac = ray_cast_body(body, Vec2(0, 0), Vec2(1, 0), 100)
        assert frac == 0.0

    def test_pointing_away(self):
        body = RigidBody(Circle(1), Vec2(5, 0), body_type=RigidBody.STATIC)
        body.update_aabb()
        frac = ray_cast_body(body, Vec2(0, 0), Vec2(-1, 0), 100)
        assert frac is None


class TestRayVsPolygon:
    def test_hit(self):
        body = RigidBody(Polygon.box(2, 2), Vec2(5, 0), body_type=RigidBody.STATIC)
        body.update_aabb()
        frac = ray_cast_body(body, Vec2(0, 0), Vec2(1, 0), 100)
        assert frac is not None
        assert frac > 0

    def test_miss(self):
        body = RigidBody(Polygon.box(2, 2), Vec2(5, 10), body_type=RigidBody.STATIC)
        body.update_aabb()
        frac = ray_cast_body(body, Vec2(0, 0), Vec2(1, 0), 100)
        assert frac is None


class TestRayCastWorld:
    def test_closest_hit(self):
        bodies = [
            RigidBody(Circle(1), Vec2(3, 0), body_type=RigidBody.STATIC),
            RigidBody(Circle(1), Vec2(8, 0), body_type=RigidBody.STATIC),
        ]
        for b in bodies:
            b.update_aabb()
        hit = ray_cast(bodies, Vec2(0, 0), Vec2(1, 0))
        assert hit is not None
        assert hit.body_index == 0  # closer one

    def test_ignore_set(self):
        bodies = [
            RigidBody(Circle(1), Vec2(3, 0), body_type=RigidBody.STATIC),
            RigidBody(Circle(1), Vec2(8, 0), body_type=RigidBody.STATIC),
        ]
        for b in bodies:
            b.update_aabb()
        hit = ray_cast(bodies, Vec2(0, 0), Vec2(1, 0), ignore={0})
        assert hit is not None
        assert hit.body_index == 1

    def test_via_world(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(5, 0), body_type=RigidBody.STATIC)
        w.add_body(b)
        w.step(1 / 60)
        hit = w.ray_cast(Vec2(0, 0), Vec2(1, 0))
        assert hit is not None
        assert hit.body_index == 0

    def test_zero_direction(self):
        bodies = [RigidBody(Circle(1), Vec2(3, 0), body_type=RigidBody.STATIC)]
        bodies[0].update_aabb()
        hit = ray_cast(bodies, Vec2(0, 0), Vec2(0, 0))
        assert hit is None