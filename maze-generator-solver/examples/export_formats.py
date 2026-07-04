#!/usr/bin/env python3
"""
Example 3: Exporting mazes to PNG and SVG.

Demonstrates exporting mazes to image formats with solution paths
drawn on top.
"""

import os
import sys

# Add parent directory to path so maze_solver is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maze_solver import Maze


def main():
    maze = Maze(20, 15, seed=42)
    maze.generate("recursive_backtracking")

    # Solve with A*.
    solution = maze.solve("astar", heuristic="manhattan")
    print(f"Solution: {len(solution)} steps")

    # Export as PNG (pure stdlib, no PIL needed).
    maze.to_png("maze.png", cell_size=20, wall_thickness=2, solution=solution)
    print("Exported: maze.png")

    # Export as SVG (resolution-independent, scalable).
    maze.to_svg("maze.svg", cell_size=30, wall_width=3, solution=solution)
    print("Exported: maze.svg")

    # Braid the maze and export again.
    maze.braid(0.8)
    solution_braided = maze.solve("astar")
    maze.to_png("maze_braided.png", cell_size=20, solution=solution_braided)
    maze.to_svg("maze_braided.svg", cell_size=30, solution=solution_braided)
    print("Exported: maze_braided.png, maze_braided.svg")


if __name__ == "__main__":
    main()