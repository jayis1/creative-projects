"""Example: using advanced metaheuristics (ILS, Lin-Kernighan).

Run with::

    python3 examples/advanced_algorithms.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve
from tsp_solver.heuristics import nearest_neighbor
from tsp_solver.advanced import iterated_local_search, lin_kernighan, savings
from tsp_solver.exact import held_karp

def main():
    inst = generate_instance(20, seed=42, name="advanced_demo")
    print(f"Instance: {inst}")

    # Optimal (for comparison)
    opt = held_karp(inst)
    print(f"\nOptimal (Held-Karp):    {opt.length:.2f}")

    # Savings construction
    sav = solve(inst, "savings")
    print(f"Savings:                {sav.length:.2f}  (ratio={sav.length/opt.length:.3f})")

    # ILS
    ils = solve(inst, "iterated_local_search", seed=42, max_iter=200)
    print(f"Iterated Local Search:  {ils.length:.2f}  (ratio={ils.length/opt.length:.3f})")

    # Lin-Kernighan
    lk = solve(inst, "lin_kernighan", seed=42, max_iter=500)
    print(f"Lin-Kernighan:           {lk.length:.2f}  (ratio={lk.length/opt.length:.3f})")

    # Compare with basic heuristics
    nn = nearest_neighbor(inst)
    print(f"Nearest Neighbor:       {nn.length:.2f}  (ratio={nn.length/opt.length:.3f})")

    # ILS with 3-opt local search
    ils3 = iterated_local_search(inst, nn, seed=42, max_iter=200, local_search="three_opt")
    print(f"ILS (3-opt):            {ils3.length:.2f}  (ratio={ils3.length/opt.length:.3f})")


if __name__ == "__main__":
    main()