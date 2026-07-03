"""I/O utilities: load/save graphs in DOT, JSON, and edge-list formats."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from .graph import Graph


# ---------------------------------------------------------------------
#  DOT (Graphviz)
# ---------------------------------------------------------------------
def save_dot(graph: Graph, path: str) -> None:
    """Write a graph to a Graphviz DOT file."""
    lines = []
    gtype = "digraph" if graph.directed else "graph"
    lines.append(f"{gtype} G {{")
    for nid, node in graph.nodes.items():
        attrs = [f'label="{nid}"']
        if node.x is not None:
            attrs.append(f'pos="{node.x},{node.y}!"')
        attr_str = ", ".join(attrs)
        lines.append(f'  "{nid}" [{attr_str}];')
    op = "->" if graph.directed else "--"
    for e in graph.edges:
        # Bug fix: removed unused variable `w`; only emit weight attr when != 1.0
        attr = f' [weight={e.weight}]' if e.weight != 1.0 else ""
        lines.append(f'  "{e.source}" {op} "{e.target}"{attr};')
    lines.append("}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def load_dot(path: str) -> Graph:
    """Parse a (subset of) DOT format into a Graph."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # detect directed
    directed = bool(re.search(r'^\s*digraph\b', text, re.IGNORECASE))
    g = Graph(directed=directed)
    # edges: "a" -> "b"  or  a -- b ;
    edge_re = re.compile(
        r'"?([^"\s;{}]+)"?\s*(->|--)\s*"?([^"\s;{}]+)"?\s*(?:\[([^\]]*)\])?;'
    )
    for m in edge_re.finditer(text):
        src, op, tgt, attrs = m.group(1), m.group(2), m.group(3), m.group(4)
        weight = 1.0
        if attrs:
            wm = re.search(r'weight\s*=\s*([\d.]+)', attrs)
            if wm:
                weight = float(wm.group(1))
        d = op == "->"
        g.add_edge(src, tgt, weight=weight, directed=d)
    # standalone nodes: "x" [...];
    node_re = re.compile(r'"?([^"\s;{}]+)"?\s*(?:\[([^\]]*)\])?\s*;')
    for m in node_re.finditer(text):
        nid = m.group(1)
        if not g.has_node(nid):
            g.add_node(nid)
    return g


# ---------------------------------------------------------------------
#  JSON
# ---------------------------------------------------------------------
def save_json(graph: Graph, path: str) -> None:
    """Serialize a graph (with positions) to JSON."""
    data = {
        "directed": graph.directed,
        "nodes": [
            {"id": n.id, "x": n.x, "y": n.y,
             "width": n.width, "height": n.height,
             "attributes": n.attributes}
            for n in graph.iter_nodes()
        ],
        "edges": [
            {"source": e.source, "target": e.target,
             "weight": e.weight, "directed": e.directed,
             "attributes": e.attributes}
            for e in graph.iter_edges()
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path: str) -> Graph:
    """Load a graph from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    g = Graph(directed=data.get("directed", False))
    for nd in data.get("nodes", []):
        node = g.add_node(nd["id"], **nd.get("attributes", {}))
        node.x = nd.get("x")
        node.y = nd.get("y")
        if "width" in nd:
            node.width = nd["width"]
        if "height" in nd:
            node.height = nd["height"]
    for ed in data.get("edges", []):
        g.add_edge(ed["source"], ed["target"], weight=ed.get("weight", 1.0),
                   directed=ed.get("directed", g.directed),
                   **ed.get("attributes", {}))
    return g


# ---------------------------------------------------------------------
#  Edge list (plain text: "src tgt [weight]")
# ---------------------------------------------------------------------
def save_edge_list(graph: Graph, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in graph.edges:
            f.write(f"{e.source} {e.target} {e.weight}\n")


def load_edge_list(path: str, directed: bool = False) -> Graph:
    g = Graph(directed=directed)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            src, tgt = parts[0], parts[1]
            w = float(parts[2]) if len(parts) > 2 else 1.0
            g.add_edge(src, tgt, weight=w)
    return g