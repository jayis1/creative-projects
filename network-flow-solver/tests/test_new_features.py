"""Tests for new features added in the comprehensive improvement.

Covers: BoykovKolmogorov, MultiSourceSink, CycleCanceling,
visualization, I/O formats, config, logging, flow decomposition.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow.graph import FlowNetwork
from networkflow.maxflow import Dinic, EdmondsKarp, PushRelabel
from networkflow.mincost import MinCostMaxFlow
from networkflow.advanced import BoykovKolmogorov, MultiSourceSink, CycleCanceling
from networkflow.visualization import to_dot, ascii_graph, flow_decomposition, ascii_flow_paths
from networkflow.io_formats import (
    read_edge_list, write_edge_list,
    read_adjacency_matrix, write_adjacency_matrix,
    read_graphml, write_graphml,
    read_lgf,
)
from networkflow.config import SolverConfig, load_config, save_config
from networkflow.logging_config import get_logger, setup_logging, set_level


def clrs_network():
    net = FlowNetwork(6)
    for u, v, c in [(0,1,16),(0,2,13),(1,2,10),(1,3,12),(2,1,4),(2,4,14),(3,2,9),(3,5,20),(4,3,7),(4,5,4)]:
        net.add_edge(u, v, c)
    return net


class TestBoykovKolmogorov(unittest.TestCase):
    def test_clrs(self):
        net = clrs_network()
        bk = BoykovKolmogorov()
        flow = bk.solve(net, 0, 5)
        self.assertEqual(flow, 23)

    def test_simple_path(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5)
        net.add_edge(1, 2, 3)
        bk = BoykovKolmogorov()
        flow = bk.solve(net, 0, 2)
        self.assertEqual(flow, 3)

    def test_no_path(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5)
        bk = BoykovKolmogorov()
        flow = bk.solve(net, 0, 2)
        self.assertEqual(flow, 0)

    def test_parallel_edges(self):
        net = FlowNetwork(2)
        net.add_edge(0, 1, 3)
        net.add_edge(0, 1, 7)
        bk = BoykovKolmogorov()
        flow = bk.solve(net, 0, 1)
        self.assertEqual(flow, 10)

    def test_bidirectional(self):
        net = FlowNetwork(2)
        net.add_edge(0, 1, 10, bidirectional=True)
        bk = BoykovKolmogorov()
        flow = bk.solve(net, 0, 1)
        self.assertEqual(flow, 10)

    def test_matches_dinic_random(self):
        """BK should produce same result as Dinic on random networks."""
        from networkflow.benchmark import random_network
        for seed in range(5):
            net = random_network(8, edge_prob=0.4, seed=seed)
            net_bk = net.copy()
            net_dinic = net.copy()
            f_bk = BoykovKolmogorov().solve(net_bk, 0, 7)
            f_dinic = Dinic().solve(net_dinic, 0, 7)
            self.assertEqual(f_bk, f_dinic,
                             f"BK={f_bk} != Dinic={f_dinic} for seed={seed}")


class TestMultiSourceSink(unittest.TestCase):
    def test_basic(self):
        net = FlowNetwork(5)
        net.add_edge(0, 2, 10)
        net.add_edge(1, 2, 5)
        net.add_edge(2, 3, 8)
        net.add_edge(2, 4, 7)
        ms = MultiSourceSink()
        flow, _ = ms.solve(net, sources=[0, 1], sinks=[3, 4])
        self.assertEqual(flow, 15)

    def test_with_caps(self):
        net = FlowNetwork(5)
        net.add_edge(0, 2, 10)
        net.add_edge(1, 2, 5)
        net.add_edge(2, 3, 8)
        net.add_edge(2, 4, 7)
        ms = MultiSourceSink()
        flow, _ = ms.solve(net, sources=[0, 1], sinks=[3, 4],
                           source_caps=[3, 2])
        self.assertEqual(flow, 5)

    def test_sink_caps(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 10)
        net.add_edge(0, 2, 10)
        ms = MultiSourceSink()
        flow, _ = ms.solve(net, sources=[0], sinks=[1, 2],
                           sink_caps=[3, 4])
        self.assertEqual(flow, 7)

    def test_no_sources_raises(self):
        net = FlowNetwork(3)
        ms = MultiSourceSink()
        with self.assertRaises(ValueError):
            ms.solve(net, sources=[], sinks=[1])

    def test_cap_length_mismatch(self):
        net = FlowNetwork(3)
        ms = MultiSourceSink()
        with self.assertRaises(ValueError):
            ms.solve(net, sources=[0], sinks=[1], source_caps=[1, 2])


class TestCycleCanceling(unittest.TestCase):
    def test_simple(self):
        net = FlowNetwork(4)
        net.add_edge(0, 1, 3, cost=1)
        net.add_edge(0, 2, 2, cost=2)
        net.add_edge(1, 3, 2, cost=3)
        net.add_edge(2, 3, 3, cost=1)
        cc = CycleCanceling()
        f, c = cc.solve(net, 0, 3)
        self.assertEqual(f, 4)
        self.assertEqual(c, 14)

    def test_matches_mcmf(self):
        """CycleCanceling should match MinCostMaxFlow on the same network."""
        from networkflow.benchmark import random_network
        for seed in range(3):
            net = random_network(6, edge_prob=0.5, seed=seed)
            # Add some costs
            import random
            rng = random.Random(seed)
            for u in range(net.n):
                for e in net.graph[u]:
                    if e.cap > 0:
                        e.cost = rng.randint(1, 10)

            net_cc = net.copy()
            net_mcmf = net.copy()
            cc = CycleCanceling()
            f_cc, c_cc = cc.solve(net_cc, 0, 5)
            mcmf = MinCostMaxFlow()
            f_mcmf, c_mcmf = mcmf.solve(net_mcmf, 0, 5)
            self.assertEqual(f_cc, f_mcmf)
            # Costs should be equal (both find min cost)
            self.assertEqual(c_cc, c_mcmf,
                             f"CC cost={c_cc} != MCMF cost={c_mcmf} for seed={seed}")


class TestVisualization(unittest.TestCase):
    def test_dot_output(self):
        net = clrs_network()
        dot = to_dot(net, source=0, sink=5)
        self.assertTrue(dot.startswith("digraph"))
        self.assertIn("rankdir=LR", dot)
        self.assertIn("0 -> 1", dot)

    def test_dot_with_flows(self):
        net = clrs_network()
        Dinic().solve(net, 0, 5)
        dot = to_dot(net, source=0, sink=5, show_flows=True)
        self.assertIn("/", dot)  # flow/cap format

    def test_dot_with_residuals(self):
        net = clrs_network()
        Dinic().solve(net, 0, 5)
        dot = to_dot(net, show_residuals=True)
        self.assertIn("dashed", dot)

    def test_ascii_graph(self):
        net = clrs_network()
        text = ascii_graph(net, source=0, sink=5)
        self.assertIn("From", text)
        self.assertIn("Cap", text)
        self.assertIn("source", text)

    def test_ascii_with_flows(self):
        net = clrs_network()
        Dinic().solve(net, 0, 5)
        text = ascii_graph(net, show_flows=True)
        self.assertIn("Flow", text)
        self.assertIn("Util%", text)

    def test_flow_decomposition(self):
        net = clrs_network()
        Dinic().solve(net, 0, 5)
        paths = flow_decomposition(net, 0, 5)
        total = sum(a for _, a in paths)
        self.assertEqual(total, 23)
        for path, amount in paths:
            self.assertEqual(path[0], 0)
            self.assertEqual(path[-1], 5)
            self.assertGreater(amount, 0)

    def test_flow_decomposition_no_flow(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5)
        net.add_edge(1, 2, 3)
        paths = flow_decomposition(net, 0, 2)
        self.assertEqual(len(paths), 0)

    def test_ascii_flow_paths(self):
        net = clrs_network()
        Dinic().solve(net, 0, 5)
        paths = flow_decomposition(net, 0, 5)
        text = ascii_flow_paths(paths)
        self.assertIn("Flow decomposition", text)
        self.assertIn("Total flow", text)


class TestIOFormats(unittest.TestCase):
    def test_edge_list_roundtrip(self):
        net = clrs_network()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.edges', delete=False) as f:
            path = f.name
        try:
            write_edge_list(net, path)
            net2, src, snk = read_edge_list(path, source=0, sink=5)
            self.assertEqual(net2.edge_count(), net.edge_count())
            self.assertEqual(src, 0)
            self.assertEqual(snk, 5)
        finally:
            os.unlink(path)

    def test_edge_list_with_costs(self):
        net = FlowNetwork(3)
        net.add_edge(0, 1, 5, cost=3)
        net.add_edge(1, 2, 3, cost=2)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.edges', delete=False) as f:
            path = f.name
        try:
            write_edge_list(net, path)
            net2, _, _ = read_edge_list(path)
            # Check cost is preserved
            for e in net2.graph[0]:
                if e.cap > 0:
                    self.assertEqual(e.cost, 3)
        finally:
            os.unlink(path)

    def test_adjacency_matrix_roundtrip(self):
        net = clrs_network()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            path = f.name
        try:
            write_adjacency_matrix(net, path)
            net2, _, _ = read_adjacency_matrix(path, source=0, sink=5)
            self.assertEqual(net2.edge_count(), net.edge_count())
        finally:
            os.unlink(path)

    def test_graphml_roundtrip(self):
        net = clrs_network()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.graphml', delete=False) as f:
            path = f.name
        try:
            write_graphml(net, path, source=0, sink=5)
            net2, src, snk = read_graphml(path)
            self.assertEqual(net2.edge_count(), net.edge_count())
            self.assertEqual(src, 0)
            self.assertEqual(snk, 5)
        finally:
            os.unlink(path)

    def test_edge_list_comments(self):
        """Edge list with comments and extra whitespace."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.edges', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("0 1 10\n")
            f.write("  1   2   5  3\n")  # with cost
            f.write("# Another comment\n")
            f.write("0 2 7\n")
            path = f.name
        try:
            net, src, snk = read_edge_list(path, source=0, sink=2)
            self.assertEqual(net.node_count(), 3)
            self.assertEqual(net.edge_count(), 3)
        finally:
            os.unlink(path)


class TestConfig(unittest.TestCase):
    def test_roundtrip(self):
        cfg = SolverConfig(algorithm="dinic", source=0, sink=5,
                           network_file="net.json", log_level="DEBUG")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            save_config(cfg, path)
            cfg2 = load_config(path)
            self.assertEqual(cfg2.algorithm, "dinic")
            self.assertEqual(cfg2.source, 0)
            self.assertEqual(cfg2.sink, 5)
            self.assertEqual(cfg2.network_file, "net.json")
            self.assertEqual(cfg2.log_level, "DEBUG")
        finally:
            os.unlink(path)

    def test_defaults(self):
        cfg = SolverConfig()
        self.assertEqual(cfg.algorithm, "dinic")
        self.assertEqual(cfg.source, 0)

    def test_logging_subdict(self):
        """Config with 'logging' sub-dict should populate log_level/log_file."""
        import json
        data = {
            "algorithm": "edmonds-karp",
            "logging": {"level": "INFO", "file": "test.log"}
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = load_config(path)
            self.assertEqual(cfg.algorithm, "edmonds-karp")
            self.assertEqual(cfg.log_level, "INFO")
            self.assertEqual(cfg.log_file, "test.log")
        finally:
            os.unlink(path)


class TestLogging(unittest.TestCase):
    def test_get_logger(self):
        logger = get_logger()
        self.assertIsNotNone(logger)

    def test_setup_logging(self):
        logger = setup_logging("WARNING")
        self.assertEqual(logger.level, 30)  # WARNING = 30

    def test_set_level(self):
        setup_logging("DEBUG")
        set_level("ERROR")
        logger = get_logger()
        self.assertEqual(logger.level, 40)  # ERROR = 40


if __name__ == "__main__":
    unittest.main(verbosity=2)