#!/usr/bin/env python3
"""Example 02: Multi-objective optimization with NSGA-II and indicators.

Demonstrates:
    - Solving ZDT1 and ZDT2 multi-objective benchmarks
    - Extracting the Pareto front
    - Computing hypervolume, IGD, spacing, and spread indicators
    - Visualizing the Pareto front
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from evopt import NSGA2
from evopt.problems.multi_objective import ZDT1, ZDT2
from evopt.indicators import hypervolume, inverted_generational_distance, spacing, spread
from evopt.utils.visualization import ascii_pareto_front


def main():
    # --- Solve ZDT1 ---
    print("=" * 60)
    print("NSGA-II on ZDT1 (10D, 100 generations)")
    print("=" * 60)
    nsga = NSGA2(ZDT1(dims=10), population_size=100, max_generations=100, seed=42)
    nsga.run()
    pareto = nsga.pareto_front
    print(f"   Pareto front size: {len(pareto)}")

    # Extract objectives
    objs = [ind.metadata["objectives"] for ind in pareto]
    f1 = [o[0] for o in objs]
    f2 = [o[1] for o in objs]
    print(f"   f1 range: [{min(f1):.4f}, {max(f1):.4f}]")
    print(f"   f2 range: [{min(f2):.4f}, {max(f2):.4f}]")

    # Compute indicators (reference point = worst + margin)
    ref = [max(f1) + 0.1, max(f2) + 0.1]
    hv = hypervolume(objs, ref)
    sp = spacing(objs)
    print(f"   Hypervolume: {hv:.6f}")
    print(f"   Spacing:     {sp:.6f}")

    # Generate a reference Pareto front for IGD (true ZDT1 front: f2 = 1 - sqrt(f1))
    import math
    true_front = [[i / 100, 1 - math.sqrt(i / 100)] for i in range(101)]
    igd = inverted_generational_distance(objs, true_front)
    print(f"   IGD:         {igd:.6f}")

    # Visualize
    print()
    print(ascii_pareto_front(pareto, title="NSGA-II Pareto Front (ZDT1)"))

    # --- Solve ZDT2 ---
    print()
    print("=" * 60)
    print("NSGA-II on ZDT2 (10D, 100 generations)")
    print("=" * 60)
    nsga2 = NSGA2(ZDT2(dims=10), population_size=100, max_generations=100, seed=42)
    nsga2.run()
    pareto2 = nsga2.pareto_front
    objs2 = [ind.metadata["objectives"] for ind in pareto2]
    ref2 = [max(o[0] for o in objs2) + 0.1, max(o[1] for o in objs2) + 0.1]
    hv2 = hypervolume(objs2, ref2)
    print(f"   Pareto front size: {len(pareto2)}")
    print(f"   Hypervolume: {hv2:.6f}")


if __name__ == "__main__":
    main()