"""Example: benchmarking and exporting results.

Run with::

    python3 examples/benchmark_demo.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tsp_solver.instance import generate_instance
from tsp_solver.benchmark import BenchmarkSuite

def main():
    # Generate instances of varying sizes
    print("=== Multi-Instance Benchmark ===\n")
    instances = [
        generate_instance(10, seed=1, name="n10"),
        generate_instance(15, seed=2, name="n15"),
        generate_instance(20, seed=3, name="n20"),
    ]

    suite = BenchmarkSuite()
    suite.run_instances(
        instances,
        algorithms=[
            "nearest_neighbor", "nearest_neighbor_multistart",
            "nearest_insertion", "farthest_insertion", "greedy",
            "savings", "christofides", "mst_approx",
            "two_opt", "or_opt",
            "simulated_annealing", "iterated_local_search", "lin_kernighan",
        ],
        seed=42,
    )

    print(suite.summary())

    # Export to JSON and CSV
    print("\n=== Export ===")
    json_data = suite.to_json()
    print(f"JSON output: {len(json_data)} chars")

    csv_data = suite.to_csv()
    print(f"CSV output: {len(csv_data)} chars")
    print("\nFirst 500 chars of CSV:")
    print(csv_data[:500])

    # Find best and fastest
    best = suite.best()
    fast = suite.fastest()
    print(f"\nBest tour: {best.algorithm} on {best.instance_name} = {best.length:.2f}")
    print(f"Fastest: {fast.algorithm} on {fast.instance_name} = {fast.time_s:.6f}s")


if __name__ == "__main__":
    main()