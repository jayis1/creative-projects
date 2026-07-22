"""Test suite for network-flow-solver."""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow.graph import FlowNetwork, FlowEdge
from networkflow.maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel
from networkflow.mincost import MinCostMaxFlow, MinCostFlow
from networkflow.matching import BipartiteMatcher, AssignmentSolver
from networkflow.mincut import MinCut, StoerWagner


def clrs_network() -> FlowNetwork:
    """The classic CLRS max-flow example network (max flow = 23)."""
    net = FlowNetwork(6)
    edges = [(0,1,16),(0,2,13),(1,2,10),(1,3,12),(2,1,4),(2,4,14),(3,2,9),(3,5,20),(4,3,7),(4,5,4)]
    for u, v, c in edges:
        net.add_edge(u, v, c)
    return net


class TestFlowNetwork(unittest.TestCase):
    def test_construction(self):
        net = FlowNetwork(4)
        net.add_edge(0, 1, 10)
        net.add_edge(1, 2, 5)
        self.assertEqual(net.node_count(), 4)
        self.assertEqual(net.edge_count(), 2)

    def test_self_loop_rejected(self):
        net = FlowNetwork(3)
        with self.assertRaises(ValueError):
            net.add_edge(0, 0, 5)

    def test_negative_cap_rejected(self):
        net = FlowNetwork(3)
        with self.assertRaises(ValueError):
            net.add_edge(0, 1, -5)

    def test_invalid_node_rejected(self):
        net = FlowNetwork(3)
        with self.assertRaises(IndexError):
            net.add_edge(0, 5, 10)

    def test_serialization_roundtrip(self):
        net = clrs_network()
        d = net.to_dict()
        net2 = FlowNetwork.from_dict(d)
        self.assertEqual(net2.node_count(), net.node_count())
        self.assertEqual(net2.edge_count(), net.edge_count())

    def test_copy(self):
        net = clrs_network()
        net2 = net.copy()
        self.assertEqual(net2.edge_count(), net.edge_count())

    def test_reset_flows(self):
        net = clrs_network()
        Dinic().solve(net, 0, 5)
        net.reset_flows()
        for u in range(net.n):
            for e in net.graph[u]:
                if e.cap > 0:
                    self.assertEqual(e.flow, 0)

    def test_add_node(self):
        net = FlowNetwork(2)
        idx = net.add_node()
        self.assertEqual(idx, 2)
        self.assertEqual(net.node_count(), 3)


class TestMaxFlow(unittest.TestCase):
    def test_clrs_all_solvers(self):
        for SolverClass in [FordFulkerson, EdmondsKarp, Dinic, PushRelabel]:
            with self.subTest(solver=SolverClass.__name__):
                net = clrs_network()
                flow = SolverClass().solve(net, 0, 5)
                self.assertEqual(flow, 23)

    def test_simple_path(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5)
        net.add_edge(1, 2, 3)
        for SolverClass in [EdmondsKarp, Dinic, PushRelabel]:
            with self.subTest(solver=SolverClass.__name__):
                n2 = net.copy()
                flow = SolverClass().solve(n2, 0, 2)
                self.assertEqual(flow, 3)

    def test_parallel_edges(self):
        net = FlowNetwork(2)
        net.add_edge(0, 1, 3)
        net.add_edge(0, 1, 7)
        flow = Dinic().solve(net, 0, 1)
        self.assertEqual(flow, 10)

    def test_no_path(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5)
        flow = Dinic().solve(net, 0, 2)
        self.assertEqual(flow, 0)

    def test_flow_validation(self):
        net = clrs_network()
        Dinic().solve(net, 0, 5)
        val = net.validate_flow(0, 5)
        self.assertEqual(val, 23)

    def test_bidirectional_edge(self):
        net = FlowNetwork(2)
        net.add_edge(0, 1, 10, bidirectional=True)
        flow = Dinic().solve(net, 0, 1)
        self.assertEqual(flow, 10)


class TestMinCut(unittest.TestCase):
    def test_clrs_min_cut(self):
        net = clrs_network()
        mc = MinCut()
        val = mc.compute(net, 0, 5)
        self.assertEqual(val, 23)
        self.assertIn(0, mc.source_side)
        self.assertIn(5, mc.sink_side)

    def test_cut_edges_capacity(self):
        net = clrs_network()
        mc = MinCut()
        mc.compute(net, 0, 5)
        total = sum(c for _, _, c in mc.cut_edges)
        self.assertEqual(total, 23)


class TestMinCostFlow(unittest.TestCase):
    def test_simple_mincost(self):
        net = FlowNetwork(4)
        net.add_edge(0, 1, 3, cost=1)
        net.add_edge(0, 2, 2, cost=2)
        net.add_edge(1, 3, 2, cost=3)
        net.add_edge(2, 3, 3, cost=1)
        mcmf = MinCostMaxFlow()
        f, c = mcmf.solve(net, 0, 3)
        self.assertEqual(f, 4)
        self.assertEqual(c, 14)

    def test_fixed_flow(self):
        net = FlowNetwork(4)
        net.add_edge(0, 1, 10, cost=1)
        net.add_edge(1, 3, 10, cost=1)
        net.add_edge(0, 2, 10, cost=5)
        net.add_edge(2, 3, 10, cost=5)
        mcf = MinCostFlow()
        f, c = mcf.solve(net, 0, 3, 5)
        self.assertEqual(f, 5)
        self.assertEqual(c, 10)  # 5 * (1+1) = 10 via cheap path

    def test_negative_cost(self):
        """Min-cost flow should handle negative-cost edges."""
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5, cost=-1)
        net.add_edge(1, 2, 5, cost=1)
        mcmf = MinCostMaxFlow()
        f, c = mcmf.solve(net, 0, 2)
        self.assertEqual(f, 5)
        self.assertEqual(c, 0)  # -1*5 + 1*5 = 0


class TestBipartiteMatching(unittest.TestCase):
    def test_perfect_matching(self):
        m = BipartiteMatcher(3, 3)
        m.add_edge(0, 0)
        m.add_edge(1, 1)
        m.add_edge(2, 2)
        self.assertEqual(m.match(), 3)

    def test_no_matching(self):
        m = BipartiteMatcher(2, 2)
        self.assertEqual(m.match(), 0)

    def test_partial_matching(self):
        m = BipartiteMatcher(3, 2)
        m.add_edge(0, 0)
        m.add_edge(1, 0)
        m.add_edge(2, 1)
        self.assertEqual(m.match(), 2)

    def test_vertex_cover(self):
        m = BipartiteMatcher(3, 3)
        for u, v in [(0,0),(0,1),(1,1),(2,2)]:
            m.add_edge(u, v)
        m.match()
        lc, rc = m.minimum_vertex_cover()
        # Vertex cover size should equal matching size
        self.assertEqual(len(lc) + len(rc), m.match() if False else
                         len([(u, m.pair_u[u]) for u in range(3) if m.pair_u[u] != -1]))

    def test_invalid_edge(self):
        m = BipartiteMatcher(2, 2)
        with self.assertRaises(IndexError):
            m.add_edge(5, 0)


class TestAssignment(unittest.TestCase):
    def test_square(self):
        s = AssignmentSolver()
        cost = [[4, 1, 3], [2, 0, 5], [3, 2, 2]]
        result = s.solve(cost)
        self.assertEqual(result, 5)

    def test_2x2(self):
        s = AssignmentSolver()
        cost = [[1, 2], [3, 4]]
        result = s.solve(cost)
        self.assertEqual(result, 5)  # 1+4

    def test_rectangular_wide(self):
        s = AssignmentSolver()
        cost = [[1, 2, 3]]
        result = s.solve(cost)
        self.assertEqual(result, 1)

    def test_rectangular_tall(self):
        s = AssignmentSolver()
        cost = [[1], [2], [3]]
        result = s.solve(cost)
        self.assertEqual(result, 1)

    def test_empty(self):
        s = AssignmentSolver()
        result = s.solve([])
        self.assertEqual(result, 0)

    def test_max_assignment(self):
        cost = [[1, 2, 3], [6, 5, 4], [1, 1, 1]]
        result = AssignmentSolver.max_assignment(cost)
        self.assertEqual(result, 10)  # 3 + 6 + 1

    def test_single_element(self):
        s = AssignmentSolver()
        self.assertEqual(s.solve([[42]]), 42)


class TestStoerWagner(unittest.TestCase):
    def test_triangle(self):
        # Triangle: 0-1(2), 0-2(3), 1-2(4)
        # Min cut = {0}|{1,2} = 2+3 = 5
        graph = {
            0: [(1, 2), (2, 3)],
            1: [(0, 2), (2, 4)],
            2: [(0, 3), (1, 4)],
        }
        sw = StoerWagner()
        val = sw.solve(graph)
        self.assertEqual(val, 5.0)

    def test_two_components(self):
        graph = {
            0: [(1, 5)],
            1: [(0, 5)],
            2: [(3, 5)],
            3: [(2, 5)],
        }
        sw = StoerWagner()
        val = sw.solve(graph)
        self.assertEqual(val, 0.0)  # disconnected


if __name__ == "__main__":
    unittest.main(verbosity=2)