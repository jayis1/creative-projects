"""
Example: Evolve warriors using a genetic algorithm.

This script demonstrates using the genetic evolver to automatically
create warriors through evolutionary computation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_war import load_warrior, GeneticEvolver

WARRIORS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warriors")


def main():
    # Load opponents for fitness evaluation
    opponents = [
        load_warrior(os.path.join(WARRIORS_DIR, "imp.red")),
        load_warrior(os.path.join(WARRIORS_DIR, "dwarf.red")),
        load_warrior(os.path.join(WARRIORS_DIR, "stone.red")),
    ]

    # Load seed warriors for initial population
    seeds = [
        load_warrior(os.path.join(WARRIORS_DIR, "imp.red")),
        load_warrior(os.path.join(WARRIORS_DIR, "dwarf.red")),
    ]

    print("Genetic Evolution Setup:")
    print(f"  Population: 20")
    print(f"  Generations: 10")
    print(f"  Opponents: {[w.name for w in opponents]}")
    print(f"  Seeds: {[w.name for w in seeds]}")
    print(f"  Mutation rate: 0.15")
    print()

    # Create and run evolver
    evolver = GeneticEvolver(
        population_size=20,
        generations=10,
        opponents=opponents,
        core_size=8000,
        max_cycles=5000,
        rounds_per_battle=2,
        mutation_rate=0.15,
        seed=42,
    )

    # Track progress
    def on_generation(gen, stats):
        print(f"  Gen {gen:3d}: best={stats.best_fitness:.1f}, "
              f"avg={stats.avg_fitness:.1f}, "
              f"diversity={stats.diversity:.0%}, "
              f"best={stats.best_individual}")

    best = evolver.evolve(seed_warriors=seeds, on_generation=on_generation)

    # Show results
    print(f"\n{'=' * 60}")
    print(f"Evolution Complete!")
    print(f"{'=' * 60}")
    print(f"  Best warrior:   {best.name}")
    print(f"  Fitness:        {best.fitness:.1f}")
    print(f"  Generation:     {best.generation}")
    print(f"  Win rate:       {best.win_rate:.1%}")
    print(f"  Instructions:   {len(best.genome)}")
    print()

    # Save best warrior
    output_path = os.path.join(WARRIORS_DIR, "evolved.red")
    evolver.save_best(output_path)
    print(f"  Saved to: {output_path}")
    print()

    # Show evolution history
    print("Evolution History:")
    print(f"  {'Gen':>4} {'Best':>8} {'Avg':>8} {'Worst':>8} {'Diversity':>10}")
    print("  " + "-" * 42)
    for stat in evolver.history:
        print(f"  {stat.generation:>4} {stat.best_fitness:>8.1f} "
              f"{stat.avg_fitness:>8.1f} {stat.worst_fitness:>8.1f} "
              f"{stat.diversity:>10.0%}")


if __name__ == "__main__":
    main()