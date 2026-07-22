"""
Visualization utilities for flow networks.

Provides ASCII-art rendering, Graphviz DOT output, and flow-difference
visualization for FlowNetwork objects.  No external dependencies required
for ASCII output; DOT output can be rendered with graphviz if installed.
"""

from __future__ import annotations

from .graph import FlowNetwork


def to_dot(network: FlowNetwork,
           source: int | None = None,
           sink: int | None = None,
           show_flows: bool = True,
           show_residuals: bool = False) -> str:
    """Generate Graphviz DOT representation of a flow network.

    Parameters
    ----------
    network : FlowNetwork
        The network to visualize.
    source, sink : int, optional
        If given, these nodes are styled as source (green) / sink (red).
    show_flows : bool
        If True, edge labels show ``flow/capacity``; otherwise just capacity.
    show_residuals : bool
        If True, include residual (reverse) edges as dashed lines.

    Returns
    -------
    str
        DOT source code.  Render with ``dot -Tpng input.dot -o output.png``.
    """
    lines = ["digraph flow {"]
    lines.append('  rankdir=LR;')
    lines.append('  node [fontname="Helvetica", fontsize=10];')
    lines.append('  edge [fontname="Helvetica", fontsize=9];')

    # Node styling
    for i in range(network.n):
        attrs = []
        if i == source:
            attrs.append('shape=box, style=filled, fillcolor="#90EE90"')
        elif i == sink:
            attrs.append('shape=box, style=filled, fillcolor="#FFB6C1"')
        else:
            attrs.append('shape=circle')
        lines.append(f'  {i} [{", ".join(attrs)}];')

    # Forward edges
    for u in range(network.n):
        for e in network.graph[u]:
            if e.cap > 0:
                if show_flows and e.flow != 0:
                    label = f'{e.flow}/{e.cap}'
                else:
                    label = f'{e.cap}'
                color = "#000000"
                if e.flow > 0 and e.flow < e.cap:
                    color = "#0066CC"  # partially used — blue
                elif e.flow >= e.cap:
                    color = "#CC0000"  # saturated — red
                penwidth = 1.0 + min(3.0, e.flow / max(e.cap, 1) * 3) if e.cap > 0 else 1.0
                lines.append(
                    f'  {u} -> {e.to} '
                    f'[label="{label}", color="{color}", '
                    f'penwidth={penwidth:.1f}];'
                )

    # Residual edges (optional)
    if show_residuals:
        for u in range(network.n):
            for e in network.graph[u]:
                if e.cap == 0 and e.residual() > 0:
                    lines.append(
                        f'  {u} -> {e.to} '
                        f'[label="{e.residual():.0f}", '
                        f'style=dashed, color="#999999"];'
                    )

    lines.append("}")
    return "\n".join(lines)


def ascii_graph(network: FlowNetwork,
                source: int | None = None,
                sink: int | None = None,
                show_flows: bool = False) -> str:
    """Render an ASCII representation of the network's edge list.

    This is a compact table suitable for terminal output.

    Parameters
    ----------
    network : FlowNetwork
        The network to display.
    source, sink : int, optional
        Marked in the output if provided.
    show_flows : bool
        If True, show ``flow/cap`` for each edge.

    Returns
    -------
    str
        Multi-line ASCII table.
    """
    lines = []
    header = f"  {'From':>6} -> {'To':<6}  {'Cap':>8}"
    if show_flows:
        header += f"  {'Flow':>8}  {'Util%':>6}"
    if source is not None or sink is not None:
        header += "  Note"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))

    for u in range(network.n):
        for e in network.graph[u]:
            if e.cap > 0:
                row = f"  {u:>6} -> {e.to:<6}  {e.cap:>8}"
                if show_flows:
                    util = (e.flow / e.cap * 100) if e.cap > 0 else 0
                    row += f"  {e.flow:>8}  {util:>5.0f}%"
                if source is not None and u == source:
                    row += "  ← source"
                elif sink is not None and e.to == sink:
                    row += "  → sink"
                lines.append(row)

    return "\n".join(lines)


def flow_decomposition(network: FlowNetwork, source: int,
                       sink: int) -> list[tuple[list[int], float]]:
    """Decompose flow into paths from source to sink with their flow amounts.

    After running a max-flow (or min-cost flow) algorithm, the flow can be
    decomposed into a set of s-t paths, each carrying some amount of flow.
    This is useful for understanding the actual flow routing.

    Returns
    -------
    list of (path, amount)
        Each element is a path (list of node indices) and the flow amount
        carried along that path.
    """
    # Copy edge flows so we can consume them during decomposition
    flow_map: dict[tuple[int, int], float] = {}
    for u in range(network.n):
        for e in network.graph[u]:
            if e.cap > 0 and e.flow > 0:
                flow_map[(u, e.to)] = e.flow

    paths: list[tuple[list[int], float]] = []

    while flow_map:
        # DFS from source to sink following positive-flow edges
        path = [source]
        cur = source
        while cur != sink:
            next_node = None
            for (u, v), f in flow_map.items():
                if u == cur and f > 0:
                    next_node = v
                    break
            if next_node is None:
                break
            path.append(next_node)
            cur = next_node

        if cur != sink or len(path) < 2:
            break

        # Find bottleneck flow on this path
        bottleneck = float("inf")
        for i in range(len(path) - 1):
            key = (path[i], path[i + 1])
            bottleneck = min(bottleneck, flow_map[key])

        paths.append((path, bottleneck))

        # Subtract bottleneck from all edges on path
        for i in range(len(path) - 1):
            key = (path[i], path[i + 1])
            flow_map[key] -= bottleneck
            if flow_map[key] <= 1e-12:
                del flow_map[key]

    return paths


def ascii_flow_paths(paths: list[tuple[list[int], float]]) -> str:
    """Render flow decomposition as ASCII."""
    if not paths:
        return "(no flow paths)"
    lines = [f"  Flow decomposition ({len(paths)} paths):"]
    total = 0.0
    for i, (path, amount) in enumerate(paths):
        path_str = " → ".join(str(n) for n in path)
        lines.append(f"  Path {i}: [{path_str}]  flow={amount}")
        total += amount
    lines.append(f"  Total flow: {total}")
    return "\n".join(lines)