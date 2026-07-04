#!/usr/bin/env python3
"""
Example 1: Basic generation and solving.

Demonstrates creating a maze, generating with different algorithms,
solving with different solvers, and rendering.
"""

import os
import sys

# Add parent directory to path so maze_solver is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maze_solver import Maze


def main():
    # Create a 20x10 maze with a fixed seed for reproducibility.
    maze = Maze(20, 10, seed=42)

    # Generate using recursive backtracking.
    maze.generate("recursive_backtracking")
    print("=== Recursive Backtracking ===")
    print(maze.render())
    print()

    # Solve using BFS (shortest path).
    solution = maze.solve("bfs")
    print(f"BFS solution: {len(solution)} steps")
    print(maze.render(solution=solution))
    print()

    # Solve using A* with Manhattan heuristic.
    solution_astar = maze.solve("astar", heuristic="manhattan")
    print(f"A* solution: {len(solution_astar)} steps (same as BFS = optimal)")
    print()

    # Solve using DFS (may not be shortest).
    solution_dfs = maze.solve("dfs")
    print(f"DFS solution: {len(solution_dfs)} steps (may differ from BFS)")
    print()

    # Solve using IDA* (memory-efficient optimal).
    solution_ida = maze.solve("ida_star")
    print(f"IDA* solution: {len(solution_ida)} steps (optimal, low memory)")
    print()


if __name__ == "__main__":
    main()