"""Tests for the Boid class — steering behaviors, species, path following."""

import math
import pytest
from boids.boid import Boid, BoidState
from boids.vector import Vector2


class TestBoidCreation:
    def test_default_creation(self):
        b = Boid(10, 20)
        assert b.pos.x == 10 and b.pos.y == 20
        assert b.vel.x == 0 and b.vel.y == 0
        assert b.max_speed == 4.0
        assert b.max_force == 0.2
        assert b.radius == 3.0
        assert b.kind == "boid"
        assert b.species == 0

    def test_with_velocity(self):
        b = Boid(0, 0, vx=3, vy=4)
        assert b.vel.x == 3 and b.vel.y == 4

    def test_with_species(self):
        b = Boid(0, 0, species=2)
        assert b.species == 2

    def test_unique_ids(self):
        b1 = Boid(0, 0)
        b2 = Boid(0, 0)
        assert b1.id != b2.id
        assert b2.id == b1.id + 1

    def test_trail_disabled_by_default(self):
        b = Boid(0, 0)
        assert b.trail is None

    def test_trail_enabled(self):
        b = Boid(0, 0, trail_length=10)
        assert b.trail is not None
        assert b.trail.maxlen == 10


class TestSeparation:
    def test_no_neighbors(self):
        b = Boid(50, 50)
        force = b.separation([], 30)
        assert force.x == 0 and force.y == 0

    def test_one_neighbor(self):
        b = Boid(50, 50, vx=1, vy=0)
        other = Boid(55, 50, vx=1, vy=0)
        force = b.separation([other], 30)
        # Should push away (negative x direction)
        assert force.x < 0

    def test_self_ignored(self):
        b = Boid(50, 50)
        force = b.separation([b], 30)
        assert force.x == 0 and force.y == 0

    def test_predator_ignored(self):
        b = Boid(50, 50)
        pred = Boid(55, 50, kind="predator")
        force = b.separation([pred], 30)
        assert force.x == 0 and force.y == 0

    def test_species_filter(self):
        b = Boid(50, 50, species=1)
        other_same = Boid(55, 50, species=1)
        other_diff = Boid(60, 50, species=2)
        force = b.separation([other_same, other_diff], 30)
        assert force.x < 0  # should only be pushed by same-species


class TestAlignment:
    def test_no_neighbors(self):
        b = Boid(50, 50)
        force = b.alignment([], 60)
        assert force.x == 0 and force.y == 0

    def test_aligned_neighbors(self):
        b = Boid(50, 50, vx=1, vy=0)
        other = Boid(55, 50, vx=1, vy=0)
        force = b.alignment([other], 60)
        # Already aligned, so force should be minimal
        assert force.length() < 1.0

    def test_species_filter(self):
        b = Boid(50, 50, species=1, vx=1, vy=0)
        other_diff = Boid(55, 50, species=2, vx=0, vy=5)
        force = b.alignment([other_diff], 60)
        assert force.x == 0 and force.y == 0


class TestCohesion:
    def test_no_neighbors(self):
        b = Boid(50, 50)
        force = b.cohesion([], 60)
        assert force.x == 0 and force.y == 0

    def test_toward_center(self):
        b = Boid(50, 50)
        other = Boid(100, 50)
        force = b.cohesion([other], 60)
        # Should steer toward the other (positive x)
        assert force.x > 0

    def test_species_filter(self):
        b = Boid(50, 50, species=1)
        other_diff = Boid(100, 50, species=2)
        force = b.cohesion([other_diff], 60)
        assert force.x == 0 and force.y == 0


class TestSeek:
    def test_seek_target(self):
        b = Boid(0, 0, vx=0, vy=0)
        force = b.seek(Vector2(100, 0))
        assert force.x > 0  # should steer right

    def test_seek_at_target(self):
        b = Boid(50, 50)
        force = b.seek(Vector2(50, 50))
        assert force.x == 0 and force.y == 0


class TestArrive:
    def test_arrive_far(self):
        b = Boid(0, 0, vx=0, vy=0)
        force = b.arrive(Vector2(200, 0), slow_radius=50)
        assert force.x > 0  # should steer toward target

    def test_arrive_close(self):
        b = Boid(99, 0, vx=5, vy=0)
        force = b.arrive(Vector2(100, 0), slow_radius=50)
        # Very close, should have small desired speed
        assert force.length() < b.max_force * 2

    def test_arrive_at_target(self):
        b = Boid(50, 50)
        force = b.arrive(Vector2(50, 50))
        assert force.x == 0 and force.y == 0


class TestFlee:
    def test_flee_from_threat(self):
        b = Boid(50, 50, vx=1, vy=0)
        force = b.flee(Vector2(55, 50), panic_dist=80)
        assert force.x < 0  # should flee left

    def test_flee_far_threat(self):
        b = Boid(0, 0)
        force = b.flee(Vector2(200, 0), panic_dist=80)
        assert force.x == 0 and force.y == 0  # too far, no flee

    def test_flee_same_position(self):
        b = Boid(50, 50)
        force = b.flee(Vector2(50, 50), panic_dist=80)
        assert force.x == 0 and force.y == 0

    def test_flee_urgency_scales(self):
        b1 = Boid(50, 50, vx=0, vy=0)
        b2 = Boid(50, 50, vx=0, vy=0)
        # Close threat
        close = b1.flee(Vector2(52, 50), panic_dist=80)
        # Far threat (but within panic dist)
        far = b2.flee(Vector2(70, 50), panic_dist=80)
        assert close.length() > far.length()


class TestWander:
    def test_wander_returns_vector(self):
        b = Boid(50, 50, vx=1, vy=0)
        force = b.wander(0.1)
        assert isinstance(force, Vector2)

    def test_wander_zero_velocity(self):
        b = Boid(50, 50, vx=0, vy=0)
        force = b.wander(0.1)
        # With zero velocity, circle_center is zero, so only offset matters
        # Should still return a vector (might be zero if offset is tiny)
        assert isinstance(force, Vector2)


class TestPathFollowing:
    def test_no_path(self):
        b = Boid(50, 50)
        force = b.follow_path()
        assert force.x == 0 and force.y == 0

    def test_empty_path(self):
        b = Boid(50, 50)
        b.path = []
        force = b.follow_path()
        assert force.x == 0 and force.y == 0

    def test_follow_first_waypoint(self):
        b = Boid(0, 0, vx=1, vy=0)
        b.path = [Vector2(100, 0), Vector2(200, 0)]
        force = b.follow_path()
        assert force.x > 0  # should seek toward 100, 0

    def test_advance_to_next_waypoint(self):
        b = Boid(99, 0, vx=1, vy=0)
        b.path = [Vector2(100, 0), Vector2(200, 0)]
        b.follow_path(arrival_radius=20)
        # Should have advanced to the second waypoint
        assert b.path_index == 1

    def test_loop_path(self):
        b = Boid(99, 0, vx=1, vy=0)
        b.path = [Vector2(100, 0)]
        b.path_index = 0
        b.follow_path(loop=True, arrival_radius=20)
        # Should have looped back to index 0
        assert b.path_index == 0

    def test_arrive_at_final(self):
        b = Boid(99, 0, vx=5, vy=0)
        b.path = [Vector2(100, 0)]
        b.path_index = 0
        force = b.follow_path(loop=False, arrival_radius=20)
        # Should arrive (decelerate) rather than seek
        assert isinstance(force, Vector2)


class TestObstacleAvoidance:
    def test_far_obstacle(self):
        b = Boid(0, 0)
        force = b.avoid_obstacle(Vector2(500, 0), 30)
        assert force.x == 0 and force.y == 0

    def test_near_obstacle(self):
        b = Boid(50, 50, vx=1, vy=0)
        force = b.avoid_obstacle(Vector2(55, 50), 30)
        assert force.x < 0  # should push away

    def test_same_position(self):
        b = Boid(50, 50)
        force = b.avoid_obstacle(Vector2(50, 50), 30)
        assert force.x == 0 and force.y == 0


class TestBoundaryForce:
    def test_center(self):
        b = Boid(400, 300, vx=1, vy=0)
        force = b.boundary_force(800, 600, margin=50)
        assert force.x == 0 and force.y == 0

    def test_left_edge(self):
        b = Boid(10, 300, vx=1, vy=0)
        force = b.boundary_force(800, 600, margin=50)
        assert force.x > 0  # push right

    def test_right_edge(self):
        b = Boid(790, 300, vx=1, vy=0)
        force = b.boundary_force(800, 600, margin=50)
        assert force.x < 0  # push left

    def test_zero_margin(self):
        b = Boid(-5, -5)
        force = b.boundary_force(100, 100, margin=0)
        assert force.x == 0 and force.y == 0

    def test_negative_margin(self):
        b = Boid(50, 50)
        force = b.boundary_force(100, 100, margin=-10)
        assert force.x == 0 and force.y == 0


class TestBoidUpdate:
    def test_basic_update(self):
        b = Boid(0, 0, vx=1, vy=0)
        b.apply_force(Vector2(0.5, 0.5))
        b.update()
        assert b.pos.x > 0
        assert b.pos.y > 0

    def test_velocity_limit(self):
        b = Boid(0, 0, vx=0, vy=0, max_speed=5)
        b.apply_force(Vector2(100, 100))
        b.update()
        assert b.vel.length() <= 5.0

    def test_acceleration_reset(self):
        b = Boid(0, 0)
        b.apply_force(Vector2(1, 1))
        b.update()
        assert b.acc.x == 0 and b.acc.y == 0

    def test_trail_recorded(self):
        b = Boid(50, 50, trail_length=5)
        b.update()
        b.update()
        assert len(b.trail) == 2


class TestSerialization:
    def test_snapshot(self):
        b = Boid(10, 20, vx=1, vy=2, species=3)
        s = b.snapshot()
        assert s.id == b.id
        assert s.x == 10 and s.y == 20
        assert s.vx == 1 and s.vy == 2
        assert s.species == 3

    def test_restore(self):
        b = Boid(10, 20, vx=1, vy=2, species=3)
        state = b.snapshot()
        b2 = Boid.restore(state, trail_length=5)
        assert b2.id == b.id
        assert b2.pos.x == 10 and b2.pos.y == 20
        assert b2.vel.x == 1 and b2.vel.y == 2
        assert b2.species == 3
        assert b2.trail is not None
        assert b2.trail.maxlen == 5

    def test_to_dict(self):
        b = Boid(10, 20, vx=1, vy=2, species=3)
        d = b.to_dict()
        assert d["pos"] == [10, 20]
        assert d["vel"] == [1, 2]
        assert d["species"] == 3
        assert d["path_index"] == 0

    def test_restore_preserves_id(self):
        b = Boid(100, 200)
        original_id = b.id
        state = b.snapshot()
        b2 = Boid.restore(state)
        assert b2.id == original_id