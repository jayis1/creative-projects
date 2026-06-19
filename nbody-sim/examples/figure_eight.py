"""Figure-eight three-body choreography demo.

The Chenciner–Montgomery solution: three equal masses chase each other along
a single figure-eight curve. Sensitive test of integrator quality — unstable
systems diverge quickly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.simulation import Simulation


def main() -> None:
    sim = Simulation.figure_eight(dt=0.002, theta=0.3, softening=0.0)
    result = sim.run(5000)
    de = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
    print(f"Figure-eight: 5000 steps")
    print(f"  Initial E = {result.initial_energy:.8f}")
    print(f"  Final   E = {result.final_energy:.8f}")
    print(f"  dE/E     = {de:.2e}")
    print(f"  Momentum = {result.final_momentum}")


if __name__ == "__main__":
    main()