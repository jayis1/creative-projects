"""
Maze analysis, difficulty scoring, and comparison utilities.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .core import Cell, Direction


def analyze_maze(maze) -> Dict[str, Any]:
    """Analyze the maze structure and return statistics.

    Returns
    -------
    dict
        Keys: ``width``, ``height``, ``total_cells``,
        ``total_walls_remaining``, ``dead_ends``, ``corridors``,
        ``junctions``, ``solution_length``, ``has_solution``,
        ``is_perfect``, ``braid_ratio``, ``difficulty_score``.
    """
    dead_ends = 0
    junctions = 0
    corridors = 0
    total_walls = 0
    for cell in maze.all_cells():
        oc = cell.open_count
        if oc == 1:
            dead_ends += 1
        elif oc >= 3:
            junctions += 1
        elif oc == 2:
            corridors += 1
        total_walls += len(cell.walls)
    solution = maze.solve("bfs")
    solution_length = len(solution) if solution else 0
    n = maze.width * maze.height
    is_perfect = maze.is_perfect()
    diff = difficulty_score(maze, solution_length=solution_length,
                            dead_ends=dead_ends, junctions=junctions)
    return {
        "width": maze.width,
        "height": maze.height,
        "total_cells": n,
        "total_walls_remaining": total_walls,
        "dead_ends": dead_ends,
        "corridors": corridors,
        "junctions": junctions,
        "solution_length": solution_length,
        "has_solution": solution is not None,
        "is_perfect": is_perfect,
        "braid_ratio": round((n - dead_ends) / n, 4) if n else 0,
        "difficulty_score": round(diff, 2),
    }


def difficulty_score(
    maze,
    solution_length: Optional[int] = None,
    dead_ends: Optional[int] = None,
    junctions: Optional[int] = None,
) -> float:
    """Compute a difficulty score (0–100) for the maze.

    The score considers:
    - **Solution length** relative to the theoretical minimum (Manhattan
      distance from start to end) — longer solutions mean more twists.
    - **Dead-end density** — more dead ends means more wrong turns.
    - **Junction density** — more junctions means more decision points.

    Parameters
    ----------
    maze : Maze
        The maze to score.
    solution_length : int, optional
        Pre-computed BFS solution length (avoids re-solving).
    dead_ends : int, optional
        Pre-computed dead-end count.
    junctions : int, optional
        Pre-computed junction count.

    Returns
    -------
    float
        Difficulty score from 0 (trivial) to 100 (very hard).
    """
    n = maze.width * maze.height
    if n == 0:
        return 0.0

    # Compute metrics if not provided.
    if solution_length is None:
        sol = maze.solve("bfs")
        solution_length = len(sol) if sol else 0
    if dead_ends is None or junctions is None:
        de, jun = 0, 0
        for cell in maze.all_cells():
            oc = cell.open_count
            if oc == 1:
                de += 1
            elif oc >= 3:
                jun += 1
        if dead_ends is None:
            dead_ends = de
        if junctions is None:
            junctions = jun

    # Theoretical minimum path length (Manhattan distance).
    sx, sy = maze.start
    ex, ey = maze.end
    min_path = abs(ex - sx) + abs(ey - sy)
    if min_path == 0:
        min_path = 1  # avoid division by zero for 1x1 mazes

    # Twist factor: how much longer the solution is vs minimum.
    twist = solution_length / min_path if min_path > 0 else 1.0
    # Dead-end density: fraction of cells that are dead ends.
    de_density = dead_ends / n
    # Junction density: fraction of cells that are junctions.
    jun_density = junctions / n

    # Weighted combination, scaled to 0-100.
    # twist typically ranges 1-5, de_density 0-0.5, jun_density 0-0.4
    score = (
        min(twist / 5.0, 1.0) * 40  # 40% weight on twistiness
        + min(de_density / 0.5, 1.0) * 30  # 30% weight on dead ends
        + min(jun_density / 0.4, 1.0) * 30  # 30% weight on junctions
    )
    return min(max(score, 0.0), 100.0)


def compare_mazes(maze_a, maze_b) -> Dict[str, Any]:
    """Compare two mazes and report structural differences.

    Parameters
    ----------
    maze_a, maze_b : Maze
        The two mazes to compare.  They must have the same dimensions.

    Returns
    -------
    dict
        Keys: ``same_dimensions``, ``same_walls`` (number of cells
        with different wall sets), ``wall_diff_count`` (total wall
        differences), ``solution_length_diff``, ``dead_end_diff``,
        ``junction_diff``, ``difficulty_diff``.
    """
    same_dims = maze_a.width == maze_b.width and maze_a.height == maze_b.height
    result: Dict[str, Any] = {
        "same_dimensions": same_dims,
        "same_walls": 0,
        "wall_diff_count": 0,
        "solution_length_diff": 0,
        "dead_end_diff": 0,
        "junction_diff": 0,
        "difficulty_diff": 0.0,
    }
    if not same_dims:
        return result

    wall_diff_cells = 0
    total_wall_diffs = 0
    for y in range(maze_a.height):
        for x in range(maze_a.width):
            ca = maze_a.cells[y][x]
            cb = maze_b.cells[y][x]
            diff = ca.walls.symmetric_difference(cb.walls)
            if diff:
                wall_diff_cells += 1
                total_wall_diffs += len(diff)

    result["same_walls"] = maze_a.width * maze_a.height - wall_diff_cells
    result["wall_diff_count"] = total_wall_diffs

    stats_a = analyze_maze(maze_a)
    stats_b = analyze_maze(maze_b)
    result["solution_length_diff"] = (
        stats_b["solution_length"] - stats_a["solution_length"]
    )
    result["dead_end_diff"] = stats_b["dead_ends"] - stats_a["dead_ends"]
    result["junction_diff"] = stats_b["junctions"] - stats_a["junctions"]
    result["difficulty_diff"] = round(
        stats_b["difficulty_score"] - stats_a["difficulty_score"], 2
    )
    return result