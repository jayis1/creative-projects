#!/usr/bin/env python3
"""Example 07: Simulated Annealing with custom cooling schedules.

Demonstrates:
    - Different cooling schedules (geometric, linear, logarithmic)
    - Custom move functions
    - Restart/reheat on stagnation
    - Tracking acceptance rates
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from evopt import SimulatedAnnealing, Rastrigin, Sphere, Ackley


def main():
    # --- 1. Different cooling schedules ---
    print("=" * 60)
    print("1. SA with different cooling schedules on Rastrigin (2D)")
    print("=" * 60)
    for schedule in ["geometric", "linear", "logarithmic"]:
        sa = SimulatedAnnealing(
            Rastrigin(dims=2), max_generations=500,
            cooling_schedule=schedule,
            initial_temperature=5.0,
            cooling_rate=0.995,
            steps_per_temperature=20,
            seed=42,
        )
        best = sa.run()
        print(f"   {schedule:12s}: fitness={best.fitness:.6f}, "
              f"T_final={sa.temperature:.4e}, "
              f"accept_rate={sa.acceptance_rate:.1%}, "
              f"restarts={sa._restarts}")

    print()

    # --- 2. Custom move function (large steps early, small steps late) ---
    print("=" * 60)
    print("2. SA with custom adaptive move function on Ackley (2D)")
    print("=" * 60)

    def adaptive_move(genome, temperature):
        """Take large steps when hot, small steps when cold."""
        sigma = max(temperature * 0.5, 0.001)
        return [g + random.gauss(0, sigma) for g in genome]

    import random
    random.seed(42)
    sa = SimulatedAnnealing(
        Ackley(dims=2), max_generations=500,
        initial_temperature=3.0, cooling_rate=0.99,
        steps_per_temperature=15,
        move_fn=adaptive_move,
        seed=42,
    )
    best = sa.run()
    print(f"   Best fitness:  {best.fitness:.6f}")
    print(f"   Accept rate:   {sa.acceptance_rate:.1%}")
    print(f"   Restarts:      {sa._restarts}")

    print()

    # --- 3. With vs without restart ---
    print("=" * 60)
    print("3. SA with vs without restart on Rastrigin (3D)")
    print("=" * 60)
    for restart in [True, False]:
        sa = SimulatedAnnealing(
            Rastrigin(dims=3), max_generations=500,
            initial_temperature=5.0, cooling_rate=0.99,
            steps_per_temperature=20,
            restart_on_stagnation=restart,
            stagnation_patience=50,
            seed=42,
        )
        best = sa.run()
        label = "with restart" if restart else "no restart"
        print(f"   {label:15s}: fitness={best.fitness:.6f}, restarts={sa._restarts}")


if __name__ == "__main__":
    main()