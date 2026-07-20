"""Example: using configuration files with the CLI and Python API.

Run with::

    python3 examples/config_demo.py
"""
import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tsp_solver.config import SolverConfig
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve

def main():
    # Create a config programmatically
    cfg = SolverConfig(algorithm="christofides", refine="two_opt", seed=42, n=30)
    print("=== Config ===")
    print(json.dumps(cfg.to_dict(), indent=2))

    # Save it to a file
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        cfg.save(f.name)
        config_path = f.name
    print(f"\nSaved to: {config_path}")

    # Load it back
    loaded = SolverConfig.from_file(config_path)
    print(f"Loaded algorithm: {loaded.algorithm}")
    print(f"Loaded refine: {loaded.refine}")

    # Use the config to solve
    inst = generate_instance(loaded.n, seed=loaded.seed)
    tour = solve(inst, loaded.algorithm, refine=loaded.refine, seed=loaded.seed)
    print(f"\nSolved {inst.n}-city instance:")
    print(f"  Algorithm: {loaded.algorithm}")
    print(f"  Refine:    {loaded.refine}")
    print(f"  Length:    {tour.length:.2f}")

    # YAML config example
    yaml_content = """\
algorithm: iterated_local_search
refine: null
seed: 42
n: 25
log_level: INFO
algorithm_params:
  iterated_local_search:
    max_iter: 300
    local_search: three_opt
"""
    yaml_path = os.path.join(os.path.dirname(__file__), "demo_config.yaml")
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    yaml_cfg = SolverConfig.from_file(yaml_path)
    print(f"\n=== YAML Config ===")
    print(f"Algorithm: {yaml_cfg.algorithm}")
    print(f"Params: {yaml_cfg.algorithm_params}")

    inst2 = generate_instance(yaml_cfg.n, seed=yaml_cfg.seed)
    params = yaml_cfg.algorithm_params.get(yaml_cfg.algorithm, {})
    tour2 = solve(inst2, yaml_cfg.algorithm, seed=yaml_cfg.seed, **params)
    print(f"ILS result: {tour2.length:.2f}")

    # Cleanup
    os.unlink(config_path)
    os.unlink(yaml_path)

if __name__ == "__main__":
    main()