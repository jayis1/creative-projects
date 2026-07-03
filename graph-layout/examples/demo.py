#!/usr/bin/env python3
"""Example: build a small graph and render it with every algorithm."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_layout import (
    Graph, FruchtermanReingold, KamadaKawai, StressMajorization,
    SugiyamaLayout, TreeLayout, CircularLayout, RadialLayout,
    GridLayout, RandomLayout, LayoutMetrics,
    SVGRenderer, ASCIIRenderer, TextRenderer,
)


def demo_graph():
    g = Graph(directed=False)
    edges = [
        ("A", "B"), ("A", "C"), ("B", "D"), ("B", "E"),
        ("C", "F"), ("C", "G"), ("D", "H"), ("E", "I"),
        ("F", "J"), ("G", "K"), ("H", "I"), ("I", "J"),
        ("J", "K"), ("A", "D"), ("B", "F"),
    ]
    for s, t in edges:
        g.add_edge(s, t)
    return g


if __name__ == "__main__":
    base = Graph()
    edges = [("A","B"),("A","C"),("B","D"),("B","E"),("C","F"),
             ("C","G"),("D","H"),("E","I"),("F","J"),("G","K"),
             ("H","I"),("I","J"),("J","K"),("A","D"),("B","F")]
    for s,t in edges:
        base.add_edge(s,t)

    algos = [
        ("Fruchterman-Reingold", FruchtermanReingold(seed=42, iterations=200)),
        ("Kamada-Kawai", KamadaKawai(seed=42)),
        ("Stress Majorization", StressMajorization(seed=42)),
        ("Sugiyama", SugiyamaLayout()),
        ("Tree", TreeLayout()),
        ("Circular", CircularLayout()),
        ("Radial", RadialLayout(seed=42)),
        ("Grid", GridLayout()),
        ("Random", RandomLayout(seed=42)),
    ]

    for name, algo in algos:
        g = base.copy()
        algo.layout(g)
        m = LayoutMetrics.all_metrics(g)
        print(f"\n{'='*50}\n{name}\n{'='*50}")
        for k, v in m.items():
            print(f"  {k:30s} {v:.4f}")

    # ASCII demo with Fruchterman-Reingold
    g = base.copy()
    FruchtermanReingold(seed=42, iterations=200).layout(g)
    print("\nASCII rendering (Fruchterman-Reingold):")
    print(ASCIIRenderer(70, 20).render(g))

    # SVG demo
    SVGRenderer().save(g, os.path.join(os.path.dirname(__file__), "demo.svg"))
    print("\nSaved demo.svg")