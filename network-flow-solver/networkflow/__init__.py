"""
network-flow-solver: A from-scratch network flow solver toolkit.

Provides max-flow, min-cut, min-cost max-flow, bipartite matching,
and assignment problem solvers using multiple algorithms.
"""

from .graph import FlowNetwork, FlowEdge
from .maxflow import FordFulkerson, EdmondsKarp, Dinic, PushRelabel
from .mincost import MinCostMaxFlow
from .matching import BipartiteMatcher, AssignmentSolver
from .mincut import MinCut
from .cli import main

__version__ = "1.0.0"
__all__ = [
    "FlowNetwork",
    "FlowEdge",
    "FordFulkerson",
    "EdmondsKarp",
    "Dinic",
    "PushRelabel",
    "MinCostMaxFlow",
    "BipartiteMatcher",
    "AssignmentSolver",
    "MinCut",
    "main",
]