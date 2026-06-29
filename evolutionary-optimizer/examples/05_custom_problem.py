#!/usr/bin/env python3
"""Example 05: Custom problem definition.

Demonstrates how to define your own optimization problem by subclassing
ContinuousProblem or Problem, and use it with any EvOpt algorithm.
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from evopt import GeneticAlgorithm, CMAES, DifferentialEvolution
from evopt.problems.base import ContinuousProblem


# --- 1. Simple custom continuous problem ---
class Beale(ContinuousProblem):
    """Beale function — 2D unimodal benchmark.

    f(x, y) = (1.5 - x + xy)^2 + (2.25 - x + xy^2)^2 + (2.625 - x + xy^3)^2
    Global minimum: f(3, 0.5) = 0
    """

    def __init__(self):
        super().__init__(dims=2, bounds=(-4.5, 4.5), maximize=False)

    def evaluate(self, genome):
        x, y = genome
        return ((1.5 - x + x * y) ** 2
                + (2.25 - x + x * y ** 2) ** 2
                + (2.625 - x + x * y ** 3) ** 2)


# --- 2. Constrained problem ---
class ConstrainedQuadratic(ContinuousProblem):
    """Minimize sum(x^2) subject to sum(x) >= 1.

    The constraint is handled via a penalty function.
    """

    def __init__(self, dims=3):
        super().__init__(dims=dims, bounds=(-5, 5), maximize=False)
        # Add a constraint: sum(x) - 1 >= 0, i.e., -(sum(x) - 1) <= 0
        self.constraints = [lambda g: 1.0 - sum(g)]  # > 0 means violated

    def evaluate(self, genome):
        return sum(x * x for x in genome)


# --- 3. Custom multi-objective problem ---
from evopt.algorithms.nsga2 import MultiObjectiveProblem

class Schaffer(MultiObjectiveProblem):
    """Schaffer's multi-objective problem.

    f1(x) = x^2
    f2(x) = (x - 2)^2

    Pareto front: x in [0, 2].
    """

    def __init__(self):
        super().__init__(maximize_list=[False, False])
        self.bounds = [(-5, 5)]

    def evaluate_multi(self, genome):
        x = genome[0]
        return [x ** 2, (x - 2) ** 2]

    def random_genome(self):
        import random
        return [random.uniform(-5, 5)]

    def genome_size(self):
        return 1


def main():
    # --- Solve Beale with GA ---
    print("=" * 60)
    print("1. GA on Beale function (2D)")
    print("=" * 60)
    ga = GeneticAlgorithm(Beale(), population_size=50, max_generations=100, seed=42)
    best = ga.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {[round(x, 4) for x in best.genome]}")
    print(f"   (Expected: [3.0, 0.5])")
    print()

    # --- Solve Beale with CMA-ES ---
    print("=" * 60)
    print("2. CMA-ES on Beale function (2D)")
    print("=" * 60)
    cma = CMAES(Beale(), max_generations=50, seed=42)
    best = cma.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {[round(x, 4) for x in best.genome]}")
    print()

    # --- Constrained problem ---
    print("=" * 60)
    print("3. DE on constrained quadratic (sum(x^2) s.t. sum(x) >= 1)")
    print("=" * 60)
    de = DifferentialEvolution(ConstrainedQuadratic(dims=3), population_size=30,
                                max_generations=100, seed=42)
    best = de.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {[round(x, 4) for x in best.genome]}")
    print(f"   Constraints:  {best.constraints}")
    print()

    # --- Multi-objective Schaffer ---
    print("=" * 60)
    print("4. NSGA-II on Schaffer's problem")
    print("=" * 60)
    from evopt import NSGA2
    nsga = NSGA2(Schaffer(), population_size=50, max_generations=50, seed=42)
    nsga.run()
    pareto = nsga.pareto_front
    print(f"   Pareto front size: {len(pareto)}")
    for ind in pareto[:5]:
        print(f"     x={ind.genome[0]:.4f}  objs={ind.metadata['objectives']}")


if __name__ == "__main__":
    main()