#!/usr/bin/env python3
"""Test enhanced features."""
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve, list_algorithms
from tsp_solver.benchmark import BenchmarkSuite
from tsp_solver.viz import ascii_plot

print("=== Algorithms ===")
print(list_algorithms())

inst = generate_instance(15, seed=42)

print("\n=== Benchmark ===")
suite = BenchmarkSuite()
suite.run(inst, seed=42)
print(suite.summary())
print(f"\nBest: {suite.best()}")
print(f"Fastest: {suite.fastest()}")

print("\n=== Multi-start NN ===")
t1 = solve(inst, 'nearest_neighbor')
t2 = solve(inst, 'nearest_neighbor_multistart', seed=42)
print(f"NN: {t1.length:.2f}")
print(f"NN multistart: {t2.length:.2f}")

print("\n=== ASCII Plot ===")
tour = solve(inst, 'christofides', refine='two_opt')
print(ascii_plot(inst, tour, width=50, height=15))

print("\n=== JSON export ===")
from tsp_solver.viz import tour_to_json
import json
data = tour_to_json(inst, tour)
print(json.dumps({k: v for k, v in data.items() if k != 'coords'}, indent=2))