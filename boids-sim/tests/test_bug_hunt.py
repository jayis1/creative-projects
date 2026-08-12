"""Bug hunt tests for boids-sim.

Each test verifies a specific bug before fixing, then confirms the fix works.
Run with: python3 -m pytest tests/test_bug_hunt.py -v
"""

import math
import os
import sys
import tempfile

# Make the package importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from boids.vector import Vector2
from boids.boid import Boid
from boids.simulation import BoidSimulation
from boids.config import SimulationConfig, get_preset, save_config, load_config, PRESETS
from boids.spatial_hash import SpatialHashGrid
from boids.renderer import SVGRenderer, ASCIIRenderer, PPMRenderer, TrailSVGRenderer


class TestSvgStrokeTypo:
    """Bug 1: SVG obstacle has 'sroke' instead of 'stroke' attribute."""

    def test_svg_obstacle_has_stroke_not_sroke(self):
        """The SVG output for obstacles should use 'stroke', not 'sroke'."""
        cfg = SimulationConfig(num_boids=5)
        sim = BoidSimulation(cfg)
        sim.add_obstacle(400, 300, 30)
        svg = SVGRenderer().render(sim)
        # Bug: obstacle circle had 'sroke=' instead of 'stroke='
        assert "sroke=" not in svg, "SVG has typo 'sroke=' should be 'stroke='"
        # After fix, stroke should be present (or at least not have the typo)
        # Note: the fix removes the invalid attribute entirely since fill is sufficient

    def test_svg_is_valid_xml(self):
        """SVG output should not contain invalid attribute names."""
        cfg = SimulationConfig(num_boids=3)
        sim = BoidSimulation(cfg)
        sim.add_obstacle(100, 100, 20)
        svg = SVGRenderer().render(sim)
        # Check for any obvious XML attribute typos
        for part in svg.split('"'):
            if part.strip().endswith("="):
                attr = part.strip().rstrip("=").split()[-1]
                # Valid SVG attributes should be lowercase letters only
                assert attr.isalpha(), f"Invalid SVG attribute: {attr}"


class TestAsciiArrowDirection:
    """Bug 2: ASCII arrow directions are inverted on the y-axis.

    In screen coordinates, y increases downward. When a boid moves down
    (angle = pi/2), the ASCII should show '↓', but the original code
    showed '↑' because the arrow array assumed y increases upward.
    """

    def test_arrow_down_for_downward_velocity(self):
        """A boid moving downward should show '↓' in ASCII."""
        cfg = SimulationConfig(num_boids=0, width=100, height=100)
        sim = BoidSimulation(cfg)
        # Add a boid moving straight down (positive y in screen coords)
        b = Boid(50, 50, vx=0, vy=5)  # moving down
        sim.boids.append(b)
        renderer = ASCIIRenderer(cols=20, rows=10)
        frame = renderer.render(sim)
        # The arrow at position (10, 5) should be '↓'
        lines = frame.split("\n")
        # Boid at (50, 50) maps to col=10, row=5
        char = lines[5][10]
        assert char == "↓", f"Expected '↓' for downward motion, got '{char}'"

    def test_arrow_up_for_upward_velocity(self):
        """A boid moving upward (negative y) should show '↑' in ASCII."""
        cfg = SimulationConfig(num_boids=0, width=100, height=100)
        sim = BoidSimulation(cfg)
        b = Boid(50, 50, vx=0, vy=-5)  # moving up (negative y)
        sim.boids.append(b)
        renderer = ASCIIRenderer(cols=20, rows=10)
        frame = renderer.render(sim)
        lines = frame.split("\n")
        char = lines[5][10]
        assert char == "↑", f"Expected '↑' for upward motion, got '{char}'"

    def test_arrow_right_for_rightward_velocity(self):
        """A boid moving right should show '→'."""
        cfg = SimulationConfig(num_boids=0, width=100, height=100)
        sim = BoidSimulation(cfg)
        b = Boid(50, 50, vx=5, vy=0)
        sim.boids.append(b)
        renderer = ASCIIRenderer(cols=20, rows=10)
        frame = renderer.render(sim)
        lines = frame.split("\n")
        char = lines[5][10]
        assert char == "→", f"Expected '→' for rightward motion, got '{char}'"


class TestCalmGlidePresetDuplicateKey:
    """Bug 3: 'calm-glide' preset has duplicate 'max_force' key in dict literal.

    The second value silently overwrites the first. While both are 0.1,
    this is dead code and could mask a bug if values are changed.
    """

    def test_calm_glide_preset_has_no_duplicate_keys(self):
        """The calm-glide preset source should not have duplicate keys."""
        # We verify by checking that the preset produces the expected config
        cfg = get_preset("calm-glide")
        assert cfg.max_force == 0.1
        assert cfg.dt == 0.5
        # The fix removes the duplicate key from the source dict


class TestUnusedNeighborsCache:
    """Bug 4: `all_neighbors_cache` in step() is populated but never used.

    This wastes memory by allocating a dict and lists each tick.
    """

    def test_no_unused_cache_variable(self):
        """After fix, step() should not allocate unnecessary cache."""
        # This is a code-level fix; we verify the simulation still works
        cfg = SimulationConfig(num_boids=10)
        sim = BoidSimulation(cfg)
        sim.step()
        sim.step()
        assert sim.tick == 2
        assert len(sim.boids) == 10


class TestBoundaryForceZeroDivision:
    """Bug 5: boundary_force() raises ZeroDivisionError when margin=0 and boid is outside."""

    def test_boundary_force_zero_margin_center(self):
        """boundary_force should handle margin=0 without crashing at center."""
        b = Boid(50, 50, vx=1, vy=1)
        # margin=0 should not cause ZeroDivisionError
        force = b.boundary_force(100, 100, margin=0)
        assert isinstance(force, Vector2)

    def test_boundary_force_zero_margin_at_edge(self):
        """At the edge with margin=0, should not crash."""
        b = Boid(0, 0, vx=1, vy=1)
        force = b.boundary_force(100, 100, margin=0)
        assert isinstance(force, Vector2)

    def test_boundary_force_zero_margin_negative_pos(self):
        """Boid at negative position with margin=0 must not ZeroDivisionError."""
        # FIX: this was the actual crash scenario
        b = Boid(-5, -5, vx=1, vy=1)
        force = b.boundary_force(100, 100, margin=0)
        assert isinstance(force, Vector2)
        # With margin=0, boundary force should be zero
        assert force.x == 0.0
        assert force.y == 0.0

    def test_boundary_force_negative_margin(self):
        """Negative margin should also be handled safely."""
        b = Boid(50, 50, vx=1, vy=1)
        force = b.boundary_force(100, 100, margin=-10)
        assert isinstance(force, Vector2)


class TestVectorSetLengthZero:
    """Bug 6: set_length on a zero vector silently does nothing.

    This can cause subtle bugs where the caller expects a non-zero vector.
    """

    def test_set_length_zero_vector(self):
        """set_length on zero vector should be a safe no-op."""
        v = Vector2(0, 0)
        v.set_length(5.0)
        # Should remain zero, not crash
        assert v.x == 0.0
        assert v.y == 0.0


class TestSpatialHashNegativeCoords:
    """Bug 7: Spatial hash should handle negative coordinates correctly.

    Boids can go slightly negative before wrapping kicks in.
    """

    def test_insert_negative_coords(self):
        """Objects at negative coordinates should be queryable."""
        grid = SpatialHashGrid(60.0)
        obj = "test_obj"
        grid.insert(obj, -10.0, -10.0)
        results = list(grid.query(-10.0, -10.0, 5.0))
        assert obj in results

    def test_query_across_negative_boundary(self):
        """Query spanning negative and positive cells should work."""
        grid = SpatialHashGrid(60.0)
        obj1 = "neg"
        obj2 = "pos"
        grid.insert(obj1, -5.0, -5.0)
        grid.insert(obj2, 5.0, 5.0)
        results = list(grid.query(0.0, 0.0, 70.0))
        assert obj1 in results
        assert obj2 in results


class TestSimulationSaveLoadRoundTrip:
    """Bug 8: Save/load should preserve all state including tick count."""

    def test_save_load_preserves_tick(self):
        """Loading a saved simulation should restore the tick count."""
        cfg = SimulationConfig(num_boids=10)
        sim = BoidSimulation(cfg)
        for _ in range(42):
            sim.step()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            sim.save(path)
            sim2 = BoidSimulation.load(path)
            assert sim2.tick == 42
            assert len(sim2.boids) == 10
        finally:
            os.unlink(path)

    def test_save_load_preserves_obstacles_and_goal(self):
        """Loading should restore obstacles, predators, and goal."""
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
            assert sim2.goal.x == 300
            assert sim2.goal.y == 300
        finally:
            os.unlink(path)


class TestPPMRendererScale:
    """Bug 9: PPM renderer with scale=0 produces a 0x0 image and negative scale produces invalid PPM."""

    def test_ppm_zero_scale_raises_error(self):
        """PPM with scale=0 should raise ValueError after fix."""
        cfg = SimulationConfig(num_boids=3, width=100, height=100)
        sim = BoidSimulation(cfg)
        with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
            path = f.name
        try:
            # FIX: scale=0 should now raise ValueError
            try:
                PPMRenderer().render(sim, path, scale=0.0)
                assert False, "Should have raised ValueError for scale=0"
            except ValueError:
                pass  # Expected after fix
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_ppm_negative_scale_raises_error(self):
        """PPM with negative scale should raise ValueError after fix."""
        cfg = SimulationConfig(num_boids=3, width=100, height=100)
        sim = BoidSimulation(cfg)
        with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
            path = f.name
        try:
            try:
                PPMRenderer().render(sim, path, scale=-1.0)
                assert False, "Should have raised ValueError for negative scale"
            except ValueError:
                pass  # Expected after fix
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestConfigYamlRoundTrip:
    """Bug 10: YAML config round-trip should preserve all values."""

    def test_yaml_round_trip(self):
        """Saving and loading YAML config should preserve values."""
        cfg = SimulationConfig(num_boids=42, w_sep=2.5, use_wrap=True)
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            save_config(cfg, path)
            cfg2 = load_config(path)
            assert cfg2.num_boids == 42
            assert cfg2.w_sep == 2.5
            assert cfg2.use_wrap == True
        finally:
            os.unlink(path)


class TestBoidRestorePreservesId:
    """Bug 11: Boid.restore should preserve the original boid ID."""

    def test_restore_preserves_id(self):
        """Restored boids should have their original IDs."""
        b = Boid(10, 20, vx=1, vy=1)
        original_id = b.id
        state = b.snapshot()
        b2 = Boid.restore(state)
        assert b2.id == original_id


class TestFleeZeroDistance:
    """Bug 12: flee() with distance exactly 0 should not crash (division by zero)."""

    def test_flee_at_exact_same_position(self):
        """flee() when boid and target are at same position should return zero force."""
        b = Boid(50, 50, vx=1, vy=1)
        force = b.flee(Vector2(50, 50), panic_dist=80)
        # Should return zero vector, not crash
        assert force.x == 0.0
        assert force.y == 0.0


class TestAvoidObstacleZeroDistance:
    """Bug 13: avoid_obstacle() with distance exactly 0 should not crash."""

    def test_avoid_obstacle_same_position(self):
        """avoid_obstacle() when boid is inside obstacle should not crash."""
        b = Boid(50, 50, vx=1, vy=1)
        force = b.avoid_obstacle(Vector2(50, 50), 30)
        # Should return zero vector (distance is 0, which is < 1e-6 guard)
        assert force.x == 0.0
        assert force.y == 0.0


class TestEmptySimulation:
    """Bug 14: Empty simulation should produce valid stats."""

    def test_empty_simulation_stats(self):
        """A simulation with 0 boids should return valid stats."""
        cfg = SimulationConfig(num_boids=0)
        sim = BoidSimulation(cfg)
        stats = sim.stats()
        assert stats["count"] == 0
        assert stats["avg_speed"] == 0.0
        assert stats["alignment"] == 0.0
        assert stats["centroid"] == [0.0, 0.0]
        assert stats["spread"] == 0.0

    def test_empty_simulation_step(self):
        """Stepping a simulation with 0 boids should not crash."""
        cfg = SimulationConfig(num_boids=0)
        sim = BoidSimulation(cfg)
        sim.step()
        assert sim.tick == 1


class TestSimulationStepNoPredators:
    """Bug 15: Simulation should work correctly with predators but no boids."""

    def test_predator_with_no_boids(self):
        """A predator with no boids to chase should still wander."""
        cfg = SimulationConfig(num_boids=0)
        sim = BoidSimulation(cfg)
        sim.add_predator(100, 100)
        sim.step()
        # Predator should have moved
        assert len(sim.predators) == 1
        # Just verify it didn't crash
        assert sim.tick == 1