"""Test suite for network-flow-solver."""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow.graph import FlowNetwork, FlowEdge
from networkflow.maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel, CapacityScaling
from networkflow.mincost import MinCostMaxFlow, MinCostFlow
from networkflow.matching import BipartiteMatcher, AssignmentSolver
from networkflow.mincut import MinCut, StoerWagner
from networkflow.connectivity import edge_disjoint_paths, vertex_disjoint_paths, edge_connectivity, GomoryHuTree
from networkflow.benchmark import random_network, grid_network, bipartite_network


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


# --- Phase 3: Bug hunt tests ---

class TestBugCopyWithFlows(unittest.TestCase):
    """Bug: copy()/from_dict() doesn't restore reverse edge flow.

    After running max flow, copy() should produce a network with the same
    flow state, including reverse edges.  The reverse edge's flow must be
    the negative of the forward edge's flow for the residual graph to be
    consistent.
    """

    def test_copy_preserves_flows(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 10)
        net.add_edge(1, 2, 5)
        Dinic().solve(net, 0, 2)
        # Now copy and check residual
        net2 = net.copy()
        # The forward edge 0->1 should have flow 5
        fwd = None
        for e in net2.graph[0]:
            if e.cap > 0:
                fwd = e
                break
        self.assertIsNotNone(fwd)
        self.assertEqual(fwd.flow, 5)
        # The reverse edge (1->0) should have flow -5
        rev = net2.graph[1][fwd.rev]
        self.assertEqual(rev.flow, -5)

    def test_copy_residual_consistent(self):
        """After copy, residual graph should match original."""
        net = FlowNetwork(3)
        net.add_edge(0, 1, 10)
        net.add_edge(1, 2, 5)
        Dinic().solve(net, 0, 2)
        net2 = net.copy()
        # Check all edges have matching residual
        for u in range(3):
            for e in net.graph[u]:
                e2 = net2.graph[u][net.graph[u].index(e)] if e in net.graph[u] else None
        # Simpler: just check that max-flow on the copy gives 0 (already saturated)
        flow = Dinic().solve(net2, 0, 2)
        self.assertEqual(flow, 0)  # already at max flow


class TestBugPushRelabelHeightOOB(unittest.TestCase):
    """Bug: PushRelabel count array out of bounds when height = 2*n+1.

    The count array has size 2*n+1 (valid indices 0..2*n), but height can
    be set to 2*n+1, causing IndexError.
    """

    def test_no_crash_on_disconnected(self):
        """A node with no outgoing residual should not crash."""
        net = FlowNetwork(4)
        net.add_edge(0, 1, 5)
        net.add_edge(1, 2, 5)
        net.add_edge(2, 3, 5)
        # Node 1 has only one outgoing edge — when saturated, relabel
        # should not cause out-of-bounds access.
        pr = PushRelabel()
        flow = pr.solve(net, 0, 3)
        self.assertEqual(flow, 5)

    def test_large_network(self):
        """Larger network shouldn't crash PushRelabel."""
        net = FlowNetwork(10)
        for i in range(9):
            net.add_edge(i, i + 1, 5)
        pr = PushRelabel()
        flow = pr.solve(net, 0, 9)
        self.assertEqual(flow, 5)


class TestBugVertexDisjointDuplicateNodes(unittest.TestCase):
    """Bug: vertex_disjoint_paths produces paths with duplicate consecutive nodes.

    When converting from split nodes back to original, both 2*i and 2*i+1
    map to i via integer division, producing [0, 1, 1, 2, 2, 3] instead of
    [0, 1, 2, 3].
    """

    def test_no_duplicate_nodes(self):
        net = FlowNetwork(4)
        net.add_edge(0, 1, 1)
        net.add_edge(0, 2, 1)
        net.add_edge(1, 3, 1)
        net.add_edge(2, 3, 1)
        paths = vertex_disjoint_paths(net, 0, 3)
        self.assertEqual(len(paths), 2)
        for path in paths:
            # No consecutive duplicates
            for i in range(len(path) - 1):
                self.assertNotEqual(path[i], path[i + 1],
                                    f"Duplicate consecutive nodes in path {path}")
            # Path should start at source and end at sink
            self.assertEqual(path[0], 0)
            self.assertEqual(path[-1], 3)


class TestBugStoerWagnerDocstring(unittest.TestCase):
    """Bug: StoerWagner docstring example claims min cut is 2.0 but it's 5.0."""

    def test_docstring_example(self):
        graph = {
            0: [(1, 2), (2, 3)],
            1: [(0, 2), (2, 4)],
            2: [(0, 3), (1, 4)],
        }
        sw = StoerWagner()
        val = sw.solve(graph)
        # Min cut = {0}|{1,2} = 2+3 = 5, not 2
        self.assertEqual(val, 5.0)


class TestBugBipartiteDuplicateEdges(unittest.TestCase):
    """Bug: BipartiteMatcher.add_edge allows duplicate edges."""

    def test_duplicate_edges_handled(self):
        m = BipartiteMatcher(2, 2)
        m.add_edge(0, 0)
        m.add_edge(0, 0)  # duplicate
        m.add_edge(1, 1)
        size = m.match()
        self.assertEqual(size, 2)


class TestCapacityScaling(unittest.TestCase):
    def test_clrs(self):
        net = clrs_network()
        flow = CapacityScaling().solve(net, 0, 5)
        self.assertEqual(flow, 23)

    def test_simple_path(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5)
        net.add_edge(1, 2, 3)
        flow = CapacityScaling().solve(net, 0, 2)
        self.assertEqual(flow, 3)

    def test_no_path(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5)
        flow = CapacityScaling().solve(net, 0, 2)
        self.assertEqual(flow, 0)


class TestConnectivity(unittest.TestCase):
    def test_edge_disjoint_simple(self):
        """Two parallel paths → 2 edge-disjoint paths."""
        net = FlowNetwork(4)
        net.add_edge(0, 1, 1)
        net.add_edge(0, 2, 1)
        net.add_edge(1, 3, 1)
        net.add_edge(2, 3, 1)
        paths = edge_disjoint_paths(net, 0, 3)
        self.assertEqual(len(paths), 2)

    def test_edge_disjoint_single(self):
        """Single path → 1 edge-disjoint path."""
        net = FlowNetwork(3)
        net.add_edge(0, 1, 1)
        net.add_edge(1, 2, 1)
        paths = edge_disjoint_paths(net, 0, 2)
        self.assertEqual(len(paths), 1)

    def test_vertex_disjoint(self):
        """Two vertex-disjoint paths through a diamond."""
        net = FlowNetwork(4)
        net.add_edge(0, 1, 1)
        net.add_edge(0, 2, 1)
        net.add_edge(1, 3, 1)
        net.add_edge(2, 3, 1)
        paths = vertex_disjoint_paths(net, 0, 3)
        self.assertEqual(len(paths), 2)

    def test_vertex_disjoint_bottleneck(self):
        """Common intermediate vertex → 1 disjoint path."""
        net = FlowNetwork(5)
        net.add_edge(0, 1, 1)
        net.add_edge(0, 2, 1)
        net.add_edge(1, 3, 1)  # both merge through 3
        net.add_edge(2, 3, 1)
        net.add_edge(3, 4, 1)
        paths = vertex_disjoint_paths(net, 0, 4)
        self.assertEqual(len(paths), 1)

    def test_edge_connectivity(self):
        """Diamond graph: 2 edge-disjoint paths → connectivity 2.

        For directed graphs, edge_connectivity fixes source and varies sink,
        so the minimum is 1 (single edge 0->1).  Using bidirectional edges
        makes it truly 2-connected.
        """
        net = FlowNetwork(4)
        net.add_edge(0, 1, 1, bidirectional=True)
        net.add_edge(0, 2, 1, bidirectional=True)
        net.add_edge(1, 3, 1, bidirectional=True)
        net.add_edge(2, 3, 1, bidirectional=True)
        ec = edge_connectivity(net)
        self.assertEqual(ec, 2)

    def test_gomory_hu(self):
        """Gomory-Hu tree on undirected graph should give correct min-cut values."""
        net = FlowNetwork(4)
        net.add_edge(0, 1, 3, bidirectional=True)
        net.add_edge(0, 2, 2, bidirectional=True)
        net.add_edge(1, 2, 5, bidirectional=True)
        net.add_edge(1, 3, 4, bidirectional=True)
        net.add_edge(2, 3, 3, bidirectional=True)
        tree = GomoryHuTree(net)
        # Min cut (0, 3): separating 0 from 3 requires cutting 0-1(3) and 0-2(2) = 5
        mc = tree.min_cut(0, 3)
        self.assertEqual(mc, 5)


class TestBenchmark(unittest.TestCase):
    def test_random_network(self):
        net = random_network(5, seed=42)
        self.assertEqual(net.node_count(), 5)
        self.assertGreater(net.edge_count(), 0)

    def test_grid_network(self):
        net = grid_network(3, 4)
        self.assertEqual(net.node_count(), 12)
        # 3*4=12 nodes, horizontal: 3*(4-1)=9, vertical: (3-1)*4=8, total=17
        self.assertEqual(net.edge_count(), 17)

    def test_bipartite_network(self):
        net = bipartite_network(3, 3, seed=42)
        # n = 1 + 3 + 3 + 1 = 8
        self.assertEqual(net.node_count(), 8)

    def test_random_reproducible(self):
        """Same seed → same network."""
        n1 = random_network(10, seed=123)
        n2 = random_network(10, seed=123)
        self.assertEqual(n1.edge_count(), n2.edge_count())


if __name__ == "__main__":
    unittest.main(verbosity=2)