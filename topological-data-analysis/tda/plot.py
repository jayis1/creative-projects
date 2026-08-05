"""
ASCII rendering of persistence diagrams.

Produces scatter-plot style ASCII art where each persistence pair is shown
as a character on a 2D (birth, death) plane with the diagonal drawn.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .diagram import PersistenceDiagram

Infinity = float("inf")


def plot_diagram_ascii(
    diagrams: Dict[int, PersistenceDiagram],
    width: int = 60,
    height: int = 30,
    dims: Optional[List[int]] = None,
) -> str:
    """Render persistence diagrams as an ASCII scatter plot.

    Each point (birth, death) is plotted on a 2D grid. The diagonal
    (birth == death) is drawn as a line. Different dimensions use different
    characters:

        H0: 'o'   H1: 'x'   H2: '+'   H3: '#'   H4+: '@'

    Essential cycles (death = inf) are shown at the top of the plot.

    Parameters
    ----------
    diagrams : dict of dimension -> PersistenceDiagram
    width, height : int
        Output dimensions in characters.
    dims : list of int, optional
        Which dimensions to plot. Default: all available.

    Returns
    -------
    str
        Multi-line ASCII string.
    """
    if dims is None:
        dims = sorted(diagrams.keys())

    dim_chars = {0: "o", 1: "x", 2: "+", 3: "#", 4: "%", 5: "&"}
    char_for = lambda d: dim_chars.get(d, "@")

    # Collect all finite points.
    all_finite: List[Tuple[float, float, int]] = []
    essential_count = 0
    for dim in dims:
        if dim not in diagrams:
            continue
        for pair in diagrams[dim]:
            if pair.death == Infinity:
                essential_count += 1
            else:
                all_finite.append((pair.birth, pair.death, dim))

    if not all_finite:
        if essential_count:
            return f"(no finite points; {essential_count} essential cycles shown at top)"
        return "(empty diagram)"

    # Compute ranges.
    all_vals = []
    for b, d, _ in all_finite:
        all_vals.extend([b, d])

    v_min = min(all_vals)
    v_max = max(all_vals)
    if v_max == v_min:
        v_max = v_min + 1.0

    # Leave room for axis labels.
    plot_w = width - 8
    plot_h = height - 3

    def to_x(val: float) -> int:
        return int((val - v_min) / (v_max - v_min) * (plot_w - 1))

    def to_y(val: float) -> int:
        return int((val - v_min) / (v_max - v_min) * (plot_h - 1))

    # Build the grid.
    grid: List[List[str]] = [[" "] * plot_w for _ in range(plot_h)]

    # Draw diagonal (y = x in data space → row = col in plot space, approximately).
    for i in range(min(plot_w, plot_h)):
        grid[plot_h - 1 - i][i] = "."

    # Plot points.
    for b, d, dim in all_finite:
        col = to_x(b)
        row = plot_h - 1 - to_y(d)
        if 0 <= row < plot_h and 0 <= col < plot_w:
            existing = grid[row][col]
            if existing == " " or existing == ".":
                grid[row][col] = char_for(dim)
            else:
                # Multiple points at same location.
                grid[row][col] = "*"

    # Add essential cycle markers at top.
    if essential_count:
        for i in range(min(essential_count, plot_w)):
            grid[0][i] = "∞"

    # Format output.
    lines: List[str] = []
    # Y-axis label and values.
    for r in range(plot_h):
        val = v_max - (r / max(1, plot_h - 1)) * (v_max - v_min)
        lines.append(f"{val:6.2f} |{''.join(grid[r])}")

    # X-axis.
    lines.append("       " + "-" * plot_w)
    x_axis = f"       {v_min:.2f}" + " " * (plot_w - 12) + f"{v_max:.2f}"
    lines.append(x_axis)

    # Legend.
    legend_parts = [f"H{d}={char_for(d)}" for d in dims if d in diagrams]
    legend_parts.append("diag=.")
    if essential_count:
        legend_parts.append("∞=essential")
    legend_parts.append("*=overlap")
    lines.append("  Legend: " + "  ".join(legend_parts))

    return "\n".join(lines)