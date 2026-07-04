"""Tests for serialization (JSON and YAML)."""
import json
import os
import tempfile
import pytest
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.joints import RevoluteJoint
from rigidbody.serialize import (
    world_to_dict, world_from_dict,
    world_to_json, world_from_json,
    body_to_dict, body_from_dict,
)


class TestBodySerialization:
    def test_round_trip(self):
        b = RigidBody(Circle(2), Vec2(3, 4), angle=0.5, density=2,
                      restitution=0.7, friction=0.4)
        b.user_data = "test_body"
        d = body_to_dict(b)
        b2 = body_from_dict(d)
        assert b2.position == b.position
        assert b2.angle == b.angle
        assert b2.restitution == b.restitution
        assert b2.friction == b.friction
        assert b2.user_data == "test_body"

    def test_static_body(self):
        b = RigidBody(Polygon.box(4, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        d = body_to_dict(b)
        b2 = body_from_dict(d)
        assert b2.is_static


class TestWorldSerialization:
    def _build_world(self):
        w = World(gravity=Vec2(0, -10), velocity_iterations=8)
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), density=2, restitution=0.3)
        box.user_data = "box0"
        w.add_body(floor)
        w.add_body(box)
        return w

    def test_round_trip_dict(self):
        w = self._build_world()
        d = world_to_dict(w)
        w2 = world_from_dict(d)
        assert len(w2.bodies) == 2
        assert w2.gravity == w.gravity
        assert w2.bodies[1].position == w.bodies[1].position

    def test_round_trip_json(self):
        w = self._build_world()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            path = f.name
        try:
            world_to_json(w, path)
            w2 = world_from_json(path)
            assert len(w2.bodies) == 2
            assert w2.bodies[1].user_data == "box0"
        finally:
            os.unlink(path)

    def test_yaml_round_trip(self):
        pytest.importorskip("yaml")
        from rigidbody.serialize import world_to_yaml, world_from_yaml
        w = self._build_world()
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            path = f.name
        try:
            world_to_yaml(w, path)
            w2 = world_from_yaml(path)
            assert len(w2.bodies) == 2
            assert w2.bodies[1].position == w.bodies[1].position
        finally:
            os.unlink(path)


class TestForceFieldSerialization:
    def test_world_with_fields(self):
        from rigidbody.core.fields import UniformField
        w = World(gravity=Vec2(0, -9.81))
        w.add_force_field(UniformField(Vec2(5, 0)))
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), density=1)
        w.add_body(box)
        d = world_to_dict(w)
        w2 = world_from_dict(d)
        # Note: force fields are not serialized by the current format,
        # but the world should still load without error.
        assert len(w2.bodies) == 1