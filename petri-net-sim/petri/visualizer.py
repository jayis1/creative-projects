"""ASCII visualization and Graphviz DOT export."""

from __future__ import annotations

from .net import PetriNet
from .analysis import ReachabilityGraph


def ascii_net(net: PetriNet) -> str:
    """Render the net structure as ASCII art.

    Places are shown as (P) circles with token counts.
    Transitions as [T] bars.
    Arcs as -> with weights.
    """
    lines: list[str] = [f"Petri Net: {net.name}", "=" * 40, ""]

    lines.append("Places:")
    for p in net.places.values():
        cap = "∞" if p.capacity is None else str(p.capacity)
        lines.append(f"  ({p.name}) tokens={p.initial} cap={cap}")
    lines.append("")

    lines.append("Transitions:")
    for t in net.transitions.values():
        pre = sorted(net.preset(t.name))
        post = sorted(net.postset(t.name))
        lines.append(f"  [{t.name}]")
        lines.append(f"    pre:  {', '.join(pre) if pre else '∅'}")
        lines.append(f"    post: {', '.join(post) if post else '∅'}")
    lines.append("")

    lines.append("Arcs:")
    for t_name in net.transitions:
        for arc in net.input_arcs(t_name):
            w = f" (×{arc.weight})" if arc.weight > 1 else ""
            lines.append(f"  {arc.source} ──{w}──▶ [{t_name}]")
        for arc in net.output_arcs(t_name):
            w = f" (×{arc.weight})" if arc.weight > 1 else ""
            lines.append(f"  [{t_name}] ──{w}──▶ {arc.target}")

    return "\n".join(lines)


def ascii_marking(marking: dict[str, int], net: PetriNet) -> str:
    """Render a marking as a row of place circles with token counts."""
    parts: list[str] = []
    for p_name in sorted(net.places):
        tokens = marking.get(p_name, 0)
        cap = net.places[p_name].capacity
        if cap is not None:
            parts.append(f"({p_name}:{tokens}/{cap})")
        else:
            parts.append(f"({p_name}:{tokens})")
    return "  ".join(parts)


def reachability_ascii(rg: ReachabilityGraph) -> str:
    """Render the reachability graph as an ASCII adjacency list."""
    lines: list[str] = [
        f"Reachability Graph ({rg.num_states} states, {rg.num_edges} edges)",
        "=" * 50,
    ]
    if rg.deadlocks:
        lines.append(f"Deadlock states: {len(rg.deadlocks)}")
    else:
        lines.append("No deadlocks (deadlock-free)")
    lines.append("")

    for node_id, node in rg.nodes.items():
        marker = " 🔒" if node_id in rg.deadlocks else ""
        init = " (initial)" if node_id == rg.initial_id else ""
        marking_str = ", ".join(
            f"{k}={v}" for k, v in sorted(node.marking.items())
        )
        lines.append(f"  {node_id}{init}{marker}")
        lines.append(f"    [{marking_str}]")
        for t_name, target_id in node.successors:
            lines.append(f"    --{t_name}--> {target_id}")

    return "\n".join(lines)


def reachability_dot(rg: ReachabilityGraph) -> str:
    """Export the reachability graph as Graphviz DOT format."""
    lines: list[str] = ["digraph reachability {", '  rankdir=LR;', '  node [shape=box];']

    for node_id, node in rg.nodes.items():
        marking_str = "\\n".join(
            f"{k}={v}" for k, v in sorted(node.marking.items())
        )
        attrs: list[str] = [f'label="{node_id}\\n{marking_str}"']
        if node_id == rg.initial_id:
            attrs.append('shape=doubleoctagon')
        if node_id in rg.deadlocks:
            attrs.append('color=red')
        lines.append(f'  "{node_id}" [{", ".join(attrs)}];')

    lines.append("")
    for node_id, node in rg.nodes.items():
        for t_name, target_id in node.successors:
            lines.append(f'  "{node_id}" -> "{target_id}" [label="{t_name}"];')

    lines.append("}")
    return "\n".join(lines)