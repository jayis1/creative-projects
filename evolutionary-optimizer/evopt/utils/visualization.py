"""Visualization utilities for evolutionary algorithm results."""

from __future__ import annotations

from typing import List, Optional, Dict, Any
import math


def ascii_convergence_plot(history: List[Dict[str, Any]], width: int = 60,
                            height: int = 15, title: str = "Convergence") -> str:
    """Render an ASCII plot of best/avg fitness over generations.

    Args:
        history: List of per-generation statistics dicts (from algo.history).
        width: Plot width in characters.
        height: Plot height in characters.
        title: Plot title.
    """
    if not history:
        return f"{title}\n(no data)"

    best = [h.get("best_fitness") for h in history if h.get("best_fitness") is not None]
    avg = [h.get("avg_fitness") for h in history if h.get("avg_fitness") is not None]

    if not best:
        return f"{title}\n(no fitness data)"

    all_vals = best + avg
    y_min = min(all_vals)
    y_max = max(all_vals)
    if y_max == y_min:
        y_max = y_min + 1

    n_gens = len(history)
    # Build grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    def to_grid(x_frac, y_val):
        gx = int(x_frac * (width - 1))
        gy = int((y_max - y_val) / (y_max - y_min) * (height - 1))
        return gx, max(0, min(height - 1, gy))

    # Plot avg fitness (dotted)
    if avg:
        for i, v in enumerate(avg):
            x_frac = i / max(n_gens - 1, 1)
            gx, gy = to_grid(x_frac, v)
            if grid[gy][gx] == ' ':
                grid[gy][gx] = '·'

    # Plot best fitness (solid)
    for i, v in enumerate(best):
        x_frac = i / max(n_gens - 1, 1)
        gx, gy = to_grid(x_frac, v)
        grid[gy][gx] = '●'

    # Y-axis labels
    lines = [title]
    for row in range(height):
        y_val = y_max - (row / (height - 1)) * (y_max - y_min)
        lines.append(f"{y_val:10.4f} │{''.join(grid[row])}")
    lines.append(f"{'':11}└{'─' * width}")
    lines.append(f"{'':11} Gen 0{'':>{width - 12}}Gen {n_gens - 1}")
    return "\n".join(lines)


def ascii_pareto_front(pareto_front: List, width: int = 60, height: int = 20,
                       title: str = "Pareto Front") -> str:
    """Render an ASCII scatter plot of a Pareto front (2 objectives only).

    Args:
        pareto_front: List of Individual objects with 'objectives' in metadata.
        width: Plot width.
        height: Plot height.
        title: Plot title.
    """
    if not pareto_front:
        return f"{title}\n(empty Pareto front)"

    objs = [ind.metadata.get('objectives', []) for ind in pareto_front]
    if not objs or len(objs[0]) < 2:
        return f"{title}\n(requires 2 objectives)"

    f1 = [o[0] for o in objs]
    f2 = [o[1] for o in objs]
    x_min, x_max = min(f1), max(f1)
    y_min, y_max = min(f2), max(f2)
    if x_max == x_min:
        x_max = x_min + 1
    if y_max == y_min:
        y_max = y_min + 1

    grid = [[' ' for _ in range(width)] for _ in range(height)]
    for fx, fy in zip(f1, f2):
        gx = int((fx - x_min) / (x_max - x_min) * (width - 1))
        gy = int((y_max - fy) / (y_max - y_min) * (height - 1))
        gx = max(0, min(width - 1, gx))
        gy = max(0, min(height - 1, gy))
        grid[gy][gx] = '◆'

    lines = [title]
    for row in range(height):
        y_val = y_max - (row / (height - 1)) * (y_max - y_min)
        lines.append(f"{y_val:10.4f} │{''.join(grid[row])}")
    lines.append(f"{'':11}└{'─' * width}")
    lines.append(f"{'':11} {x_min:.3f}{'':>{width - 14}}{x_max:.3f}")
    return "\n".join(lines)


def diversity_plot(history: List[Dict[str, Any]], width: int = 60,
                   height: int = 10, title: str = "Population Diversity") -> str:
    """Render an ASCII plot of population diversity over generations."""
    diversity = [h.get("diversity") for h in history if h.get("diversity") is not None]
    if not diversity:
        return f"{title}\n(no data)"

    grid = [[' ' for _ in range(width)] for _ in range(height)]
    n = len(diversity)
    for i, d in enumerate(diversity):
        x_frac = i / max(n - 1, 1)
        gx = int(x_frac * (width - 1))
        gy = int((1.0 - d) * (height - 1))
        gy = max(0, min(height - 1, gy))
        grid[gy][gx] = '▓'

    lines = [title]
    for row in range(height):
        val = 1.0 - row / (height - 1)
        lines.append(f"{val:4.2f} │{''.join(grid[row])}")
    lines.append(f"      └{'─' * width}")
    lines.append(f"       Gen 0{'':>{width - 12}}Gen {n - 1}")
    return "\n".join(lines)