"""Advanced demo: showcase new v3.0.0 features.

Run from the project root:
    python3 examples/advanced_demo.py
"""

from graph_layout import (
    Graph, FruchtermanReingold, DRGraphLayout, PivotMDSLayout,
    HTMLRenderer, MatrixRenderer, LayoutMetrics,
    petersen_graph, barabasi_albert, watts_strogatz,
    dijkstra, degree_centrality, closeness_centrality,
    betweenness_centrality, minimum_spanning_tree, label_propagation,
    bfs, dfs, has_cycle, topological_sort,
    SVGRenderer, ASCIIRenderer,
)
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def demo_algorithms():
    """Demonstrate graph algorithms."""
    g = barabasi_albert(30, 3, seed=42)
    print("=== Graph Algorithms Demo ===")
    print(f"Graph: {g.node_count} nodes, {g.edge_count} edges")

    # BFS
    order = bfs(g, "0")
    print(f"BFS from 0: {order[:10]}...")

    # Dijkstra
    dist = dijkstra(g, "0")
    print(f"Dijkstra distances from 0: {dict(list(dist.items())[:5])}")

    # Centrality
    deg = degree_centrality(g)
    top_deg = sorted(deg.items(), key=lambda x: -x[1])[:3]
    print(f"Top 3 by degree centrality: {top_deg}")

    close = closeness_centrality(g)
    top_close = sorted(close.items(), key=lambda x: -x[1])[:3]
    print(f"Top 3 by closeness centrality: {top_close}")

    betw = betweenness_centrality(g)
    top_betw = sorted(betw.items(), key=lambda x: -x[1])[:3]
    print(f"Top 3 by betweenness centrality: {top_betw}")

    # MST
    mst = minimum_spanning_tree(g)
    print(f"MST: {len(mst)} edges, total weight = {sum(w for _,_,w in mst):.2f}")

    # Cycle detection
    print(f"Has cycle: {has_cycle(g)}")

    # Community detection
    communities = label_propagation(g, seed=42)
    n_comm = len(set(communities.values()))
    print(f"Communities detected: {n_comm}")


def demo_new_layouts():
    """Demonstrate new layout algorithms."""
    print("\n=== New Layout Algorithms ===")
    g = watts_strogatz(40, 4, 0.3, seed=42)

    # DRGraph (deterministic, no seed needed)
    g1 = g.copy()
    DRGraphLayout(width=800, height=600, iterations=100).layout(g1)
    m1 = LayoutMetrics.all_metrics(g1)
    print(f"DRGraph:     crossings={int(m1['crossing_count'])}, stress={m1['stress']:.2f}")

    # PivotMDS
    g2 = g.copy()
    PivotMDSLayout(width=800, height=600, pivots=10, seed=42).layout(g2)
    m2 = LayoutMetrics.all_metrics(g2)
    print(f"PivotMDS:    crossings={int(m2['crossing_count'])}, stress={m2['stress']:.2f}")

    # Compare with FruchtermanReingold
    g3 = g.copy()
    FruchtermanReingold(seed=42, iterations=100).layout(g3)
    m3 = LayoutMetrics.all_metrics(g3)
    print(f"FR:          crossings={int(m3['crossing_count'])}, stress={m3['stress']:.2f}")


def demo_new_renderers():
    """Demonstrate HTML and Matrix renderers."""
    print("\n=== New Renderers ===")
    g = petersen_graph()
    FruchtermanReingold(seed=42, iterations=100).layout(g)

    # HTML renderer with dark theme and metrics
    html = HTMLRenderer(width=600, height=500, title="Petersen Graph",
                        show_metrics=True, theme="dark")
    html.save(g, os.path.join(OUTPUT_DIR, "petersen.html"))
    print(f"HTML renderer: saved petersen.html")

    # Matrix renderer
    mat = MatrixRenderer(cell_size=24)
    mat.save(g, os.path.join(OUTPUT_DIR, "petersen_matrix.svg"))
    print(f"Matrix renderer: saved petersen_matrix.svg")

    # ASCII preview
    print("\nASCII preview of Petersen graph:")
    g2 = petersen_graph()
    FruchtermanReingold(seed=42, iterations=100).layout(g2)
    print(ASCIIRenderer(50, 20).render(g2))


if __name__ == "__main__":
    demo_algorithms()
    demo_new_layouts()
    demo_new_renderers()
    print(f"\nAll outputs saved to {OUTPUT_DIR}/")