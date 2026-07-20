#!/usr/bin/env python3
"""Bug hunt tests for the TSP solver."""
import sys
import math
sys.path.insert(0, '.')

from tsp_solver.instance import TSPInstance, generate_instance
from tsp_solver.tour import Tour
from tsp_solver.solver import solve
from tsp_solver.exact import held_karp, branch_and_bound
from tsp_solver.heuristics import nearest_neighbor, greedy, nearest_insertion, farthest_insertion
from tsp_solver.local_search import two_opt, three_opt, or_opt
from tsp_solver.metaheuristics import simulated_annealing, genetic_algorithm, ant_colony
from tsp_solver.approximation import mst_approx, christofides

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} {detail}")
        failed += 1

print("=== Bug Hunt Tests ===\n")

# --- Bug 1: 3-opt produces invalid permutations ---
print("--- Bug 1: 3-opt tour validity ---")
inst = generate_instance(10, seed=42)
tour_3opt = three_opt(inst, max_iter=100)
order = list(tour_3opt.order)
is_perm = sorted(order) == list(range(inst.n))
check("3-opt produces valid permutation", is_perm, f"got {order}, sorted={sorted(order)}")
if is_perm:
    # Check length matches
    computed_len = inst.tour_length(order)
    check("3-opt cached length matches actual", abs(computed_len - tour_3opt.length) < 1e-6,
          f"cached={tour_3opt.length}, actual={computed_len}")

# Test 3-opt on multiple instances
for seed in range(5):
    inst = generate_instance(8, seed=seed)
    t = three_opt(inst, max_iter=50)
    is_perm = sorted(t.order) == list(range(inst.n))
    check(f"3-opt valid perm (seed={seed})", is_perm, f"order={list(t.order)}")

# --- Bug 2: 3-opt improvement check ---
print("\n--- Bug 2: 3-opt should not worsen tour ---")
inst = generate_instance(12, seed=42)
nn_tour = nearest_neighbor(inst)
t3 = three_opt(inst, nn_tour, max_iter=100)
check("3-opt does not worsen NN tour", t3.length <= nn_tour.length + 1e-6,
      f"NN={nn_tour.length}, 3opt={t3.length}")

# --- Bug 3: or_opt produces valid permutations ---
print("\n--- Bug 3: or_opt tour validity ---")
for seed in range(5):
    inst = generate_instance(8, seed=seed)
    t = or_opt(inst, max_iter=50)
    is_perm = sorted(t.order) == list(range(inst.n))
    check(f"or_opt valid perm (seed={seed})", is_perm, f"order={list(t.order)}")

# --- Bug 4: or_opt should not worsen tour ---
print("\n--- Bug 4: or_opt should not worsen tour ---")
inst = generate_instance(12, seed=42)
nn_tour = nearest_neighbor(inst)
to = or_opt(inst, nn_tour, max_iter=100)
check("or_opt does not worsen NN tour", to.length <= nn_tour.length + 1e-6,
      f"NN={nn_tour.length}, or_opt={to.length}")

# --- Bug 5: branch_and_bound matches held_karp ---
print("\n--- Bug 5: B&B vs Held-Karp correctness ---")
for seed in range(10):
    inst = generate_instance(8, seed=seed)
    hk = held_karp(inst)
    bb = branch_and_bound(inst)
    check(f"B&B == Held-Karp (seed={seed})", abs(hk.length - bb.length) < 1e-6,
          f"HK={hk.length}, B&B={bb.length}")

# --- Bug 6: Tour validates that order is a permutation ---
print("\n--- Bug 6: Tour handles n=2 ---")
inst = TSPInstance(coords=[[0, 0], [3, 4]])
t = solve(inst, 'nearest_neighbor')
check("NN works for n=2", abs(t.length - 10.0) < 0.01, f"length={t.length}")

# --- Bug 7: Christofides produces valid tour ---
print("\n--- Bug 7: Christofides tour validity ---")
for seed in range(10):
    inst = generate_instance(12, seed=seed)
    t = christofides(inst)
    is_perm = sorted(t.order) == list(range(inst.n))
    check(f"Christofides valid perm (seed={seed})", is_perm, f"order={list(t.order)}")

# --- Bug 8: 2-opt wrap-around correctness ---
print("\n--- Bug 8: 2-opt validity and improvement ---")
for seed in range(5):
    inst = generate_instance(10, seed=seed)
    nn = nearest_neighbor(inst)
    t2 = two_opt(inst, nn, max_iter=100)
    is_perm = sorted(t2.order) == list(range(inst.n))
    check(f"2-opt valid perm (seed={seed})", is_perm, f"order={list(t2.order)}")
    check(f"2-opt improves NN (seed={seed})", t2.length <= nn.length + 1e-6,
          f"NN={nn.length}, 2opt={t2.length}")

# --- Bug 9: SA produces valid tours ---
print("\n--- Bug 9: Simulated annealing validity ---")
for seed in range(5):
    inst = generate_instance(10, seed=seed)
    t = simulated_annealing(inst, seed=seed, max_iter=10000)
    is_perm = sorted(t.order) == list(range(inst.n))
    check(f"SA valid perm (seed={seed})", is_perm, f"order={list(t.order)}")
    check(f"SA length positive (seed={seed})", t.length > 0, f"length={t.length}")

# --- Bug 10: GA produces valid tours ---
print("\n--- Bug 10: Genetic algorithm validity ---")
for seed in range(3):
    inst = generate_instance(10, seed=seed)
    t = genetic_algorithm(inst, seed=seed, generations=50, population_size=30)
    is_perm = sorted(t.order) == list(range(inst.n))
    check(f"GA valid perm (seed={seed})", is_perm, f"order={list(t.order)}")

# --- Bug 11: ACO produces valid tours ---
print("\n--- Bug 11: Ant colony validity ---")
for seed in range(3):
    inst = generate_instance(10, seed=seed)
    t = ant_colony(inst, seed=seed, n_iterations=30, n_ants=20)
    is_perm = sorted(t.order) == list(range(inst.n))
    check(f"ACO valid perm (seed={seed})", is_perm, f"order={list(t.order)}")

# --- Bug 12: Greedy produces valid tours ---
print("\n--- Bug 12: Greedy validity ---")
for seed in range(5):
    inst = generate_instance(10, seed=seed)
    t = greedy(inst)
    is_perm = sorted(t.order) == list(range(inst.n))
    check(f"Greedy valid perm (seed={seed})", is_perm, f"order={list(t.order)}")

# --- Bug 13: tour_length matches cached length ---
print("\n--- Bug 13: Cached length consistency ---")
inst = generate_instance(15, seed=42)
for algo in ['nearest_neighbor', 'greedy', 'mst_approx', 'christofides',
             'nearest_insertion', 'farthest_insertion']:
    t = solve(inst, algo)
    actual = inst.tour_length(list(t.order))
    check(f"{algo} cached == actual", abs(t.length - actual) < 1e-6,
          f"cached={t.length}, actual={actual}")

print(f"\n=== Results: {passed} passed, {failed} failed ===")
sys.exit(1 if failed > 0 else 0)