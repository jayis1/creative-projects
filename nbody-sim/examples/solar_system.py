"""Solar system demo.

Runs a simplified inner solar system (Sun + Mercury, Venus, Earth, Mars)
and prints energy conservation. Demonstrates the solar-system preset with
a large mass ratio.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.simulation import Simulation


def main() -> None:
    sim = Simulation.solar_system(
        dt=0.0001, theta=0.5, softening=0.01, G=1.0
    )
    result = sim.run(5000)
    de = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
    print("Solar system: 5000 steps")
    print(f"  Initial E = {result.initial_energy:.10f}")
    print(f"  Final   E = {result.final_energy:.10f}")
    print(f"  dE/E     = {de:.2e}")
    print(f"  Bodies:")
    for b in sim.bodies:
        print(f"    {b.name:10s}  pos=({b.x:.4f}, {b.y:.4f})  "
              f"v=({b.vx:.4f}, {b.vy:.4f})  m={b.m:.2e}")


if __name__ == "__main__":
    main()