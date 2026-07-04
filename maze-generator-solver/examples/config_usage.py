#!/usr/bin/env python3
"""
Example 4: Using configuration files for declarative maze generation.

Shows how to load a JSON config file to generate mazes without
writing code — ideal for batch processing or user-customizable mazes.
"""

import json
import os
import sys

# Add parent directory to path so maze_solver is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maze_solver.io_utils import load_config, maze_from_config


def main():
    # Load the config file.
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "config.json"
    )
    config = load_config(config_path)
    print("=== Configuration ===")
    print(json.dumps(config, indent=2))
    print()

    # Create the maze from config.
    maze = maze_from_config(config)
    print(f"Maze: {maze.width}x{maze.height}")
    print(f"Generator: {config['generator']}")
    print(f"Braid: {config.get('braid')}")
    print()

    # Solve and display.
    solution = maze.solve(config.get("solver", "bfs"),
                          heuristic=config.get("heuristic", "manhattan"))
    if solution:
        print(maze.render(solution=solution))
        print(f"\nSolution: {len(solution)} steps")
    print()

    # Analyze.
    stats = maze.analyze()
    print("=== Analysis ===")
    for key, val in stats.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()