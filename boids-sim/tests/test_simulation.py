"""Tests for the simulation engine."""

import os
import json
import tempfile
import pytest
from boids.simulation import BoidSimulation, Obstacle
from boids.config import SimulationConfig, get_preset
from boids.vector import Vector2
from boids.events import EventBus


class TestSimulationCreation:
    def test_default_config(self):
        sim = BoidSimulation()
        assert len(sim.boids) == 150
        assert sim.tick == 0
        assert sim.events is not None
        assert sim.tracker is not None

    def test_custom_config(self):
        cfg = SimulationConfig(num_boids=50, width=400, height=300)
        sim = BoidSimulation(cfg)
        assert len(sim.boids) == 50
        assert sim.config.width == 400

    def test_multi_species(self):
        cfg = SimulationConfig(num_boids=30, num_species=3)
        sim = BoidSimulation(cfg)
        species_counts = {0: 0, 1: 0, 2: 0}
        for b in sim.boids:
            species_counts[b.species] += 1
        assert species_counts[0] == 10
        assert species_counts[1] == 10
        assert species_counts[2] == 10

    def test_single_species_default(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        for b in sim.boids:
            assert b.species == 0


class TestSimulationStep:
    def test_step_advances_tick(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        sim.step()
        assert sim.tick == 1

    def test_multiple_steps(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        for _ in range(50):
            sim.step()
        assert sim.tick == 50

    def test_boids_move(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        positions_before = [(b.pos.x, b.pos.y) for b in sim.boids]
        sim.step()
        positions_after = [(b.pos.x, b.pos.y) for b in sim.boids]
        moved = sum(1 for before, after in zip(positions_before, positions_after)
                    if before != after)
        assert moved > 0

    def test_empty_simulation(self):
        sim = BoidSimulation(SimulationConfig(num_boids=0))
        sim.step()
        assert sim.tick == 1

    def test_quadtree_index(self):
        cfg = SimulationConfig(num_boids=20, spatial_index="quadtree")
        sim = BoidSimulation(cfg)
        sim.step()
        assert sim.tick == 1

    def test_invalid_spatial_index(self):
        cfg = SimulationConfig(num_boids=10, spatial_index="bogus")
        with pytest.raises(ValueError):
            BoidSimulation(cfg)


class TestObstacles:
    def test_add_obstacle(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        sim.add_obstacle(100, 100, 30)
        assert len(sim.obstacles) == 1

    def test_add_invalid_obstacle(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        with pytest.raises(ValueError):
            sim.add_obstacle(100, 100, -5)

    def test_obstacle_event_fired(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        events = []
        sim.events.on("obstacle_added", lambda obs: events.append(obs))
        sim.add_obstacle(100, 100, 30)
        assert len(events) == 1


class TestPredators:
    def test_add_predator(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        sim.add_predator(100, 100)
        assert len(sim.predators) == 1

    def test_predator_event_fired(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        events = []
        sim.events.on("predator_added", lambda p: events.append(p))
        sim.add_predator(100, 100)
        assert len(events) == 1

    def test_predator_moves(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        sim.add_predator(100, 100)
        pos_before = (sim.predators[0].pos.x, sim.predators[0].pos.y)
        sim.step()
        pos_after = (sim.predators[0].pos.x, sim.predators[0].pos.y)
        assert pos_before != pos_after

    def test_collision_detection(self):
        cfg = SimulationConfig(num_boids=1, width=200, height=200)
        sim = BoidSimulation(cfg)
        sim.add_predator(100, 100)
        # Boid is near predator — should trigger collision
        sim.boids[0].pos = Vector2(101, 100)
        collisions = []
        sim.events.on("collision", lambda p, b: collisions.append((p, b)))
        sim.step()
        assert len(collisions) > 0


class TestGoalSeeking:
    def test_set_and_clear_goal(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        sim.set_goal(400, 300)
        assert sim.goal is not None
        sim.clear_goal()
        assert sim.goal is None


class TestPathFollowing:
    def test_set_boid_path(self):
        sim = BoidSimulation(SimulationConfig(num_boids=5))
        sim.set_boid_path(0, [(100, 100), (200, 200)])
        assert sim.boids[0].path is not None
        assert len(sim.boids[0].path) == 2

    def test_set_all_paths(self):
        sim = BoidSimulation(SimulationConfig(num_boids=5))
        sim.set_all_paths([(100, 100), (200, 200), (300, 300)], loop=True)
        for b in sim.boids:
            assert b.path is not None
            assert len(b.path) == 3
        assert sim.config.path_loop == True

    def test_path_following_in_step(self):
        cfg = SimulationConfig(num_boids=5, w_path=2.0)
        sim = BoidSimulation(cfg)
        sim.set_all_paths([(400, 300), (700, 500)])
        sim.step()
        # Boids should have moved (seeking first waypoint)
        assert sim.tick == 1


class TestEvents:
    def test_step_events(self):
        sim = BoidSimulation(SimulationConfig(num_boids=5))
        starts = []
        ends = []
        sim.events.on("step_start", lambda t: starts.append(t))
        sim.events.on("step_end", lambda t: ends.append(t))
        sim.step()
        assert len(starts) == 1
        assert len(ends) == 1
        assert starts[0] == 1
        assert ends[0] == 1

    def test_boid_added_event(self):
        sim = BoidSimulation(SimulationConfig(num_boids=0))
        events = []
        sim.events.on("boid_added", lambda b: events.append(b))
        sim.add_boid(50, 50)
        assert len(events) == 1

    def test_boid_removed_event(self):
        sim = BoidSimulation(SimulationConfig(num_boids=5))
        events = []
        sim.events.on("boid_removed", lambda b: events.append(b))
        sim.remove_boid(0)
        assert len(events) == 1

    def test_listener_exception_doesnt_crash(self):
        sim = BoidSimulation(SimulationConfig(num_boids=5))
        def bad_listener(t):
            raise RuntimeError("boom")
        sim.events.on("step_start", bad_listener)
        sim.step()  # should not crash
        assert sim.tick == 1

    def test_off_unsubscribes(self):
        bus = EventBus()
        calls = []
        def cb(x):
            calls.append(x)
        bus.on("test", cb)
        bus.emit("test", 1)
        assert len(calls) == 1
        bus.off("test", cb)
        bus.emit("test", 2)
        assert len(calls) == 1  # no new calls


class TestStatsTracker:
    def test_record_and_len(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        for _ in range(20):
            sim.step()
        assert len(sim.tracker) == 20

    def test_column(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        for _ in range(5):
            sim.step()
        alignments = sim.tracker.column("alignment")
        assert len(alignments) == 5

    def test_average(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        for _ in range(10):
            sim.step()
        avg = sim.tracker.average("alignment")
        assert avg is not None
        assert 0 <= avg <= 1

    def test_trend(self):
        sim = BoidSimulation(SimulationConfig(num_boids=20))
        for _ in range(30):
            sim.step()
        trend = sim.tracker.trend("avg_speed", window=10)
        assert trend is not None

    def test_summary(self):
        sim = BoidSimulation(SimulationConfig(num_boids=20))
        for _ in range(10):
            sim.step()
        s = sim.tracker.summary()
        assert "alignment" in s
        assert "avg_speed" in s
        assert "spread" in s

    def test_convergence_tick_none(self):
        sim = BoidSimulation(SimulationConfig(num_boids=10))
        for _ in range(5):
            sim.step()
        # Very high threshold that will never be reached
        conv = sim.tracker.convergence_tick("alignment", threshold=0.99, window=2)
        assert conv is None


class TestStats:
    def test_stats_keys(self):
        sim = BoidSimulation(SimulationConfig(num_boids=20))
        sim.step()
        stats = sim.stats()
        assert "tick" in stats
        assert "count" in stats
        assert "predators" in stats
        assert "obstacles" in stats
        assert "avg_speed" in stats
        assert "alignment" in stats
        assert "centroid" in stats
        assert "spread" in stats

    def test_empty_stats(self):
        sim = BoidSimulation(SimulationConfig(num_boids=0))
        stats = sim.stats()
        assert stats["count"] == 0
        assert stats["avg_speed"] == 0.0
        assert stats["alignment"] == 0.0


class TestSerialization:
    def test_save_load_round_trip(self):
        cfg = SimulationConfig(num_boids=15)
        sim = BoidSimulation(cfg)
        for _ in range(10):
            sim.step()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            sim.save(path)
            sim2 = BoidSimulation.load(path)
            assert sim2.tick == 10
            assert len(sim2.boids) == 15
        finally:
            os.unlink(path)

    def test_save_load_with_species(self):
        cfg = SimulationConfig(num_boids=15, num_species=3)
        sim = BoidSimulation(cfg)
        sim.step()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            sim.save(path)
            sim2 = BoidSimulation.load(path)
            for b in sim2.boids:
                assert b.species in (0, 1, 2)
        finally:
            os.unlink(path)

    def test_save_load_with_obstacles_predators_goal(self):
        cfg = SimulationConfig(num_boids=5)
        sim = BoidSimulation(cfg)
        sim.add_obstacle(100, 100, 30)
        sim.add_predator(200, 200)
        sim.set_goal(300, 300)
        sim.step()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            sim.save(path)
            sim2 = BoidSimulation.load(path)
            assert len(sim2.obstacles) == 1
            assert len(sim2.predators) == 1
            assert sim2.goal is not None
        finally:
            os.unlink(path)

    def test_to_dict(self):
        sim = BoidSimulation(SimulationConfig(num_boids=5))
        d = sim.to_dict()
        assert "config" in d
        assert "boids" in d
        assert "obstacles" in d
        assert "predators" in d
        assert "tick" in d


class TestWrapping:
    def test_wrap_left(self):
        sim = BoidSimulation(SimulationConfig(num_boids=1, width=100, height=100, use_wrap=True))
        sim.boids[0].pos = Vector2(-5, 50)
        sim._wrap(sim.boids[0])
        assert sim.boids[0].pos.x == 95  # wrapped to right side

    def test_wrap_right(self):
        sim = BoidSimulation(SimulationConfig(num_boids=1, width=100, height=100, use_wrap=True))
        sim.boids[0].pos = Vector2(105, 50)
        sim._wrap(sim.boids[0])
        assert sim.boids[0].pos.x == 5  # wrapped to left side

    def test_wrap_top(self):
        sim = BoidSimulation(SimulationConfig(num_boids=1, width=100, height=100, use_wrap=True))
        sim.boids[0].pos = Vector2(50, -5)
        sim._wrap(sim.boids[0])
        assert sim.boids[0].pos.y == 95

    def test_wrap_bottom(self):
        sim = BoidSimulation(SimulationConfig(num_boids=1, width=100, height=100, use_wrap=True))
        sim.boids[0].pos = Vector2(50, 105)
        sim._wrap(sim.boids[0])
        assert sim.boids[0].pos.y == 5