#!/usr/bin/env python3
"""Example: Generate and solve KenKen puzzles of various sizes.

This example demonstrates the basic API for generating puzzles, solving them,
and analyzing their difficulty.

Usage:
    python3 examples/generate_and_solve.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenken_solver import (
    KenKenGenerator,
    KenKenSolver,
    PuzzleAnalyzer,
    render_puzzle,
    render_solved_puzzle,
)


def main() -> None:
    # Generate puzzles of various sizes and difficulties
    configs = [
        (3, "easy", 1),
        (4, "medium", 42),
        (5, "medium", 100),
        (6, "hard", 7),
    ]

    for size, difficulty, seed in configs:
        print(f"\n{'='*60}")
        print(f"  {size}×{size} {difficulty} puzzle (seed={seed})")
        print(f"{'='*60}\n")

        # Generate
        gen = KenKenGenerator(size=size, seed=seed, difficulty=difficulty)
        puzzle = gen.generate()

        # Show the puzzle
        print("Puzzle:")
        print(render_puzzle(puzzle))
        print()

        # Solve
        solver = KenKenSolver(puzzle)
        grid = solver.solve_grid()
        print("Solution:")
        print(render_solved_puzzle(puzzle, grid))
        print()

        # Analyze
        analyzer = PuzzleAnalyzer(puzzle)
        analysis = analyzer.analyze()
        print(f"Difficulty: {analysis['difficulty_category']} "
              f"(score={analysis['difficulty_score']})")
        print(f"Cages: {analysis['num_cages']}, "
              f"avg size: {analysis['avg_cage_size']}")
        print(f"Operators: {analysis['operator_distribution']}")
        print(f"Solver nodes: {analysis['solver_nodes']}, "
              f"backtracks: {analysis['solver_backtracks']}")
        print(f"Unique: {solver.count_solutions() == 1}")


if __name__ == "__main__":
    main()