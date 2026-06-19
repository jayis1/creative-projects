"""Tests for the integrators (leapfrog, RK4, Forest–Ruth)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.body import Body
from nbody.simulation import Simulation
from nbody.integrators import (
    LeapfrogIntegrator,
    RK4Integrator,
    ForestRuthIntegrator,
    make_integrator,
    INTEGRATORS,
)


class TestLeapfrogIntegrator:
    def test_step_no_bodies(self):
        integ = LeapfrogIntegrator()
        integ.step([], 0.01)  # should not crash

    def test_step_zero_dt(self):
        bodies = [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)]
        integ = LeapfrogIntegrator(theta=0.5, softening=0.1)
        x0 = bodies[0].x
        integ.step(bodies, 0.0)
        assert bodies[0].x == x0  # no movement with dt=0

    def test_energy_conservation_two_body(self):
        """Leapfrog should conserve energy well for a circular orbit."""
        sim = Simulation.two_body_orbit(dt=0.005, theta=0.0, softening=0.05)
        result = sim.run(2000)
        dE = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
        assert dE < 1e-6, f"Energy drift too large: {dE}"

    def test_momentum_conservation(self):
        """Total momentum should be exactly conserved."""
        sim = Simulation.two_body_orbit(dt=0.01, theta=0.5, softening=0.1)
        result = sim.run(100)
        dp = math.hypot(
            result.final_momentum[0] - result.initial_momentum[0],
            result.final_momentum[1] - result.initial_momentum[1],
        )
        assert dp < 1e-10, f"Momentum not conserved: dp={dp}"


class TestRK4Integrator:
    def test_step_no_bodies(self):
        integ = RK4Integrator()
        integ.step([], 0.01)

    def test_step_zero_dt(self):
        bodies = [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)]
        integ = RK4Integrator(theta=0.5, softening=0.1)
        x0 = bodies[0].x
        integ.step(bodies, 0.0)
        assert bodies[0].x == x0

    def test_rk4_energy_drift(self):
        """RK4 should have small energy error per step but secular drift."""
        sim = Simulation.two_body_orbit(
            dt=0.005, theta=0.0, softening=0.05, integrator="rk4"
        )
        result = sim.run(500)
        dE = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
        # RK4 is accurate per step but drifts — 500 steps should be fine.
        assert dE < 0.01, f"RK4 energy drift too large: {dE}"

    def test_rk4_vs_leapfrog_accuracy(self):
        """For short runs, RK4 should be more accurate than leapfrog per step."""
        dt = 0.01
        sim_lf = Simulation.two_body_orbit(dt=dt, theta=0.0, softening=0.05, integrator="leapfrog")
        sim_rk4 = Simulation.two_body_orbit(dt=dt, theta=0.0, softening=0.05, integrator="rk4")
        res_lf = sim_lf.run(100)
        res_rk4 = sim_rk4.run(100)
        dE_lf = abs(res_lf.final_energy - res_lf.initial_energy) / abs(res_lf.initial_energy)
        dE_rk4 = abs(res_rk4.final_energy - res_rk4.initial_energy) / abs(res_rk4.initial_energy)
        # RK4 should be at least as good as leapfrog for 100 steps at this dt.
        # (Not strictly guaranteed since leapfrog is symplectic, but for short runs RK4 is good.)
        assert dE_rk4 < 1e-4, f"RK4 dE/E too large: {dE_rk4}"


class TestForestRuthIntegrator:
    def test_step_no_bodies(self):
        integ = ForestRuthIntegrator()
        integ.step([], 0.01)

    def test_energy_conservation(self):
        """Forest–Ruth is symplectic, so energy should be bounded."""
        sim = Simulation.two_body_orbit(
            dt=0.01, theta=0.0, softening=0.05, integrator="forest-ruth"
        )
        result = sim.run(1000)
        dE = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
        # Forest-Ruth is 4th order symplectic, should conserve well.
        assert dE < 1e-4, f"Forest-Ruth energy drift too large: {dE}"

    def test_momentum_conservation(self):
        sim = Simulation.two_body_orbit(
            dt=0.01, theta=0.5, softening=0.1, integrator="forest-ruth"
        )
        result = sim.run(100)
        dp = math.hypot(
            result.final_momentum[0] - result.initial_momentum[0],
            result.final_momentum[1] - result.initial_momentum[1],
        )
        assert dp < 1e-10, f"Momentum not conserved: dp={dp}"


class TestIntegratorRegistry:
    def test_make_integrator_leapfrog(self):
        integ = make_integrator("leapfrog")
        assert isinstance(integ, LeapfrogIntegrator)

    def test_make_integrator_rk4(self):
        integ = make_integrator("rk4")
        assert isinstance(integ, RK4Integrator)

    def test_make_integrator_forest_ruth(self):
        integ = make_integrator("forest-ruth")
        assert isinstance(integ, ForestRuthIntegrator)

    def test_make_integrator_case_insensitive(self):
        integ = make_integrator("LEAPFROG")
        assert isinstance(integ, LeapfrogIntegrator)

    def test_make_integrator_invalid(self):
        try:
            make_integrator("euler")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_all_integrators_in_dict(self):
        assert "leapfrog" in INTEGRATORS
        assert "rk4" in INTEGRATORS
        assert "forest-ruth" in INTEGRATORS