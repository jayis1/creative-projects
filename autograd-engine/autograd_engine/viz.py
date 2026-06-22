"""Computation-graph visualization utilities.

Generates Graphviz DOT format output of the computation graph rooted at a
given ``Value`` node.  This can be rendered with the ``dot`` command-line
tool or any Graphviz-compatible viewer.

Example
-------
>>> from autograd_engine import Value
>>> from autograd_engine.viz import to_dot, draw_dot
>>> x = Value(2.0, label="x")
>>> y = x ** 2 + 3 * x + 1
>>> y.backward()
>>> print(to_dot(y))         # DOT source as a string
>>> draw_dot(y, "graph.dot") # write to file
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set

from .engine import Value


def _node_id(v: Value) -> str:
    return f"node{id(v)}"


def _fmt(x: float) -> str:
    """Format a float compactly."""
    if x == 0:
        return "0"
    if abs(x) < 1e-4 or abs(x) >= 1e6:
        return f"{x:.2e}"
    return f"{x:.4f}"


def to_dot(root: Value, title: Optional[str] = None) -> str:
    """Generate Graphviz DOT source for the computation graph.

    Each node shows its label (if set), operation, data, and gradient.
    Edges connect operation nodes to their inputs.
    """
    lines = ["digraph autograd {"]
    lines.append("  rankdir=LR;")
    lines.append('  node [shape=record, fontsize=10];')
    if title:
        lines.append(f'  label="{title}";')
        lines.append("  labelloc=t;")

    visited: Set[int] = set()
    nodes: list[Value] = []

    def collect(v: Value) -> None:
        if id(v) in visited:
            return
        visited.add(id(v))
        for child in v._prev:
            collect(child)
        nodes.append(v)

    collect(root)

    # Emit node definitions
    for v in nodes:
        nid = _node_id(v)
        label_parts = []
        if v.label:
            label_parts.append(v.label)
        if v._op:
            label_parts.append(v._op)
        label_parts.append(f"data={_fmt(v.data)}")
        if v.grad != 0.0 or v is root:
            label_parts.append(f"grad={_fmt(v.grad)}")
        label_str = " | ".join(label_parts)
        lines.append(f'  {nid} [label="{label_str}"];')

    # Emit edges
    for v in nodes:
        for child in v._prev:
            lines.append(f"  {_node_id(v)} -> {_node_id(child)};")

    lines.append("}")
    return "\n".join(lines)


def draw_dot(root: Value, path: str | Path, title: Optional[str] = None) -> None:
    """Write the DOT source to a file."""
    Path(path).write_text(to_dot(root, title=title))


def ascii_loss_chart(history: list[float], width: int = 60, height: int = 15) -> str:
    """Render a simple ASCII chart of a loss history.

    Parameters
    ----------
    history : list[float]
        Per-epoch loss values.
    width : int
        Character width of the chart.
    height : int
        Character height of the chart.
    """
    if not history:
        return "(empty history)"
    if len(history) == 1:
        return f"epoch 0: loss={history[0]:.6f}"

    lo = min(history)
    hi = max(history)
    if hi == lo:
        hi = lo + 1.0  # avoid division by zero

    # Build grid
    grid = [[" "] * width for _ in range(height)]
    n = len(history)
    for i, val in enumerate(history):
        x = int(i / (n - 1) * (width - 1))
        y = int((1.0 - (val - lo) / (hi - lo)) * (height - 1))
        grid[y][x] = "●"

    # Draw axis lines
    lines = []
    lines.append(f"  loss (max={hi:.4f}, min={lo:.4f})")
    lines.append("  ┌" + "─" * width + "┐")
    for row in grid:
        lines.append("  │" + "".join(row) + "│")
    lines.append("  └" + "─" * width + "┘")
    lines.append(f"   epoch 0{'':^{width - 12}}epoch {n - 1}")
    return "\n".join(lines)