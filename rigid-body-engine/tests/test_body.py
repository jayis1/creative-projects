"""Tests for the rigid body class."""
import pytest
from rigidbody.core.body import RigidBody
from rigidbody.core.shapes import Circle, Polygon
from rigidbody.core.vec2 import Vec2


class TestRigidBodyConstruction:
    def test_dynamic(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=2.0)
        assert b.is_dynamic
        assert b.mass > 0
        assert b.inv_mass > 0
        assert b.inertia > 0

    def test_static(self):
        b = RigidBody(Polygon.box(1, 1), Vec2(0, 0), body_type=RigidBody.STATIC)
        assert b.is_static
        assert b.mass == 0
        assert b.inv_mass == 0

    def test_kinematic(self):
        b = RigidBody(Polygon.box(1, 1), Vec2(0, 0), body_type=RigidBody.KINEMATIC)
        assert b.is_kinematic
        assert b.inv_mass == 0

    def test_invalid_density(self):
        with pytest.raises(ValueError):
            RigidBody(Circle(1), Vec2(0, 0), density=0)
        with pytest.raises(ValueError):
            RigidBody(Circle(1), Vec2(0, 0), density=-1)

    def test_restitution_clamped(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1, restitution=5)
        assert b.restitution == 1.0
        b2 = RigidBody(Circle(1), Vec2(0, 0), density=1, restitution=-1)
        assert b2.restitution == 0.0

    def test_friction_non_negative(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1, friction=-1)
        assert b.friction == 0.0


class TestCoordinateTransform:
    def test_to_world(self):
        b = RigidBody(Circle(1), Vec2(5, 5), angle=0.0, density=1)
        assert b.to_world(Vec2(0, 0)) == Vec2(5, 5)
        assert b.to_world(Vec2(1, 0)) == Vec2(6, 5)

    def test_to_local(self):
        b = RigidBody(Circle(1), Vec2(5, 5), angle=0.0, density=1)
        assert b.to_local(Vec2(5, 5)) == Vec2(0, 0)
        assert b.to_local(Vec2(6, 5)) == Vec2(1, 0)

    def test_round_trip(self):
        b = RigidBody(Circle(1), Vec2(3, 4), angle=0.5, density=1)
        p = Vec2(1.5, -2.3)
        wp = b.to_world(p)
        lp = b.to_local(wp)
        assert lp.almost_eq(p)


class TestForces:
    def test_apply_force(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.apply_force(Vec2(10, 0))
        assert b.force == Vec2(10, 0)

    def test_apply_force_with_torque(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.apply_force(Vec2(0, 10), Vec2(1, 0))
        assert b.force == Vec2(0, 10)
        # r.cross(F) where r=(1,0), F=(0,10): 1*10 - 0*0 = 10
        assert b.torque == pytest.approx(10)

    def test_static_ignores_force(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b.apply_force(Vec2(10, 0))
        assert b.force == Vec2(0, 0)

    def test_apply_impulse(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.apply_impulse(Vec2(10, 0))
        assert b.linear_velocity.x > 0

    def test_apply_torque(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.apply_torque(50)
        assert b.torque == 50


class TestIntegration:
    def test_free_fall(self):
        b = RigidBody(Circle(1), Vec2(0, 10), density=1, linear_damping=0)
        b.integrate(Vec2(0, -10), 0.1)
        # v = 0 + (-10)*0.1 = -1
        assert b.linear_velocity.y == pytest.approx(-1.0)
        # x = 10 + (-1)*0.1 = 9.9
        assert b.position.y == pytest.approx(10 - 0.1)

    def test_static_no_motion(self):
        b = RigidBody(Circle(1), Vec2(5, 5), body_type=RigidBody.STATIC)
        b.integrate(Vec2(0, -10), 0.1)
        assert b.position == Vec2(5, 5)

    def test_kinematic_moves(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.KINEMATIC)
        b.linear_velocity = Vec2(2, 0)
        b.integrate(Vec2(0, 0), 1.0)
        assert b.position == Vec2(2, 0)


class TestSleeping:
    def test_set_sleeping(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.set_sleeping()
        assert b.sleeping
        assert b.linear_velocity == Vec2(0, 0)
        assert b.angular_velocity == 0.0

    def test_set_awake(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.set_sleeping()
        b.set_awake()
        assert not b.sleeping

    def test_sleeping_ignores_force(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.set_sleeping()
        b.apply_force(Vec2(10, 0))
        assert b.force == Vec2(0, 0)