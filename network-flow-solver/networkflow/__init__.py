"""
network-flow-solver: A from-scratch network flow solver toolkit.

Provides max-flow, min-cut, min-cost max-flow, bipartite matching,
and assignment problem solvers using multiple algorithms.
"""

from .graph import FlowNetwork, FlowEdge
from .maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel, CapacityScaling
from .mincost import MinCostMaxFlow, MinCostFlow
from .matching import BipartiteMatcher, AssignmentSolver
from .mincut import MinCut, StoerWagner
from .connectivity import edge_disjoint_paths, vertex_disjoint_paths, edge_connectivity, GomoryHuTree
from .benchmark import random_network, benchmark_solver, compare_solvers, print_comparison_table, grid_network, bipartite_network
from .dimacs import read_dimacs, write_dimacs
from .cli import main

__version__ = "2.0.0"
__all__ = [
    "FlowNetwork",
    "FlowEdge",
    "FordFulkerson",
    "EdmondsKarp",
    "Dinic",
    "PushRelabel",
    "CapacityScaling",
    "MinCostMaxFlow",
    "MinCostFlow",
    "BipartiteMatcher",
    "AssignmentSolver",
    "MinCut",
    "StoerWagner",
    "edge_disjoint_paths",
    "vertex_disjoint_paths",
    "edge_connectivity",
    "GomoryHuTree",
    "random_network",
    "benchmark_solver",
    "compare_solvers",
    "print_comparison_table",
    "grid_network",
    "bipartite_network",
    "read_dimacs",
    "write_dimacs",
    "main",
]