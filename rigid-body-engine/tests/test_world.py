"""Tests for the world: integration, collision response, sleeping."""
import pytest
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.joints import RevoluteJoint, DistanceJoint, PrismaticJoint


class TestWorldSetup:
    def test_default_gravity(self):
        w = World()
        assert w.gravity == Vec2(0, -9.81)

    def test_add_body(self):
        w = World()
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        idx = w.add_body(b)
        assert idx == 0
        assert len(w.bodies) == 1

    def test_add_joint(self):
        w = World()
        a = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Circle(1), Vec2(2, 0), density=1)
        w.add_body(a)
        w.add_body(b)
        w.add_joint(DistanceJoint(a, Vec2.zero(), b, Vec2.zero(), length=2))
        assert len(w.joints) == 1

    def test_invalid_iterations(self):
        with pytest.raises(ValueError):
            World(velocity_iterations=0)
        with pytest.raises(ValueError):
            World(joint_iterations=0)


class TestSimulationBasics:
    def test_box_rests_on_floor(self):
        w = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), density=1)
        w.add_body(floor)
        w.add_body(box)
        for _ in range(300):
            w.step(1 / 60)
        # Box should rest near y=0.5 (floor top at 0, box half-height 0.5)
        assert 0.4 < box.position.y < 0.6

    def test_circle_bounces(self):
        w = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC,
                          restitution=1.0)
        ball = RigidBody(Circle(0.5), Vec2(0, 5), density=1, restitution=1.0)
        w.add_body(floor)
        w.add_body(ball)
        for _ in range(120):
            w.step(1 / 60)
        # Ball should have bounced back up (positive y velocity at some point)
        # After 2 seconds with e=1, energy is conserved
        assert ball.position.y > 0

    def test_step_zero_dt(self):
        w = World()
        b = RigidBody(Circle(1), Vec2(0, 5), density=1)
        w.add_body(b)
        pos_before = b.position
        w.step(0)
        assert b.position == pos_before

    def test_step_negative_dt(self):
        w = World()
        b = RigidBody(Circle(1), Vec2(0, 5), density=1)
        w.add_body(b)
        pos_before = b.position
        w.step(-0.1)
        assert b.position == pos_before


class TestCollisionFiltering:
    def test_layer_filter(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Circle(1), Vec2(0, 0), density=1)
        a.collision_layer = 0x01
        a.collision_mask = 0x02
        b = RigidBody(Circle(1), Vec2(0.5, 0), density=1)
        b.collision_layer = 0x02
        b.collision_mask = 0x01
        w.add_body(a)
        w.add_body(b)
        # a sees b (mask 0x02 & layer 0x02 = ok); b sees a (mask 0x01 & layer 0x01 = ok)
        collisions = []
        w.on_collision = lambda ia, ib, m: collisions.append((ia, ib))
        w.step(1 / 60)
        assert len(collisions) > 0

    def test_no_collision_when_filtered(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Circle(1), Vec2(0, 0), density=1)
        a.collision_layer = 0x01
        a.collision_mask = 0x01  # only collides with layer 1
        b = RigidBody(Circle(1), Vec2(0.5, 0), density=1)
        b.collision_layer = 0x02  # on layer 2
        b.collision_mask = 0x02
        w.add_body(a)
        w.add_body(b)
        collisions = []
        w.on_collision = lambda ia, ib, m: collisions.append((ia, ib))
        w.step(1 / 60)
        assert len(collisions) == 0


class TestSleeping:
    def test_body_sleeps(self):
        w = World(gravity=Vec2(0, -9.81), allow_sleeping=True)
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), density=1)
        w.add_body(floor)
        w.add_body(box)
        for _ in range(300):
            w.step(1 / 60)
        assert box.sleeping

    def test_no_sleeping_when_disabled(self):
        w = World(gravity=Vec2(0, -9.81), allow_sleeping=False)
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), density=1)
        w.add_body(floor)
        w.add_body(box)
        for _ in range(300):
            w.step(1 / 60)
        assert not box.sleeping


class TestSpatialQueries:
    def test_bodies_at_point(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Circle(2), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Polygon.box(2, 2), Vec2(5, 0), body_type=RigidBody.STATIC)
        w.add_body(a)
        w.add_body(b)
        w.step(1 / 60)
        hits = w.bodies_at(Vec2(0, 0))
        assert 0 in hits
        assert 1 not in hits
        hits2 = w.bodies_at(Vec2(5, 0))
        assert 1 in hits2

    def test_bodies_in_aabb(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Circle(1), Vec2(10, 0), body_type=RigidBody.STATIC)
        w.add_body(a)
        w.add_body(b)
        w.step(1 / 60)
        result = w.bodies_in_aabb(Vec2(-5, -5), Vec2(5, 5))
        assert 0 in result
        assert 1 not in result

    def test_ray_cast(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Circle(1), Vec2(5, 0), body_type=RigidBody.STATIC)
        w.add_body(a)
        w.step(1 / 60)
        hit = w.ray_cast(Vec2(0, 0), Vec2(1, 0))
        assert hit is not None
        assert hit.body_index == 0
        assert hit.point.x > 0

    def test_ray_cast_miss(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Circle(1), Vec2(5, 0), body_type=RigidBody.STATIC)
        w.add_body(a)
        w.step(1 / 60)
        hit = w.ray_cast(Vec2(0, 10), Vec2(0, 1))
        assert hit is None