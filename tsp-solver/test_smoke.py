#!/usr/bin/env python3
"""Quick smoke test for the TSP solver."""
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve, list_algorithms

print('Algorithms:', list_algorithms())
inst = generate_instance(10, seed=42)
print('Instance:', inst)

t = solve(inst, 'nearest_neighbor')
print('NN:', t)

t2 = solve(inst, 'christofides', refine='two_opt')
print('Christofides+2opt:', t2)

t3 = solve(inst, 'held_karp')
print('Held-Karp (optimal):', t3)

t4 = solve(inst, 'simulated_annealing', seed=42)
print('SA:', t4)

t5 = solve(inst, 'genetic_algorithm', seed=42, generations=50)
print('GA:', t5)

t6 = solve(inst, 'ant_colony', seed=42, n_iterations=50)
print('ACO:', t6)

t7 = solve(inst, 'greedy')
print('Greedy:', t7)

t8 = solve(inst, 'mst_approx')
print('MST approx:', t8)

t9 = solve(inst, 'nearest_insertion')
print('Nearest insertion:', t9)

t10 = solve(inst, 'farthest_insertion')
print('Farthest insertion:', t10)

t11 = solve(inst, 'branch_and_bound')
print('B&B:', t11)

t12 = solve(inst, 'two_opt')
print('2-opt from NN:', t12)

t13 = solve(inst, 'or_opt')
print('Or-opt:', t13)

t14 = solve(inst, 'three_opt', refine='two_opt')
print('3-opt+2-opt:', t14)

print()
print('=== Comparison ===')
for algo in list_algorithms():
    tour = solve(inst, algo, seed=42)
    optimal = t3.length
    ratio = tour.length / optimal if optimal > 0 else 0
    print(f'{algo:<25} len={tour.length:>8.2f}  ratio={ratio:.3f}')
print(f'Optimal (Held-Karp): {t3.length:.2f}')