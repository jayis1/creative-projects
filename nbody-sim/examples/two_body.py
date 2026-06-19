"""Two-body circular orbit demo.

Runs a short simulation of two equal masses in a circular orbit and prints
the energy drift, which should be tiny for the symplectic integrator.
"""

import os
import sys

# Make the nbody package importable when run directly from the examples/ dir.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.simulation import Simulation


def main() -> None:
    sim = Simulation.two_body_orbit(dt=0.005, theta=0.5, softening=0.05)
    result = sim.run(2000)
    de = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
    print(f"Two-body orbit: 2000 steps")
    print(f"  Initial E = {result.initial_energy:.8f}")
    print(f"  Final   E = {result.final_energy:.8f}")
    print(f"  dE/E     = {de:.2e}")
    print(f"  Momentum = {result.final_momentum}")


if __name__ == "__main__":
    main()