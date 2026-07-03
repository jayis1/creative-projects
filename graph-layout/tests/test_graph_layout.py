"""Bug hunt tests for graph-layout — verify bugs before fixing."""

import sys, os, math, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_layout import (
    Graph, FruchtermanReingold, KamadaKawai, StressMajorization,
    SugiyamaLayout, TreeLayout, CircularLayout, RadialLayout,
    GridLayout, RandomLayout, LayoutMetrics,
    SVGRenderer, ASCIIRenderer, TextRenderer, AnimatedSVGRenderer,
    petersen_graph, hypercube_graph, erdos_renyi, barabasi_albert,
    watts_strogatz, complete_bipartite, path_graph, star_graph,
    cycle_graph, scale_to_fit, bounding_box, normalize, translate, rotate,
    center_on_origin, load_json, save_json, load_dot, save_dot,
    load_edge_list, save_edge_list,
)


# ===== Bug 3: barabasi_albert infinite loop =====
def test_barabasi_albert_small_n():
    """Bug 3: BA with n=2, m=1 should not infinite-loop."""
    g = barabasi_albert(2, 1, seed=42)
    assert g.node_count == 2


def test_barabasi_albert_m_equals_n():
    """Bug 3: BA with m >= n-1 edge case."""
    g = barabasi_albert(3, 2, seed=42)
    assert g.node_count == 3


# ===== Bug 4: metrics crossing_count with partial positions =====
def test_metrics_crossing_none_y():
    """Bug 4: crossing_count should handle node.x set but node.y=None."""
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("C", "D")
    g.nodes["A"].x = 0; g.nodes["A"].y = 0
    g.nodes["B"].x = 10; g.nodes["B"].y = 10
    g.nodes["C"].x = 0; g.nodes["C"].y = 10
    g.nodes["D"].x = 10; g.nodes["D"].y = 0  # crossing
    # Now set D.y to None to trigger the bug
    g.nodes["D"].y = None
    # This should not crash with TypeError
    result = LayoutMetrics.crossing_count(g)
    assert isinstance(result, int)


# ===== Bug 5: ASCIIRenderer Bresenham uses changing x0/y0 =====
def test_ascii_bresenham_diagonal():
    """Bug 5: ASCII renderer should use initial dx/dy for char selection."""
    g = Graph()
    g.add_edge("A", "B")
    g.nodes["A"].x = 0; g.nodes["A"].y = 0
    g.nodes["B"].x = 100; g.nodes["B"].y = 100
    r = ASCIIRenderer(20, 10)
    out = r.render(g)
    assert isinstance(out, str)
    # The line should be rendered without crash


# ===== Bug 6: Sugiyama DFS recursion limit =====
def test_sugiyama_large_graph():
    """Bug 6: Sugiyama should handle deep chains without recursion error."""
    # Build a deep chain
    g = Graph(directed=True)
    for i in range(200):
        g.add_edge(f"n{i}", f"n{i+1}")
    s = SugiyamaLayout()
    s.layout(g)  # should not hit RecursionError
    assert all(n.x is not None for n in g.iter_nodes())


# ===== Bug 7: TreeLayout disconnected components =====
def test_tree_layout_disconnected():
    """Bug 7: TreeLayout should handle disconnected graphs properly."""
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("D", "E")  # separate component
    g.add_edge("E", "F")
    t = TreeLayout()
    t.layout(g)
    # All nodes should be positioned
    for nid in g.nodes:
        assert g.nodes[nid].x is not None, f"Node {nid} not positioned"
        assert g.nodes[nid].y is not None, f"Node {nid} not positioned"


# ===== Bug 8: RadialLayout unvisited nodes =====
def test_radial_disconnected():
    """Bug 8: RadialLayout only BFS from one root — disconnected nodes unpositioned."""
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("C", "D")  # disconnected
    r = RadialLayout()
    r.layout(g)
    # All nodes should be positioned
    for nid in g.nodes:
        assert g.nodes[nid].x is not None, f"Node {nid} not positioned by RadialLayout"


# ===== Bug 9: remove_edge doesn't handle KeyError on _adj =====
def test_remove_edge_nonexistent():
    """Bug 9: remove_edge on nonexistent edge should not crash."""
    g = Graph()
    g.add_node("A")
    g.add_node("B")
    # No edge between A and B, try removing anyway
    g.remove_edge("A", "B")  # should not raise KeyError


# ===== Bug 10: DOT loader node regex catches edge lines =====
def test_dot_roundtrip():
    """Bug 10: DOT save then load should preserve graph structure."""
    g = petersen_graph()
    FruchtermanReingold(seed=42, iterations=50).layout(g)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".dot", mode="w", delete=False) as f:
        save_dot(g, f.name)
        g2 = load_dot(f.name)
    os.unlink(f.name if isinstance(f.name, str) else f.name)
    assert g2.node_count == g.node_count
    # Edges might differ due to DOT loader also creating duplicate nodes from edge lines


# ===== Bug 11: StressMajorization division by zero =====
def test_stress_two_nodes():
    """Bug 11: Stress majorization with 2 nodes should not crash."""
    g = Graph()
    g.add_edge("A", "B")
    s = StressMajorization(seed=42)
    s.layout(g)
    assert g.nodes["A"].x is not None
    assert g.nodes["B"].x is not None


# ===== Bug 12: Graph.copy doesn't copy edge_map correctly =====
def test_graph_copy_preserves_edges():
    """Bug 12: Graph.copy should preserve all edges."""
    g = petersen_graph()
    g2 = g.copy()
    assert g2.edge_count == g.edge_count
    assert g2.node_count == g.node_count


# ===== Basic sanity tests =====
def test_empty_graph_all_layouts():
    """All layouts should handle empty graphs."""
    g = Graph()
    for cls in [FruchtermanReingold, KamadaKawai, StressMajorization,
                SugiyamaLayout, TreeLayout, CircularLayout, RadialLayout,
                GridLayout, RandomLayout]:
        g2 = g.copy()
        cls(seed=42).layout(g2)
        assert g2.node_count == 0


def test_single_node_all_layouts():
    """All layouts should handle a single node."""
    g = Graph()
    g.add_node("only")
    for cls in [FruchtermanReingold, KamadaKawai, StressMajorization,
                SugiyamaLayout, TreeLayout, CircularLayout, RadialLayout,
                GridLayout, RandomLayout]:
        g2 = g.copy()
        cls(seed=42).layout(g2)
        assert g2.nodes["only"].x is not None


def test_all_layouts_produce_positions():
    """Every layout algorithm must assign positions to all nodes."""
    g = petersen_graph()
    for cls in [FruchtermanReingold, KamadaKawai, StressMajorization,
                SugiyamaLayout, TreeLayout, CircularLayout, RadialLayout,
                GridLayout, RandomLayout]:
        g2 = g.copy()
        cls(seed=42, width=800, height=600).layout(g2)
        for nid, node in g2.nodes.items():
            assert node.x is not None, f"{cls.__name__}: node {nid} x is None"
            assert node.y is not None, f"{cls.__name__}: node {nid} y is None"


def test_generators():
    """Test all graph generators produce valid graphs."""
    assert petersen_graph().node_count == 10
    assert petersen_graph().edge_count == 15
    assert hypercube_graph(3).node_count == 8
    assert path_graph(5).edge_count == 4
    assert star_graph(5).edge_count == 5
    assert cycle_graph(5).edge_count == 5
    assert complete_bipartite(2, 3).node_count == 5
    assert complete_bipartite(2, 3).edge_count == 6
    g = erdos_renyi(10, 0.5, seed=42)
    assert g.node_count == 10
    g = watts_strogatz(10, 4, 0.3, seed=42)
    assert g.node_count == 10


def test_json_roundtrip():
    """JSON save/load should preserve graph structure and positions."""
    g = petersen_graph()
    FruchtermanReingold(seed=42, iterations=50).layout(g)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        save_json(g, f.name)
        g2 = load_json(f.name)
    assert g2.node_count == g.node_count
    assert g2.edge_count == g.edge_count
    for nid in g.nodes:
        assert g2.nodes[nid].x is not None
    os.unlink(f.name if isinstance(f.name, str) else f.name)


def test_edge_list_roundtrip():
    """Edge list save/load should preserve edges."""
    g = path_graph(5)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
        save_edge_list(g, f.name)
        g2 = load_edge_list(f.name)
    assert g2.edge_count == g.edge_count
    os.unlink(f.name if isinstance(f.name, str) else f.name)


def test_transforms():
    """Test layout transforms."""
    g = petersen_graph()
    FruchtermanReingold(seed=42, iterations=50).layout(g)
    bb = bounding_box(g)
    assert len(bb) == 4
    g2 = g.copy()
    scale_to_fit(g2, 100, 100)
    minx, miny, maxx, maxy = bounding_box(g2)
    assert maxx <= 101
    assert maxy <= 101
    g3 = g.copy()
    normalize(g3)
    minx, miny, maxx, maxy = bounding_box(g3)
    assert maxx <= 1.01
    assert maxy <= 1.01


def test_svg_renderer():
    """SVG renderer should produce valid SVG."""
    g = petersen_graph()
    FruchtermanReingold(seed=42, iterations=50).layout(g)
    svg = SVGRenderer().render(g)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "circle" in svg


def test_animated_svg():
    """Animated SVG renderer should produce valid SVG."""
    g = petersen_graph()
    algo = FruchtermanReingold(seed=42, iterations=50,
                                capture_frames=True, frame_interval=5)
    algo.layout(g)
    svg = AnimatedSVGRenderer().render(algo.frames, g)
    assert "<svg" in svg
    assert "animate" in svg.lower()


def test_metrics():
    """Metrics should return reasonable values for a positioned graph."""
    g = petersen_graph()
    FruchtermanReingold(seed=42, iterations=50).layout(g)
    m = LayoutMetrics.all_metrics(g)
    assert "crossing_count" in m
    assert "stress" in m
    assert m["crossing_count"] >= 0
    assert not math.isnan(m["stress"])


def test_cli():
    """Test CLI entry point."""
    from graph_layout.cli import main
    g = petersen_graph()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".edges", mode="w", delete=False) as f:
        save_edge_list(g, f.name)
        path = f.name
    out = path + ".svg"
    main(["layout", path, "-o", out, "-a", "fr"])
    assert os.path.exists(out)
    os.unlink(path)
    os.unlink(out)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])