#!/usr/bin/env python3
"""Example 06: CMA-ES on ill-conditioned problems.

CMA-ES excels at ill-conditioned and non-separable problems where other
optimizers struggle. This example demonstrates CMA-ES on the cigar function
(an ill-conditioned problem) and compares it with GA.
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from evopt import CMAES, GeneticAlgorithm, DifferentialEvolution
from evopt.problems.base import ContinuousProblem


class Cigar(ContinuousProblem):
    """Cigar function — ill-conditioned: f(x) = x1^2 + 10^6 * sum(x2..xn^2).

    The condition number is ~10^6, making this very hard for simple optimizers.
    Global minimum: f(0,...,0) = 0.
    """

    def __init__(self, dims=5):
        super().__init__(dims=dims, bounds=(-10, 10), maximize=False)

    def evaluate(self, genome):
        return genome[0] ** 2 + 1e6 * sum(x ** 2 for x in genome[1:])


class Tablet(ContinuousProblem):
    """Tablet function: f(x) = 10^6 * x1^2 + sum(x2..xn^2)."""

    def __init__(self, dims=5):
        super().__init__(dims=dims, bounds=(-10, 10), maximize=False)

    def evaluate(self, genome):
        return 1e6 * genome[0] ** 2 + sum(x ** 2 for x in genome[1:])


def main():
    # --- Cigar function ---
    print("=" * 60)
    print("CMA-ES vs GA vs DE on Cigar (5D, condition ~10^6)")
    print("=" * 60)

    for name, cls in [("CMA-ES", CMAES), ("GA", GeneticAlgorithm), ("DE", DifferentialEvolution)]:
        if name == "CMA-ES":
            algo = cls(Cigar(dims=5), max_generations=200, seed=42)
        elif name == "GA":
            algo = cls(Cigar(dims=5), population_size=50, max_generations=200, seed=42)
        else:
            algo = cls(Cigar(dims=5), population_size=50, max_generations=200, seed=42)
        best = algo.run()
        print(f"   {name:8s}: fitness={best.fitness:.6e}")

    print()

    # --- Tablet function ---
    print("=" * 60)
    print("CMA-ES vs GA vs DE on Tablet (5D)")
    print("=" * 60)

    for name, cls in [("CMA-ES", CMAES), ("GA", GeneticAlgorithm), ("DE", DifferentialEvolution)]:
        if name == "CMA-ES":
            algo = cls(Tablet(dims=5), max_generations=200, seed=42)
        elif name == "GA":
            algo = cls(Tablet(dims=5), population_size=50, max_generations=200, seed=42)
        else:
            algo = cls(Tablet(dims=5), population_size=50, max_generations=200, seed=42)
        best = algo.run()
        print(f"   {name:8s}: fitness={best.fitness:.6e}")

    # --- Show CMA-ES state ---
    print()
    print("=" * 60)
    print("CMA-ES internal state after optimization")
    print("=" * 60)
    cma = CMAES(Cigar(dims=3), max_generations=100, seed=42)
    cma.run()
    import numpy as np
    print(f"   Final sigma:   {cma.sigma:.6e}")
    print(f"   Final mean:    {cma.mean}")
    print(f"   Eigenvalues:   {np.linalg.eigvalsh(cma.C)}")
    print(f"   Condition #:   {max(np.linalg.eigvalsh(cma.C)) / max(min(np.linalg.eigvalsh(cma.C)), 1e-30):.2f}")


if __name__ == "__main__":
    main()