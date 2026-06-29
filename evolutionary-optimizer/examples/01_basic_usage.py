#!/usr/bin/env python3
"""Example 01: Basic usage — solve benchmark problems with different algorithms.

This example shows how to use the Python API to:
    - Create a problem instance
    - Configure and run different algorithms
    - Access results, statistics, and history
    - Display ASCII visualization
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from evopt import (
    GeneticAlgorithm, DifferentialEvolution, ParticleSwarmOptimizer,
    CMAES, SimulatedAnnealing,
    Sphere, Rastrigin, Rosenbrock, Ackley,
)
from evopt.utils.visualization import ascii_convergence_plot


def main():
    # --- 1. Solve Sphere (2D) with GA ---
    print("=" * 60)
    print("1. Genetic Algorithm on Sphere (2D)")
    print("=" * 60)
    ga = GeneticAlgorithm(
        Sphere(dims=2), population_size=50, max_generations=100,
        crossover_rate=0.9, mutation_rate=0.1, seed=42, verbose=False,
    )
    best = ga.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {best.genome}")
    print(f"   Generations:  {ga.generation}")
    print()

    # --- 2. Solve Rastrigin (5D) with DE ---
    print("=" * 60)
    print("2. Differential Evolution on Rastrigin (5D)")
    print("=" * 60)
    de = DifferentialEvolution(
        Rastrigin(dims=5), population_size=50, max_generations=200,
        F=0.8, CR=0.9, strategy="rand/1", seed=42,
    )
    best = de.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {[round(x, 4) for x in best.genome]}")
    print()

    # --- 3. Solve Rosenbrock with PSO ---
    print("=" * 60)
    print("3. Particle Swarm Optimization on Rosenbrock (3D)")
    print("=" * 60)
    pso = ParticleSwarmOptimizer(
        Rosenbrock(dims=3), swarm_size=50, max_generations=150, seed=42,
    )
    best = pso.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {[round(x, 4) for x in best.genome]}")
    print()

    # --- 4. Solve Ackley with CMA-ES ---
    print("=" * 60)
    print("4. CMA-ES on Ackley (3D)")
    print("=" * 60)
    cma = CMAES(Ackley(dims=3), max_generations=80, seed=42)
    best = cma.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {[round(x, 6) for x in best.genome]}")
    print()

    # --- 5. Solve Rastrigin with Simulated Annealing ---
    print("=" * 60)
    print("5. Simulated Annealing on Rastrigin (2D)")
    print("=" * 60)
    sa = SimulatedAnnealing(
        Rastrigin(dims=2), max_generations=500,
        initial_temperature=5.0, cooling_rate=0.99,
        steps_per_temperature=20, seed=42,
    )
    best = sa.run()
    print(f"   Best fitness: {best.fitness:.8f}")
    print(f"   Best genome:  {[round(x, 4) for x in best.genome]}")
    print(f"   Acceptance rate: {sa.acceptance_rate:.1%}")
    print()

    # --- 6. Show convergence plot ---
    print("=" * 60)
    print("6. ASCII Convergence Plot (GA on Sphere)")
    print("=" * 60)
    ga2 = GeneticAlgorithm(Sphere(dims=2), population_size=30, max_generations=50, seed=42)
    ga2.run()
    print(ascii_convergence_plot(ga2.history, title="GA Convergence"))

    # --- 7. Summary statistics ---
    print("=" * 60)
    print("7. Statistics Summary")
    print("=" * 60)
    summary = ga.statistics.summary()
    for k, v in summary.items():
        print(f"   {k}: {v}")


if __name__ == "__main__":
    main()