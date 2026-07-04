"""Tests for force fields."""
import pytest
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.core.fields import UniformField, RadialField, DragField, BuoyancyField


class TestUniformField:
    def test_applies_force(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        w.add_body(b)
        w.add_force_field(UniformField(Vec2(10, 0)))
        w.step(1 / 60)
        assert b.linear_velocity.x > 0

    def test_skips_static(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        w.add_body(b)
        w.add_force_field(UniformField(Vec2(10, 0)))
        w.step(1 / 60)
        assert b.linear_velocity == Vec2(0, 0)


class TestRadialField:
    def test_attracts(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(5, 0), density=1)
        w.add_body(b)
        w.add_force_field(RadialField(Vec2(0, 0), strength=100, falloff=0))
        w.step(1 / 60)
        # Should be pulled toward origin (negative x velocity)
        assert b.linear_velocity.x < 0

    def test_repels(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(5, 0), density=1)
        w.add_body(b)
        w.add_force_field(RadialField(Vec2(0, 0), strength=-100, falloff=0))
        w.step(1 / 60)
        assert b.linear_velocity.x > 0

    def test_max_radius(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(100, 0), density=1)
        w.add_body(b)
        w.add_force_field(RadialField(Vec2(0, 0), strength=100, max_radius=10))
        w.step(1 / 60)
        assert b.linear_velocity == Vec2(0, 0)


class TestDragField:
    def test_drag_opposes_motion(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.linear_velocity = Vec2(10, 0)
        w.add_body(b)
        w.add_force_field(DragField(coefficient=1.0))
        w.step(1 / 60)
        # Drag should decelerate the body
        assert b.linear_velocity.x < 10

    def test_no_drag_on_stationary(self):
        w = World(gravity=Vec2(0, 0))
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        w.add_body(b)
        w.add_force_field(DragField(coefficient=1.0))
        w.step(1 / 60)
        assert b.linear_velocity == Vec2(0, 0)


class TestBuoyancyField:
    def test_floats(self):
        w = World(gravity=Vec2(0, -9.81))
        b = RigidBody(Polygon.box(2, 2), Vec2(0, 0), density=0.5)
        w.add_body(b)
        w.add_force_field(BuoyancyField(fluid_level=0, fluid_density=1.0))
        # Run simulation; body should float, not sink forever
        for _ in range(300):
            w.step(1 / 60)
        # Body should be above some minimum level (buoyancy prevents sinking)
        assert b.position.y > -5