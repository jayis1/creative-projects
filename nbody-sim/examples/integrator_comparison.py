"""Integrator comparison demo.

Runs the same two-body system with all three integrators (leapfrog, RK4,
Forest–Ruth) and compares energy conservation over 2000 steps.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.simulation import Simulation

INTEGRATORS = ["leapfrog", "rk4", "forest-ruth"]
DT = 0.005
STEPS = 2000


def main() -> None:
    print(f"Two-body orbit: {STEPS} steps, dt={DT}")
    print(f"{'Integrator':<20s} {'dE/E':>12s}  {'time/step':>10s}")
    print("-" * 50)
    for name in INTEGRATORS:
        sim = Simulation.two_body_orbit(
            dt=DT, theta=0.0, softening=0.05, integrator=name
        )
        result = sim.run(STEPS)
        de = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
        print(f"{name:<20s} {de:>12.2e}")


if __name__ == "__main__":
    main()