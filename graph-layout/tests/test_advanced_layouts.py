"""Tests for new layout algorithms (DRGraph, PivotMDS) — v3.0.0."""

import sys, os, math, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_layout import (
    Graph, DRGraphLayout, PivotMDSLayout, LayoutMetrics,
    petersen_graph, path_graph, star_graph, complete_bipartite,
    barabasi_albert, erdos_renyi, watts_strogatz,
)


class TestDRGraph:
    def test_empty_graph(self):
        g = Graph()
        DRGraphLayout().layout(g)
        assert g.node_count == 0

    def test_single_node(self):
        g = Graph()
        g.add_node("only")
        DRGraphLayout().layout(g)
        assert g.nodes["only"].x is not None
        assert g.nodes["only"].y is not None

    def test_petersen_positions(self):
        g = petersen_graph()
        DRGraphLayout(width=800, height=600, iterations=50).layout(g)
        for nid, node in g.nodes.items():
            assert node.x is not None, f"Node {nid} x is None"
            assert node.y is not None, f"Node {nid} y is None"

    def test_two_nodes(self):
        g = Graph()
        g.add_edge("A", "B")
        DRGraphLayout(seed=42).layout(g)
        assert g.nodes["A"].x is not None
        assert g.nodes["B"].x is not None

    def test_positions_within_bounds(self):
        g = barabasi_albert(30, 3, seed=42)
        DRGraphLayout(width=500, height=500, iterations=50, seed=42).layout(g)
        for node in g.iter_nodes():
            assert 0 <= node.x <= 500
            assert 0 <= node.y <= 500

    def test_deterministic_init(self):
        """DRGraph should produce reasonable layout even without seed."""
        g = petersen_graph()
        DRGraphLayout(width=800, height=600, iterations=50, seed=None).layout(g)
        for node in g.iter_nodes():
            assert node.x is not None


class TestPivotMDS:
    def test_empty_graph(self):
        g = Graph()
        PivotMDSLayout().layout(g)
        assert g.node_count == 0

    def test_single_node(self):
        g = Graph()
        g.add_node("only")
        PivotMDSLayout().layout(g)
        assert g.nodes["only"].x is not None

    def test_petersen_positions(self):
        g = petersen_graph()
        PivotMDSLayout(width=800, height=600, pivots=5, seed=42).layout(g)
        for nid, node in g.nodes.items():
            assert node.x is not None, f"Node {nid} x is None"
            assert node.y is not None, f"Node {nid} y is None"

    def test_two_nodes(self):
        g = Graph()
        g.add_edge("A", "B")
        PivotMDSLayout(seed=42).layout(g)
        assert g.nodes["A"].x is not None

    def test_large_graph(self):
        g = erdos_renyi(40, 0.3, seed=42)
        PivotMDSLayout(width=1000, height=1000, pivots=10, seed=42).layout(g)
        for node in g.iter_nodes():
            assert node.x is not None
            assert node.y is not None

    def test_pivots_capped(self):
        """Pivots should be capped at node count."""
        g = path_graph(5)
        PivotMDSLayout(pivots=100, seed=42).layout(g)
        for node in g.iter_nodes():
            assert node.x is not None