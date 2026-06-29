#!/usr/bin/env python3
"""Example 04: Batch experiments and parameter sweeps.

Demonstrates:
    - Running multiple algorithm/problem combinations
    - Repeating experiments with different seeds
    - Parameter sweeps (grid search)
    - Exporting results to JSON/CSV
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pathlib import Path
from evopt.results import Experiment, parameter_sweep


def main():
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # --- 1. Batch experiment: compare algorithms ---
    print("=" * 60)
    print("1. Batch experiment: GA vs DE vs PSO vs CMA-ES on Rastrigin")
    print("=" * 60)
    exp = Experiment(name="algo_comparison")
    for alg in ["ga", "de", "pso", "cmaes"]:
        exp.add(alg, "rastrigin", {
            "dims": 5,
            "population_size": 50,
            "max_generations": 100,
        }, seed=42)
    results = exp.run(repeats=3, verbose=False)
    print(f"   Total runs: {len(results)}")
    exp.report()

    # --- 2. Save results ---
    print()
    print("=" * 60)
    print("2. Save results to JSON")
    print("=" * 60)
    exp.save_results(output_dir / "batch_results")
    print(f"   Saved to: {output_dir / 'batch_results'}")

    # --- 3. Parameter sweep: GA mutation rate ---
    print()
    print("=" * 60)
    print("3. Parameter sweep: GA mutation_rate on Rastrigin")
    print("=" * 60)
    sweep_exp = parameter_sweep(
        "ga", "rastrigin",
        param_grid={
            "mutation_rate": [0.01, 0.05, 0.1, 0.2],
            "crossover_rate": [0.7, 0.9],
        },
        fixed_params={
            "dims": 3,
            "population_size": 50,
            "max_generations": 50,
        },
        repeats=2,
        seed=42,
    )
    sweep_exp.report()
    print(f"   Total configurations: {len(sweep_exp.configs)}")
    print(f"   Total results: {len(sweep_exp.results)}")

    # --- 4. Find best configuration ---
    print()
    print("=" * 60)
    print("4. Best configuration from sweep")
    print("=" * 60)
    best_result = min(sweep_exp.results, key=lambda r: r.best_fitness)
    print(f"   Best fitness: {best_result.best_fitness:.6f}")
    print(f"   Algorithm:    {best_result.algorithm_name}")
    print(f"   Metadata:     {best_result.metadata}")


if __name__ == "__main__":
    main()