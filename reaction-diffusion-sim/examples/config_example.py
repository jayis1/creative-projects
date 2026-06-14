#!/usr/bin/env python3
"""
Configuration File Example — Load and run from YAML.

Demonstrates:
1. Creating a configuration file
2. Loading configuration
3. Running the simulation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rdsim import ReactionDiffusionSolver, load_config, save_frame
import tempfile

def main():
    # Create a YAML configuration
    config_yaml = """
model: gray-scott
grid_size: 128
steps: 5000
dt: 1.0
method: euler
bc: periodic
params:
  F: 0.035
  k: 0.065
  Du: 0.16
  Dv: 0.08
viz:
  field: v
  cmap: inferno
  output: config_output.png
"""

    # Write to temp file and load
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(config_yaml)
        config_path = f.name

    try:
        # Load configuration
        config = load_config(config_path)
        print(f"Loaded config: model={config.model}, grid={config.grid_size}, "
              f"steps={config.steps}")
        config.validate()

        # Create solver from config
        solver = ReactionDiffusionSolver(
            config.model,
            grid_size=config.grid_size,
            params=config.params,
            bc=config.bc,
            dt=config.dt,
        )
        solver.apply_perturbation()

        # Run
        print(f"Running {config.steps} steps...")
        solver.step(config.steps, method=config.method)

        # Save output
        save_frame(
            solver.u, solver.v, config.viz.output,
            field=config.viz.field, cmap=config.viz.cmap,
        )
        print(f"Saved to {config.viz.output}")
    finally:
        os.unlink(config_path)

if __name__ == "__main__":
    main()