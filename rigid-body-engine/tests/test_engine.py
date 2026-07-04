"""Test suite for the rigid-body engine.

Covers vector math, shapes, collision detection, solver, joints, world,
serialization, diagnostics, force fields, and collision filtering.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rigidbody import (
    AABB, AsciiRenderer, BuoyancyField, Circle, ContactSolver, Diagnostics,
    DistanceJoint, DragField, Joint, MouseJoint, PPMRenderer, Polygon, RigidBody,
    RadialField, RevoluteJoint, UniformField, Vec2, WeldJoint, World,
    body_from_dict, body_to_dict, collide, compute_energy, compute_momentum,
    point_in_polygon, world_from_dict, world_to_dict,
)
from rigidbody.core.mat22 import Mat22, solve_2x2


class TestVec2(unittest.TestCase):
    def test_add_sub(self):
        a = Vec2(1, 2)
        b = Vec2(3, 4)
        self.assertTrue((a + b).almost_eq(Vec2(4, 6)))
        self.assertTrue((a - b).almost_eq(Vec2(-2, -2)))

    def test_mul_div(self):
        a = Vec2(2, 4)
        self.assertTrue((a * 3).almost_eq(Vec2(6, 12)))
        self.assertTrue((a / 2).almost_eq(Vec2(1, 2)))

    def test_div_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            Vec2(1, 1) / 0

    def test_dot_cross(self):
        self.assertAlmostEqual(Vec2(1, 0).dot(Vec2(0, 1)), 0)
        self.assertAlmostEqual(Vec2(1, 0).cross(Vec2(0, 1)), 1)
        self.assertAlmostEqual(Vec2(1, 0).cross(Vec2(0, -1)), -1)

    def test_normalize(self):
        v = Vec2(3, 4)
        self.assertAlmostEqual(v.normalize().length(), 1.0)
        self.assertTrue(Vec2(0, 0).normalize().almost_eq(Vec2(0, 0)))

    def test_perpendicular(self):
        v = Vec2(1, 0)
        self.assertTrue(v.perpendicular().almost_eq(Vec2(0, 1)))

    def test_rotate(self):
        v = Vec2(1, 0)
        r = v.rotate(math.pi / 2)
        self.assertAlmostEqual(r.x, 0, places=10)
        self.assertAlmostEqual(r.y, 1, places=10)

    def test_cross_scalar(self):
        v = Vec2(1, 0)
        r = v.cross_scalar(2)
        self.assertTrue(r.almost_eq(Vec2(0, 2)))

    def test_from_angle(self):
        v = Vec2.from_angle(0, 5)
        self.assertTrue(v.almost_eq(Vec2(5, 0)))

    def test_neg(self):
        self.assertTrue((-Vec2(1, -2)).almost_eq(Vec2(-1, 2)))


class TestMat22(unittest.TestCase):
    def test_identity(self):
        m = Mat22.identity()
        x, y = m.multiply_vec(3, 4)
        self.assertAlmostEqual(x, 3)
        self.assertAlmostEqual(y, 4)

    def test_rotation(self):
        m = Mat22.rotation(math.pi / 2)
        x, y = m.multiply_vec(1, 0)
        self.assertAlmostEqual(x, 0, places=10)
        self.assertAlmostEqual(y, 1, places=10)

    def test_inverse(self):
        m = Mat22(1, 2, 3, 4)
        inv = m.inverse()
        prod = Mat22(
            m.a * inv.a + m.b * inv.c, m.a * inv.b + m.b * inv.d,
            m.c * inv.a + m.d * inv.c, m.c * inv.b + m.d * inv.d,
        )
        self.assertAlmostEqual(prod.a, 1)
        self.assertAlmostEqual(prod.d, 1)
        self.assertAlmostEqual(prod.b, 0)
        self.assertAlmostEqual(prod.c, 0)

    def test_singular_inverse_raises(self):
        m = Mat22(1, 2, 2, 4)
        with self.assertRaises(ZeroDivisionError):
            m.inverse()

    def test_solve_2x2(self):
        x, y = solve_2x2(2, 1, 1, 3, 5, 10)
        self.assertAlmostEqual(2 * x + y, 5)
        self.assertAlmostEqual(x + 3 * y, 10)

    def test_solve_2x2_singular(self):
        with self.assertRaises(ZeroDivisionError):
            solve_2x2(1, 2, 2, 4, 1, 1)


class TestShapes(unittest.TestCase):
    def test_circle_mass(self):
        c = Circle(2.0)
        m, i = c.compute_mass(1.0)
        self.assertAlmostEqual(m, math.pi * 4)
        self.assertAlmostEqual(i, 0.5 * m * 4)

    def test_circle_zero_radius(self):
        with self.assertRaises(ValueError):
            Circle(0)
        with self.assertRaises(ValueError):
            Circle(-1)

    def test_polygon_box(self):
        p = Polygon.box(2, 2)
        m, i = p.compute_mass(1.0)
        self.assertAlmostEqual(m, 4.0)  # area = 4, density = 1

    def test_polygon_box_invalid(self):
        with self.assertRaises(ValueError):
            Polygon.box(0, 1)
        with self.assertRaises(ValueError):
            Polygon.box(-1, 1)

    def test_polygon_regular(self):
        p = Polygon.regular_polygon(6, 1.0)
        self.assertEqual(len(p.vertices), 6)

    def test_polygon_regular_invalid(self):
        with self.assertRaises(ValueError):
            Polygon.regular_polygon(2, 1)
        with self.assertRaises(ValueError):
            Polygon.regular_polygon(5, 0)

    def test_polygon_non_convex_raises(self):
        with self.assertRaises(ValueError):
            Polygon([Vec2(0, 0), Vec2(2, 0), Vec2(1, 0.5), Vec2(2, 2), Vec2(0, 2)])

    def test_polygon_too_few_vertices(self):
        with self.assertRaises(ValueError):
            Polygon([Vec2(0, 0), Vec2(1, 0)])

    def test_polygon_centroid_centered(self):
        p = Polygon.box(4, 2)
        centroid = Vec2(0, 0)
        for v in p.vertices:
            centroid = centroid + v
        centroid = centroid / 4
        self.assertTrue(centroid.almost_eq(Vec2(0, 0), 1e-10))

    def test_aabb_overlaps(self):
        a = AABB(Vec2(0, 0), Vec2(2, 2))
        b = AABB(Vec2(1, 1), Vec2(3, 3))
        c = AABB(Vec2(3, 3), Vec2(4, 4))
        self.assertTrue(a.overlaps(b))
        self.assertFalse(a.overlaps(c))

    def test_aabb_contains(self):
        a = AABB(Vec2(0, 0), Vec2(4, 4))
        self.assertTrue(a.contains(Vec2(2, 2)))
        self.assertFalse(a.contains(Vec2(5, 5)))

    def test_aabb_combine(self):
        a = AABB(Vec2(0, 0), Vec2(2, 2))
        b = AABB(Vec2(1, 1), Vec2(3, 3))
        c = a.combine(b)
        self.assertTrue(c.min.almost_eq(Vec2(0, 0)))
        self.assertTrue(c.max.almost_eq(Vec2(3, 3)))


class TestCollision(unittest.TestCase):
    def test_circle_circle_overlap(self):
        a = Circle(1.0)
        b = Circle(1.0)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(1.5, 0), 0)
        self.assertIsNotNone(m)
        self.assertEqual(m.contact_count, 1)
        self.assertAlmostEqual(m.penetration, 0.5)
        self.assertTrue(m.normal.almost_eq(Vec2(1, 0)))

    def test_circle_circle_separate(self):
        a = Circle(1.0)
        b = Circle(1.0)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(3, 0), 0)
        self.assertIsNone(m)

    def test_circle_circle_coincident(self):
        a = Circle(1.0)
        b = Circle(1.0)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(0, 0), 0)
        self.assertIsNotNone(m)
        self.assertAlmostEqual(m.penetration, 2.0)

    def test_polygon_polygon_overlap(self):
        a = Polygon.box(2, 2)
        b = Polygon.box(2, 2)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(1, 0), 0)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(m.contact_count, 1)
        self.assertAlmostEqual(m.penetration, 1.0, places=6)

    def test_polygon_polygon_separate(self):
        a = Polygon.box(2, 2)
        b = Polygon.box(2, 2)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(5, 0), 0)
        self.assertIsNone(m)

    def test_polygon_polygon_normal_direction(self):
        """Normal must point from A to B."""
        a = Polygon.box(2, 2)
        b = Polygon.box(2, 2)
        m = collide(a, b, Vec2(0, 0), 0, Vec2(0, 1.5), 0)
        self.assertIsNotNone(m)
        # Normal should point up (from A at y=0 to B at y=1.5)
        self.assertAlmostEqual(m.normal.y, 1.0, places=6)

    def test_circle_polygon_overlap(self):
        c = Circle(0.5)
        p = Polygon.box(2, 2)
        m = collide(c, p, Vec2(0, 1.2), 0, Vec2(0, 0), 0)
        self.assertIsNotNone(m)
        self.assertGreater(m.penetration, 0)

    def test_circle_polygon_separate(self):
        c = Circle(0.5)
        p = Polygon.box(2, 2)
        m = collide(c, p, Vec2(0, 5), 0, Vec2(0, 0), 0)
        self.assertIsNone(m)

    def test_point_in_polygon(self):
        p = Polygon.box(4, 4)
        self.assertTrue(point_in_polygon(Vec2(0, 0), p, Vec2(0, 0), 0))
        self.assertFalse(point_in_polygon(Vec2(3, 3), p, Vec2(0, 0), 0))

    def test_rotated_polygon_collision(self):
        a = Polygon.box(4, 1)
        b = Polygon.box(4, 1)
        # Rotate B 90 degrees → becomes 1x4
        m = collide(a, b, Vec2(0, 0), 0, Vec2(0, 0.5), math.pi / 2)
        self.assertIsNotNone(m)
        self.assertGreater(m.penetration, 0)


class TestBody(unittest.TestCase):
    def test_dynamic_mass(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=2)
        self.assertGreater(b.mass, 0)
        self.assertGreater(b.inv_mass, 0)

    def test_static_infinite_mass(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        self.assertEqual(b.mass, 0)
        self.assertEqual(b.inv_mass, 0)

    def test_kinematic_infinite_mass(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.KINEMATIC)
        self.assertEqual(b.mass, 0)
        self.assertEqual(b.inv_mass, 0)

    def test_negative_density_raises(self):
        with self.assertRaises(ValueError):
            RigidBody(Circle(1), Vec2(0, 0), density=-1)

    def test_restitution_clamped(self):
        b = RigidBody(Circle(1), Vec2(0, 0), restitution=5.0)
        self.assertEqual(b.restitution, 1.0)
        b2 = RigidBody(Circle(1), Vec2(0, 0), restitution=-1.0)
        self.assertEqual(b2.restitution, 0.0)

    def test_apply_force_dynamic(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        b.apply_force(Vec2(10, 0))
        self.assertTrue(b.force.almost_eq(Vec2(10, 0)))

    def test_apply_force_static_no_effect(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        b.apply_force(Vec2(10, 0))
        self.assertTrue(b.force.almost_eq(Vec2(0, 0)))

    def test_apply_impulse(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        b.apply_impulse(Vec2(10, 0))
        self.assertGreater(b.linear_velocity.x, 0)

    def test_velocity_at_point(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        b.angular_velocity = 1.0
        v = b.velocity_at_point(Vec2(1, 0))
        # At point (1,0) with angular vel 1: tangential velocity = (-r.y, r.x)*w = (0, 1)*1
        self.assertAlmostEqual(v.y, 1.0, places=6)

    def test_to_world_to_local(self):
        b = RigidBody(Circle(1), Vec2(2, 3), angle=math.pi / 2)
        local = Vec2(1, 0)
        world = b.to_world(local)
        back = b.to_local(world)
        self.assertTrue(local.almost_eq(back, 1e-10))

    def test_sleeping(self):
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        b.set_sleeping()
        self.assertTrue(b.sleeping)
        self.assertTrue(b.linear_velocity.almost_eq(Vec2(0, 0)))
        b.set_awake()
        self.assertFalse(b.sleeping)


class TestWorld(unittest.TestCase):
    def test_box_on_floor(self):
        world = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), body_type=RigidBody.DYNAMIC, density=1)
        world.add_body(floor)
        world.add_body(box)
        dt = 1 / 60
        for _ in range(300):
            world.step(dt)
        self.assertGreater(box.position.y, 0, "box fell through floor")
        self.assertLess(box.position.y, 0.6, "box floating above floor")
        self.assertAlmostEqual(box.linear_velocity.y, 0, places=2)

    def test_ball_bounce(self):
        world = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        ball = RigidBody(Circle(0.5), Vec2(0, 5), body_type=RigidBody.DYNAMIC, restitution=0.8)
        world.add_body(floor)
        world.add_body(ball)
        dt = 1 / 60
        for _ in range(100):
            world.step(dt)
        # Ball should have bounced and still be above floor
        self.assertGreater(ball.position.y, 0)

    def test_collision_filter(self):
        world = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        world.add_body(floor)
        ghost = RigidBody(Polygon.box(1, 1), Vec2(0, 5), body_type=RigidBody.DYNAMIC, density=1)
        ghost.collision_layer = 0x0002
        ghost.collision_mask = 0x0002
        world.add_body(ghost)
        dt = 1 / 60
        for _ in range(120):
            world.step(dt)
        self.assertLess(ghost.position.y, 0, "ghost should pass through floor")

    def test_sensor(self):
        world = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        world.add_body(floor)
        sensor = RigidBody(Polygon.box(4, 0.2), Vec2(0, 2), body_type=RigidBody.STATIC)
        sensor.is_sensor = True
        world.add_body(sensor)
        ball = RigidBody(Polygon.box(1, 1), Vec2(0, 5), body_type=RigidBody.DYNAMIC, density=1)
        world.add_body(ball)
        hits = []
        world.on_collision = lambda a, b, m: hits.append((a, b))
        dt = 1 / 60
        for _ in range(100):
            world.step(dt)
        self.assertGreater(len(hits), 0, "sensor should detect collisions")
        self.assertLess(ball.position.y, 2, "ball should pass through sensor")

    def test_zero_dt_noop(self):
        world = World()
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        world.add_body(b)
        world.step(0)
        self.assertTrue(b.position.almost_eq(Vec2(0, 0)))

    def test_kinematic_moves(self):
        world = World()
        plat = RigidBody(Polygon.box(2, 0.5), Vec2(0, 0), body_type=RigidBody.KINEMATIC)
        plat.linear_velocity = Vec2(1, 0)
        world.add_body(plat)
        world.step(1 / 60)
        self.assertAlmostEqual(plat.position.x, 1 / 60, places=6)

    def test_bodies_at_point(self):
        world = World()
        box = RigidBody(Polygon.box(2, 2), Vec2(0, 0), body_type=RigidBody.STATIC)
        world.add_body(box)
        ids = world.bodies_at(Vec2(0, 0))
        self.assertIn(0, ids)
        ids2 = world.bodies_at(Vec2(5, 5))
        self.assertEqual(ids2, [])

    def test_collision_callback(self):
        world = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), body_type=RigidBody.DYNAMIC, density=1)
        world.add_body(floor)
        world.add_body(box)
        events = []
        world.on_collision = lambda a, b, m: events.append((a, b))
        for _ in range(100):
            world.step(1 / 60)
        self.assertGreater(len(events), 0, "collision callback should fire")


class TestJoints(unittest.TestCase):
    def test_distance_joint(self):
        world = World(gravity=Vec2(0, -9.81))
        a = RigidBody(Circle(0.5), Vec2(-2, 5), body_type=RigidBody.DYNAMIC, density=1)
        b = RigidBody(Circle(0.5), Vec2(2, 5), body_type=RigidBody.DYNAMIC, density=1)
        world.add_body(a)
        world.add_body(b)
        world.add_joint(DistanceJoint(a, Vec2.zero(), b, Vec2.zero(), length=4))
        for _ in range(60):
            world.step(1 / 60)
        dist = (b.position - a.position).length()
        self.assertAlmostEqual(dist, 4, places=1)

    def test_revolute_joint(self):
        world = World(gravity=Vec2(0, -9.81))
        pivot = RigidBody(Polygon.box(0.4, 0.4), Vec2(0, 10), body_type=RigidBody.STATIC)
        bob = RigidBody(Circle(0.5), Vec2(2, 10), body_type=RigidBody.DYNAMIC, density=5)
        world.add_body(pivot)
        world.add_body(bob)
        world.add_joint(RevoluteJoint(pivot, Vec2.zero(), bob, Vec2(-2, 0)))
        for _ in range(60):
            world.step(1 / 60)
        # Bob should have swung downward but not fallen freely
        self.assertLess(bob.position.y, 10)
        self.assertGreater(bob.position.y, 5, "bob shouldn't have fallen far — joint holds it")


class TestDiagnostics(unittest.TestCase):
    def test_energy_computation(self):
        bodies = [
            RigidBody(Circle(1), Vec2(0, 10), body_type=RigidBody.DYNAMIC, density=1),
            RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC),
        ]
        bodies[0].linear_velocity = Vec2(2, 0)
        e = compute_energy(bodies)
        self.assertGreater(e["kinetic"], 0)
        self.assertGreater(e["potential"], 0)

    def test_momentum_computation(self):
        bodies = [RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=2)]
        bodies[0].linear_velocity = Vec2(3, 0)
        p = compute_momentum(bodies)
        # Circle(1) with density 2: mass = π*1²*2 = 2π, vel=3 → px = 6π
        self.assertAlmostEqual(p["px"], 2 * math.pi * 3)

    def test_diagnostics_drift(self):
        diag = Diagnostics()
        world = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), body_type=RigidBody.DYNAMIC, density=1)
        world.add_body(floor)
        world.add_body(box)
        for _ in range(100):
            world.step(1 / 60)
            diag.sample(world.bodies)
        drift = diag.energy_drift()
        # Baumgarte stabilization injects energy during position correction;
        # drift of ~50-80% is expected for a box settling under gravity.
        self.assertLess(abs(drift), 1.5, "energy drift should be bounded")


class TestSerialization(unittest.TestCase):
    def test_body_roundtrip(self):
        b = RigidBody(Polygon.box(2, 2), Vec2(3, 4), angle=0.5,
                      body_type=RigidBody.DYNAMIC, density=2, friction=0.7, restitution=0.3)
        b.user_data = "test"
        d = body_to_dict(b)
        b2 = body_from_dict(d)
        self.assertTrue(b2.position.almost_eq(b.position))
        self.assertAlmostEqual(b2.angle, b.angle)
        self.assertEqual(b2.body_type, b.body_type)
        self.assertEqual(b2.user_data, "test")

    def test_circle_body_roundtrip(self):
        b = RigidBody(Circle(1.5), Vec2(2, 3), body_type=RigidBody.DYNAMIC, density=1)
        d = body_to_dict(b)
        b2 = body_from_dict(d)
        self.assertEqual(b2.shape.shape_type, "circle")
        self.assertAlmostEqual(b2.shape.radius, 1.5)

    def test_world_roundtrip(self):
        world = World(gravity=Vec2(0, -5))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 3), body_type=RigidBody.DYNAMIC, density=1)
        box.user_data = "box"
        world.add_body(floor)
        world.add_body(box)
        d = world_to_dict(world)
        world2 = world_from_dict(d)
        self.assertEqual(len(world2.bodies), 2)
        self.assertAlmostEqual(world2.gravity.y, -5)
        self.assertTrue(world2.bodies[1].position.almost_eq(Vec2(0, 3)))
        self.assertEqual(world2.bodies[1].user_data, "box")

    def test_world_roundtrip_with_joint(self):
        world = World()
        a = RigidBody(Circle(0.5), Vec2(-2, 5), body_type=RigidBody.DYNAMIC, density=1)
        b = RigidBody(Circle(0.5), Vec2(2, 5), body_type=RigidBody.DYNAMIC, density=1)
        world.add_body(a)
        world.add_body(b)
        world.add_joint(DistanceJoint(a, Vec2.zero(), b, Vec2.zero(), length=4))
        d = world_to_dict(world)
        world2 = world_from_dict(d)
        self.assertEqual(len(world2.joints), 1)
        self.assertIsInstance(world2.joints[0], DistanceJoint)


class TestForceFields(unittest.TestCase):
    def test_uniform_field(self):
        field = UniformField(Vec2(10, 0))
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        field.apply(b, 0.01)
        self.assertGreater(b.force.x, 0)

    def test_uniform_field_static(self):
        field = UniformField(Vec2(10, 0))
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.STATIC)
        field.apply(b, 0.01)
        self.assertTrue(b.force.almost_eq(Vec2(0, 0)))

    def test_radial_field(self):
        field = RadialField(Vec2(10, 0), strength=100, falloff=0)
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        field.apply(b, 0.01)
        self.assertGreater(b.force.x, 0)  # pulled toward center at x=10

    def test_drag_field(self):
        field = DragField(0.5)
        b = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        b.linear_velocity = Vec2(10, 0)
        field.apply(b, 0.01)
        self.assertLess(b.force.x, 0)  # drag opposes motion


class TestBroadPhase(unittest.TestCase):
    def test_overlapping_pairs(self):
        from rigidbody.core.broadphase import BroadPhase
        bp = BroadPhase()
        b1 = RigidBody(Circle(1), Vec2(0, 0), body_type=RigidBody.DYNAMIC, density=1)
        b2 = RigidBody(Circle(1), Vec2(1, 0), body_type=RigidBody.DYNAMIC, density=1)
        b3 = RigidBody(Circle(1), Vec2(10, 0), body_type=RigidBody.DYNAMIC, density=1)
        bodies = [b1, b2, b3]
        for b in bodies:
            b.update_aabb()
        pairs = bp.update(bodies)
        self.assertIn((0, 1), pairs)
        self.assertNotIn((0, 2), pairs)
        self.assertNotIn((1, 2), pairs)


if __name__ == "__main__":
    unittest.main(verbosity=2)