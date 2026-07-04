"""Tests for joints: distance, revolute, weld, prismatic."""
import pytest
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.joints import DistanceJoint, RevoluteJoint, WeldJoint, PrismaticJoint


class TestDistanceJoint:
    def test_construction(self):
        a = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Circle(1), Vec2(2, 0), density=1)
        j = DistanceJoint(a, Vec2.zero(), b, Vec2.zero(), length=2.0)
        assert j.length == 2.0
        assert j.stiffness == 1.0

    def test_auto_length(self):
        a = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Circle(1), Vec2(3, 0), density=1)
        j = DistanceJoint(a, Vec2.zero(), b, Vec2.zero())
        assert j.length == pytest.approx(3.0)

    def test_maintains_distance(self):
        w = World(gravity=Vec2(0, -9.81), velocity_iterations=20, joint_iterations=20)
        a = RigidBody(Circle(0.5), Vec2(0, 10), body_type=RigidBody.STATIC)
        b = RigidBody(Circle(0.5), Vec2(0, 7), density=1)
        w.add_body(a)
        w.add_body(b)
        w.add_joint(DistanceJoint(a, Vec2.zero(), b, Vec2.zero(), length=3.0, stiffness=1.0))
        for _ in range(300):
            w.step(1 / 60)
        dist = (b.position - a.position).length()
        # The distance joint constrains the bob — it shouldn't fall freely
        assert dist < 10.0  # should be much less than free-fall distance


class TestRevoluteJoint:
    def test_pendulum(self):
        w = World(gravity=Vec2(0, -9.81), joint_iterations=20)
        pivot = RigidBody(Polygon.box(0.4, 0.4), Vec2(0, 10), body_type=RigidBody.STATIC)
        bob = RigidBody(Circle(0.5), Vec2(0, 7), density=5)
        w.add_body(pivot)
        w.add_body(bob)
        w.add_joint(RevoluteJoint(pivot, Vec2.zero(), bob, Vec2(0, 3)))
        for _ in range(300):
            w.step(1 / 60)
        # Bob should have moved from its initial position
        assert abs(bob.position.x) > 0.01 or abs(bob.position.y - 7) > 0.01

    def test_motor(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Polygon.box(1, 1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Polygon.box(1, 1), Vec2(2, 0), density=1)
        w.add_body(a)
        w.add_body(b)
        w.add_joint(RevoluteJoint(a, Vec2(2, 0), b, Vec2(0, 0),
                                   motor_enabled=True, motor_speed=5.0,
                                   max_motor_force=100))
        for _ in range(60):
            w.step(1 / 60)
        # Motor should have spun body b
        assert abs(b.angular_velocity) > 0.1


class TestPrismaticJoint:
    def test_construction(self):
        a = RigidBody(Polygon.box(1, 1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Polygon.box(1, 1), Vec2(1, 0), density=1)
        j = PrismaticJoint(a, Vec2.zero(), b, Vec2.zero(), axis=Vec2(1, 0))
        assert j.local_axis is not None

    def test_motor_slides(self):
        w = World(gravity=Vec2(0, 0))
        a = RigidBody(Polygon.box(0.5, 0.5), Vec2(0, 0), body_type=RigidBody.STATIC)
        b = RigidBody(Polygon.box(0.5, 0.5), Vec2(1, 0), density=1)
        w.add_body(a)
        w.add_body(b)
        w.add_joint(PrismaticJoint(a, Vec2.zero(), b, Vec2.zero(),
                                    axis=Vec2(1, 0),
                                    motor_enabled=True, motor_speed=3.0,
                                    max_motor_force=50))
        initial_dist = (b.position - a.position).length()
        for _ in range(120):
            w.step(1 / 60)
        final_dist = (b.position - a.position).length()
        # Body b should have slid along the x axis
        assert final_dist != pytest.approx(initial_dist, abs=0.01)