#!/usr/bin/env python3
"""Example 03: Configuration files — run experiments from YAML/JSON.

Demonstrates:
    - Creating config templates programmatically
    - Saving/loading YAML and JSON configs
    - Running algorithms from config files
    - Using callbacks in config files
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pathlib import Path
from evopt.config import default_config, save_config, load_config, build_from_config


def main():
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # --- 1. Create and save a YAML config ---
    print("=" * 60)
    print("1. Create and save a YAML config for GA on Rastrigin")
    print("=" * 60)
    cfg = default_config("ga", "rastrigin",
                          dims=5, population_size=50, max_generations=100,
                          crossover_rate=0.9, mutation_rate=0.05, elite_size=2)
    cfg["callbacks"] = [
        {"type": "stagnation", "params": {"patience": 30}},
        {"type": "adaptive_mutation_rate", "params": {}},
    ]
    yaml_path = output_dir / "ga_rastrigin.yaml"
    save_config(cfg, yaml_path)
    print(f"   Saved to: {yaml_path}")
    print(f"   Content:\n{yaml_path.read_text()}")

    # --- 2. Load and run from YAML ---
    print("=" * 60)
    print("2. Load and run from YAML config")
    print("=" * 60)
    loaded = load_config(yaml_path)
    problem, algo = build_from_config(loaded)
    print(f"   Algorithm: {algo.__class__.__name__}")
    print(f"   Problem:   {problem.__class__.__name__}")
    print(f"   Callbacks: {len(algo.callbacks)}")
    best = algo.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Termination:  {algo.termination_reason}")
    print()

    # --- 3. JSON config for CMA-ES ---
    print("=" * 60)
    print("3. JSON config for CMA-ES on Sphere")
    print("=" * 60)
    cfg2 = default_config("cmaes", "sphere", dims=3, max_generations=50)
    json_path = output_dir / "cmaes_sphere.json"
    save_config(cfg2, json_path)
    print(f"   Saved to: {json_path}")
    _, algo2 = build_from_config(load_config(json_path))
    best2 = algo2.run()
    print(f"   Best fitness: {best2.fitness:.10f}")
    print()

    # --- 4. Config with DE custom strategy ---
    print("=" * 60)
    print("4. Config for DE with custom strategy")
    print("=" * 60)
    cfg3 = {
        "algorithm": {
            "name": "de",
            "params": {
                "population_size": 50,
                "max_generations": 100,
                "F": 0.6,
                "CR": 0.9,
                "strategy": "best/1",
            }
        },
        "problem": {"name": "ackley", "params": {"dims": 3}},
        "seed": 42,
        "verbose": False,
    }
    json_path3 = output_dir / "de_ackley.json"
    save_config(cfg3, json_path3)
    _, algo3 = build_from_config(load_config(json_path3))
    best3 = algo3.run()
    print(f"   Best fitness: {best3.fitness:.8f}")


if __name__ == "__main__":
    main()