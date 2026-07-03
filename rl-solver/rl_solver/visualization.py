"""ASCII visualization tools for MDP value functions, policies, and Q-tables."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .mdp import MDP
from .planners import Policy


# Arrow mapping for grid directions
ARROWS = {"N": "↑", "S": "↓", "E": "→", "W": "←", None: "·", "pickup": "P", "dropoff": "D"}


def render_value_heatmap(
    mdp: MDP,
    V: Dict[Any, float],
    width: int = 8,
    show_states: bool = True,
) -> str:
    """Render a value function as an ASCII heatmap for 2D grid MDPs.

    Detects grid dimensions from (row, col) state tuples.  Non-grid MDPs
    fall back to a sorted list.
    """
    # detect grid
    grid_states = [(s[0], s[1]) for s in mdp.states if isinstance(s, tuple) and len(s) == 2]
    if grid_states and len(grid_states) == len(mdp.states):
        return _render_grid_values(grid_states, V, width)
    else:
        return _render_list_values(mdp.states, V, width)


def _render_grid_values(states, V, width) -> str:
    rows = max(r for r, c in states) + 1
    cols = max(c for r, c in states) + 1
    # find min/max for color scaling
    vals = [V.get((r, c), 0.0) for r in range(rows) for c in range(cols)]
    vmin, vmax = min(vals), max(vals)
    vrange = vmax - vmin if vmax != vmin else 1.0
    lines = []
    for r in range(rows):
        row_parts = []
        for c in range(cols):
            v = V.get((r, c), 0.0)
            # color bar
            norm = (v - vmin) / vrange
            bar_len = max(1, int(norm * (width - 4)))
            bar = "█" * bar_len + "░" * (width - 4 - bar_len)
            row_parts.append(f"{v:>{width-5}.3f}{bar}")
        lines.append(" ".join(row_parts))
    return "\n".join(lines)


def _render_list_values(states, V, width) -> str:
    lines = []
    for s in sorted(states, key=str):
        lines.append(f"  {str(s):<20} {V.get(s, 0.0):>{width}.4f}")
    return "\n".join(lines)


def render_policy_grid(mdp: MDP, pi: Policy, rows: Optional[int] = None, cols: Optional[int] = None) -> str:
    """Render a policy as arrows on a grid (for grid MDPs)."""
    grid_states = [s for s in mdp.states if isinstance(s, tuple) and len(s) == 2]
    if not grid_states or len(grid_states) != len(mdp.states):
        # fallback: list
        lines = []
        for s in sorted(mdp.states, key=str):
            a = pi[s]
            lines.append(f"  {str(s):<20} -> {a}")
        return "\n".join(lines)
    if rows is None:
        rows = max(s[0] for s in grid_states) + 1
    if cols is None:
        cols = max(s[1] for s in grid_states) + 1
    r_max: int = int(rows)
    c_max: int = int(cols)
    lines = []
    for r in range(r_max):
        row_parts = []
        for c in range(c_max):
            a = pi[(r, c)]
            symbol = ARROWS.get(a, str(a)[:3])
            row_parts.append(f"  {symbol}  ")
        lines.append("".join(row_parts))
    return "\n".join(lines)


def render_q_table(
    Q: Dict[Any, Dict[Any, float]],
    precision: int = 3,
    max_states: int = 50,
) -> str:
    """Render a Q-table as a formatted table."""
    states = sorted(Q.keys(), key=str)[:max_states]
    if not states:
        return "(empty Q-table)"
    # collect all actions
    all_actions = []
    for s in states:
        for a in Q.get(s, {}):
            if a not in all_actions:
                all_actions.append(a)
    # header
    col_w = max(8, precision + 5)
    state_w = 15
    header = f"{'State':<{state_w}}" + "".join(f"{str(a):>{col_w}}" for a in all_actions)
    sep = "-" * len(header)
    lines = [header, sep]
    for s in states:
        row = f"{str(s):<{state_w}}"
        for a in all_actions:
            v = Q.get(s, {}).get(a, 0.0)
            row += f"{v:>{col_w}.{precision}f}"
        lines.append(row)
    if len(Q) > max_states:
        lines.append(f"... ({len(Q) - max_states} more states)")
    return "\n".join(lines)


def render_learning_curve(
    rewards: List[float],
    width: int = 60,
    height: int = 15,
    title: str = "Learning Curve",
) -> str:
    """Render an ASCII learning curve from episode rewards."""
    if not rewards:
        return f"{title}\n(no data)"
    n = len(rewards)
    rmin, rmax = min(rewards), max(rewards)
    rrange = rmax - rmin if rmax != rmin else 1.0
    lines = [title]
    # top border
    lines.append(f"  {rmax:.3f} ┌{'─' * width}┐")
    for row in range(height, 0, -1):
        threshold = rmin + (row / height) * rrange
        chars = []
        for col in range(width):
            idx = int((col / width) * n)
            idx = min(idx, n - 1)
            if rewards[idx] >= threshold:
                chars.append("●")
            else:
                chars.append(" ")
        label = ""
        if row == height:
            label = f"  ({len(rewards)} episodes)"
        lines.append(f"         │{''.join(chars)}│{label}")
    lines.append(f"  {rmin:.3f} └{'─' * width}┘")
    lines.append(f"         0{' ' * (width - len(str(n)))}{n}")
    return "\n".join(lines)


__all__ = [
    "render_value_heatmap",
    "render_policy_grid",
    "render_q_table",
    "render_learning_curve",
]