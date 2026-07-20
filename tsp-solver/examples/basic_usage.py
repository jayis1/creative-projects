"""Example: basic usage of the TSP solver.

Run with::

    python3 examples/basic_usage.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve, list_algorithms, list_algorithms_by_category
from tsp_solver.viz import ascii_plot
from tsp_solver.benchmark import BenchmarkSuite

def main():
    # List algorithms by category
    print("=== Available Algorithms ===")
    for cat, algos in list_algorithms_by_category().items():
        print(f"  {cat}: {', '.join(algos)}")

    # Generate a random instance
    print("\n=== Generate Instance ===")
    inst = generate_instance(15, seed=42, name="demo")
    print(f"Instance: {inst}")

    # Solve with different algorithms
    print("\n=== Solve ===")
    for algo in ["nearest_neighbor", "christofides", "held_karp", "savings"]:
        tour = solve(inst, algo, seed=42)
        print(f"  {algo:<28} length={tour.length:.2f}")

    # Solve with refinement
    print("\n=== Christofides + 2-opt ===")
    tour = solve(inst, "christofides", refine="two_opt", seed=42)
    print(f"  length={tour.length:.2f}")
    print(f"  order={tour.order}")

    # Visualize
    print("\n=== Visualization ===")
    print(ascii_plot(inst, tour))

    # Benchmark all algorithms
    print("\n=== Benchmark ===")
    suite = BenchmarkSuite()
    suite.run(inst, seed=42)
    print(suite.summary())
    print(f"\nBest: {suite.best()}")
    print(f"Fastest: {suite.fastest()}")


if __name__ == "__main__":
    main()