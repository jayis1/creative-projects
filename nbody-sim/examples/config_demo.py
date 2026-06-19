"""Config file demo.

Loads a configuration from configs/ and runs the simulation.
Demonstrates the --config CLI flag and the config system.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.config import load_config
from nbody.simulation import Simulation
from nbody.cli import PRESETS


def main() -> None:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "configs", "plummer_example.yaml"
    )
    if not os.path.exists(config_path):
        print(f"Config not found: {config_path}")
        sys.exit(1)

    cfg = load_config(config_path)
    print(f"Loaded config: preset={cfg.preset}, N={cfg.n_bodies}, "
          f"steps={cfg.steps}, dt={cfg.dt}")

    # Build the simulation from the config.
    # We'll construct args manually from the config for the preset factory.
    import argparse
    args = argparse.Namespace(
        preset=cfg.preset, dt=cfg.dt, theta=cfg.theta,
        softening=cfg.softening, G=cfg.G, n_bodies=cfg.n_bodies,
        seed=cfg.seed, integrator="leapfrog",
        recenter_com=cfg.recenter_com, adaptive_dt=cfg.adaptive_dt,
        adaptive_eta=cfg.adaptive_eta,
    )
    sim = PRESETS[cfg.preset](args)
    result = sim.run(cfg.steps, snapshot_every=cfg.snapshot_every)
    de = abs(result.final_energy - result.initial_energy) / abs(result.initial_energy)
    print(f"  dE/E = {de:.2e}")
    print(f"  Snapshots: {len(result.snapshots)}")


if __name__ == "__main__":
    main()