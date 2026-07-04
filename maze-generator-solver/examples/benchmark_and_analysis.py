#!/usr/bin/env python3
"""
Example 2: Benchmarking all solvers and analyzing maze difficulty.

Compares all 7 solvers on the same maze, prints analysis statistics,
and computes a difficulty score.
"""

import os
import sys

# Add parent directory to path so maze_solver is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maze_solver import Maze
from maze_solver.analysis import analyze_maze, difficulty_score


def main():
    maze = Maze(30, 20, seed=42)
    maze.generate("recursive_backtracking")

    print("=== Maze Analysis ===")
    stats = analyze_maze(maze)
    for key, val in stats.items():
        print(f"  {key}: {val}")
    print()

    print("=== Difficulty Score ===")
    score = difficulty_score(maze)
    print(f"  Score: {score:.2f}/100")
    if score < 20:
        print("  Rating: Easy")
    elif score < 40:
        print("  Rating: Medium")
    elif score < 60:
        print("  Rating: Hard")
    elif score < 80:
        print("  Rating: Very Hard")
    else:
        print("  Rating: Extreme")
    print()

    print("=== Solver Benchmark ===")
    results = maze.benchmark()
    print(f"{'Algorithm':<16} {'Found':<6} {'Length':<8} "
          f"{'Explored':<10} {'Time (ms)':<10}")
    print("-" * 52)
    for r in results:
        print(
            f"{r['algorithm']:<16} {str(r['found']):<6} "
            f"{r['path_length']:<8} {r['explored']:<10} "
            f"{r['time_ms']:<10}"
        )
    print()

    # Compare with a different generator.
    maze2 = Maze(30, 20, seed=42)
    maze2.generate("prims")
    from maze_solver.analysis import compare_mazes
    print("=== Compare Recursive Backtracking vs Prim's ===")
    cmp = compare_mazes(maze, maze2)
    for key, val in cmp.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()