"""Tests for graph algorithms module (v3.0.0)."""

import sys, os, math, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_layout import (
    Graph, petersen_graph, path_graph, cycle_graph, star_graph,
    complete_bipartite, barabasi_albert, erdos_renyi,
    bfs, dfs, dijkstra, degree_centrality, closeness_centrality,
    betweenness_centrality, minimum_spanning_tree, has_cycle,
    topological_sort, label_propagation,
)


class TestBFS:
    def test_bfs_simple_path(self):
        g = path_graph(5)  # 0-1-2-3-4
        result = bfs(g, "0")
        assert result == ["0", "1", "2", "3", "4"]

    def test_bfs_star(self):
        g = star_graph(4)  # center "0" connected to 1,2,3,4
        result = bfs(g, "0")
        assert result[0] == "0"
        assert set(result) == {"0", "1", "2", "3", "4"}

    def test_bfs_disconnected(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("C", "D")
        result = bfs(g, "A")
        assert set(result) == {"A", "B"}
        assert "C" not in result

    def test_bfs_nonexistent_start(self):
        g = path_graph(3)
        assert bfs(g, "ZZZ") == []

    def test_bfs_cycle(self):
        g = cycle_graph(5)
        result = bfs(g, "0")
        assert set(result) == {"0", "1", "2", "3", "4"}


class TestDFS:
    def test_dfs_simple_path(self):
        g = path_graph(5)
        result = dfs(g, "0")
        assert set(result) == {"0", "1", "2", "3", "4"}
        assert result[0] == "0"

    def test_dfs_visits_all_connected(self):
        g = star_graph(4)
        result = dfs(g, "0")
        assert set(result) == {"0", "1", "2", "3", "4"}


class TestDijkstra:
    def test_dijkstra_path_graph(self):
        g = path_graph(5)
        dist = dijkstra(g, "0")
        assert dist["0"] == 0
        assert dist["1"] == 1
        assert dist["4"] == 4

    def test_dijkstra_weighted(self):
        g = Graph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=2.0)
        g.add_edge("A", "C", weight=10.0)  # direct but expensive
        dist = dijkstra(g, "A")
        assert dist["C"] == 3.0  # A->B->C is cheaper

    def test_dijkstra_disconnected(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_node("C")  # isolated
        dist = dijkstra(g, "A")
        assert dist["A"] == 0
        assert dist["B"] == 1
        assert "C" not in dist  # unreachable


class TestCentrality:
    def test_degree_centrality_star(self):
        g = star_graph(4)  # center "0", leaves 1-4
        c = degree_centrality(g)
        assert c["0"] == 1.0  # center has degree 4, n-1=4
        assert c["1"] == 0.25

    def test_degree_centrality_single_node(self):
        g = Graph()
        g.add_node("only")
        c = degree_centrality(g)
        assert c["only"] == 0.0

    def test_closeness_centrality_path(self):
        g = path_graph(4)  # 0-1-2-3
        c = closeness_centrality(g)
        # Node 1 and 2 should have higher closeness than endpoints
        assert c["1"] > c["0"]
        assert c["2"] > c["3"]

    def test_betweenness_centrality_path(self):
        g = path_graph(5)  # 0-1-2-3-4
        b = betweenness_centrality(g)
        # Node 2 is on all shortest paths through the middle
        assert b["2"] > b["0"]
        assert b["2"] > b["4"]

    def test_betweenness_star(self):
        g = star_graph(4)  # center "0"
        b = betweenness_centrality(g)
        # Center has maximum betweenness
        assert b["0"] > b["1"]


class TestMST:
    def test_mst_simple(self):
        g = Graph()
        g.add_edge("A", "B", weight=1)
        g.add_edge("B", "C", weight=2)
        g.add_edge("A", "C", weight=10)
        mst = minimum_spanning_tree(g)
        assert len(mst) == 2  # n-1 edges
        total = sum(w for _, _, w in mst)
        assert total == 3  # A-B(1) + B-C(2)

    def test_mst_complete_graph(self):
        g = Graph.complete_graph(4)  # all weight=1
        mst = minimum_spanning_tree(g)
        assert len(mst) == 3  # n-1 edges

    def test_mst_empty(self):
        g = Graph()
        assert minimum_spanning_tree(g) == []


class TestCycleDetection:
    def test_cycle_in_cycle_graph(self):
        g = cycle_graph(5)
        assert has_cycle(g) is True

    def test_no_cycle_in_path(self):
        g = path_graph(5)
        assert has_cycle(g) is False

    def test_no_cycle_in_tree(self):
        g = Graph.tree_graph(2, 3)
        assert has_cycle(g) is False

    def test_cycle_in_complete(self):
        g = Graph.complete_graph(4)
        assert has_cycle(g) is True


class TestTopologicalSort:
    def test_dag(self):
        g = Graph(directed=True)
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")
        order = topological_sort(g)
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_cycle_raises(self):
        g = Graph(directed=True)
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")
        with pytest.raises(ValueError):
            topological_sort(g)


class TestLabelPropagation:
    def test_two_clusters(self):
        g = Graph()
        # cluster 1: 0-1-2
        g.add_edge("0", "1")
        g.add_edge("1", "2")
        g.add_edge("0", "2")
        # cluster 2: 3-4-5
        g.add_edge("3", "4")
        g.add_edge("4", "5")
        g.add_edge("3", "5")
        # bridge
        g.add_edge("2", "3")
        communities = label_propagation(g, seed=42)
        # Should detect at most a few communities
        n_comm = len(set(communities.values()))
        assert n_comm >= 1
        assert n_comm <= 4

    def test_single_node(self):
        g = Graph()
        g.add_node("only")
        communities = label_propagation(g)
        assert communities["only"] == 0