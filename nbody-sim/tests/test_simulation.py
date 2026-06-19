"""Tests for the simulation orchestrator and presets."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.body import Body
from nbody.simulation import Simulation, SimulationResult, Snapshot


class TestSimulationConstruction:
    def test_empty_bodies(self):
        try:
            Simulation([])
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_negative_mass(self):
        try:
            Simulation([Body(0, 0, 0, 0, -1)])
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_invalid_theta(self):
        try:
            Simulation([Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)], theta=3.0)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_invalid_softening(self):
        try:
            Simulation([Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)], softening=-1.0)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_invalid_dt(self):
        try:
            Simulation([Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)], dt=0.0)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_dt_zero_with_adaptive(self):
        """dt=0 should be allowed when adaptive_dt is True."""
        sim = Simulation(
            [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)],
            dt=0.0, adaptive_dt=True, softening=0.5
        )
        assert sim.adaptive_dt is True

    def test_defensive_copy(self):
        """Simulation should not modify the original body list."""
        bodies = [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)]
        sim = Simulation(bodies, dt=0.01, softening=0.1)
        sim.run(10)
        # Original bodies should be unchanged.
        assert bodies[0].x == 0.0
        assert bodies[1].x == 1.0

    def test_integrator_selection(self):
        sim = Simulation(
            [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)],
            dt=0.01, softening=0.1, integrator="rk4"
        )
        assert sim.integrator_name == "rk4"

    def test_unknown_integrator(self):
        try:
            Simulation(
                [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)],
                integrator="euler"
            )
            assert False, "Should raise ValueError"
        except ValueError:
            pass


class TestSimulationRun:
    def test_basic_run(self):
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        result = sim.run(100)
        assert result.n_steps == 100
        assert len(result.snapshots) == 0  # no snapshots requested

    def test_run_with_snapshots(self):
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        result = sim.run(100, snapshot_every=20)
        # Initial (0) + 20, 40, 60, 80, 100 = 6 snapshots.
        assert len(result.snapshots) == 6
        assert result.snapshots[0].step == 0
        assert result.snapshots[-1].step == 100

    def test_run_with_on_step(self):
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        calls = []
        result = sim.run(50, on_step=lambda s: calls.append(s.step_count))
        assert len(calls) == 50
        assert calls[-1] == 50

    def test_run_called_twice(self):
        """run() should work when called multiple times on the same sim."""
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        sim.run(50)
        res = sim.run(10, snapshot_every=5)
        # First snapshot should have step=50 (not 0).
        assert res.snapshots[0].step == 50
        assert abs(res.snapshots[0].t - 0.5) < 1e-9

    def test_final_snapshot_not_multiple(self):
        """Final snapshot should be captured even if steps not a multiple."""
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        result = sim.run(10, snapshot_every=7)
        # Should capture step 0, 7, and 10 (final).
        assert result.snapshots[-1].step == 10

    def test_diagnostics_methods(self):
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        e = sim.total_energy()
        p = sim.total_momentum()
        com = sim.center_of_mass()
        assert isinstance(e, float)
        assert isinstance(p, tuple) and len(p) == 2
        assert isinstance(com, tuple) and len(com) == 2


class TestPresets:
    def test_two_body_orbit(self):
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        assert len(sim.bodies) == 2
        assert sim.bodies[0].name == "body1"
        assert sim.bodies[1].name == "body2"

    def test_figure_eight(self):
        sim = Simulation.figure_eight(dt=0.001, softening=0.0)
        assert len(sim.bodies) == 3
        # All masses equal.
        assert all(b.m == 1.0 for b in sim.bodies)

    def test_plummer_sphere(self):
        sim = Simulation.plummer_sphere(n=50, seed=42, radius=10.0, softening=1.0)
        assert len(sim.bodies) == 50
        # All bodies within capped radius.
        max_r = max(math.hypot(b.x, b.y) for b in sim.bodies)
        assert max_r <= 100.0 + 1e-6

    def test_random_cloud(self):
        sim = Simulation.random_cloud(n=30, seed=7, spread=5.0)
        assert len(sim.bodies) == 30
        for b in sim.bodies:
            assert -5.0 <= b.x <= 5.0
            assert -5.0 <= b.y <= 5.0

    def test_solar_system(self):
        sim = Simulation.solar_system(dt=0.001, softening=0.01)
        assert len(sim.bodies) == 5  # Sun + 4 planets
        assert sim.bodies[0].name == "Sun"
        # Sun should be at origin.
        assert abs(sim.bodies[0].x) < 1e-10
        assert abs(sim.bodies[0].y) < 1e-10

    def test_binary_system(self):
        sim = Simulation.binary_system(dt=0.01, softening=0.1)
        assert len(sim.bodies) == 2
        assert sim.bodies[0].name == "star1"

    def test_binary_eccentric(self):
        sim = Simulation.binary_system(eccentricity=0.5, dt=0.01, softening=0.1)
        assert len(sim.bodies) == 2

    def test_kuzmin_disk(self):
        sim = Simulation.kuzmin_disk(n=50, seed=42, scale_radius=5.0, softening=1.0)
        assert len(sim.bodies) == 50
        max_r = max(math.hypot(b.x, b.y) for b in sim.bodies)
        # Kuzmin cap is 20*a = 100.
        assert max_r <= 100.0 + 1e-6

    def test_preset_reproducible(self):
        """Same seed should give same initial conditions."""
        sim1 = Simulation.plummer_sphere(n=20, seed=123, softening=1.0)
        sim2 = Simulation.plummer_sphere(n=20, seed=123, softening=1.0)
        for b1, b2 in zip(sim1.bodies, sim2.bodies):
            assert b1.x == b2.x
            assert b1.y == b2.y


class TestRecenterCom:
    def test_recenter_zeros_momentum(self):
        """After recentering, total momentum should be ~zero."""
        sim = Simulation.random_cloud(n=20, seed=5, dt=0.01, softening=0.5,
                                       recenter_com=True)
        px, py = sim.total_momentum()
        assert abs(px) < 1e-10, f"COM momentum x not zero: {px}"
        assert abs(py) < 1e-10, f"COM momentum y not zero: {py}"

    def test_recenter_com_at_origin(self):
        sim = Simulation.random_cloud(n=20, seed=5, dt=0.01, softening=0.5,
                                       recenter_com=True)
        cx, cy = sim.center_of_mass()
        assert abs(cx) < 1e-10
        assert abs(cy) < 1e-10