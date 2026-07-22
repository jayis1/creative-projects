"""
network-flow-solver: A from-scratch network flow solver toolkit.

Provides max-flow, min-cut, min-cost max-flow, bipartite matching,
assignment problem solvers, connectivity analysis, graph I/O,
visualization, and benchmarking — all in pure Python with no
external dependencies.

Example
-------
>>> from networkflow import FlowNetwork, Dinic
>>> net = FlowNetwork(6)
>>> net.add_edge(0, 1, 16)
>>> net.add_edge(0, 2, 13)
>>> net.add_edge(1, 3, 12)
>>> net.add_edge(2, 4, 14)
>>> net.add_edge(3, 5, 20)
>>> net.add_edge(4, 5, 4)
>>> Dinic().solve(net, 0, 5)
23
"""

from .graph import FlowNetwork, FlowEdge
from .maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel, CapacityScaling
from .mincost import MinCostMaxFlow, MinCostFlow
from .matching import BipartiteMatcher, AssignmentSolver
from .mincut import MinCut, StoerWagner
from .connectivity import edge_disjoint_paths, vertex_disjoint_paths, edge_connectivity, GomoryHuTree
from .benchmark import random_network, benchmark_solver, compare_solvers, print_comparison_table, grid_network, bipartite_network
from .dimacs import read_dimacs, write_dimacs
from .advanced import BoykovKolmogorov, MultiSourceSink, CycleCanceling
from .visualization import to_dot, ascii_graph, flow_decomposition, ascii_flow_paths
from .io_formats import (
    read_edge_list, write_edge_list,
    read_adjacency_matrix, write_adjacency_matrix,
    read_graphml, write_graphml,
    read_lgf,
)
from .config import SolverConfig, load_config, save_config
from .logging_config import get_logger, setup_logging, set_level
from .cli import main

__version__ = "3.0.0"
__all__ = [
    # Core data structures
    "FlowNetwork",
    "FlowEdge",
    # Max-flow solvers
    "FordFulkerson",
    "EdmondsKarp",
    "Dinic",
    "PushRelabel",
    "CapacityScaling",
    "BoykovKolmogorov",
    # Multi-source/sink
    "MultiSourceSink",
    # Min-cost flow
    "MinCostMaxFlow",
    "MinCostFlow",
    "CycleCanceling",
    # Matching & assignment
    "BipartiteMatcher",
    "AssignmentSolver",
    # Min-cut
    "MinCut",
    "StoerWagner",
    # Connectivity
    "edge_disjoint_paths",
    "vertex_disjoint_paths",
    "edge_connectivity",
    "GomoryHuTree",
    # Benchmarking
    "random_network",
    "benchmark_solver",
    "compare_solvers",
    "print_comparison_table",
    "grid_network",
    "bipartite_network",
    # DIMACS I/O
    "read_dimacs",
    "write_dimacs",
    # Additional I/O formats
    "read_edge_list",
    "write_edge_list",
    "read_adjacency_matrix",
    "write_adjacency_matrix",
    "read_graphml",
    "write_graphml",
    "read_lgf",
    # Visualization
    "to_dot",
    "ascii_graph",
    "flow_decomposition",
    "ascii_flow_paths",
    # Config
    "SolverConfig",
    "load_config",
    "save_config",
    # Logging
    "get_logger",
    "setup_logging",
    "set_level",
    # CLI
    "main",
]