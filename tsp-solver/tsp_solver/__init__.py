"""tsp_solver — a Traveling Salesman Problem solver.

This package provides exact, approximation, and metaheuristic algorithms
for the classic NP-hard Traveling Salesman Problem (TSP).

Public API
----------
- :class:`TSPInstance` — represent a TSP instance with city coordinates or an
  explicit distance matrix.
- :class:`Tour` — an immutable tour representation with O(1) length lookup.
- :func:`solve` — convenience function that runs a named algorithm.
- :func:`list_algorithms` — list all available algorithm names.
- Algorithm modules: :mod:`exact`, :mod:`heuristics`, :mod:`local_search`,
  :mod:`metaheuristics`, :mod:`approximation`, :mod:`advanced`.
- :func:`generate_instance` — generate random Euclidean instances.
- :func:`load_tsplib` — load instances from TSPLIB-style text files.
- :class:`BenchmarkSuite` — benchmark and compare all algorithms.
- :class:`SolverConfig` — typed configuration for the solver and CLI.
"""

from .instance import TSPInstance, generate_instance, load_tsplib
from .tour import Tour
from .exact import held_karp, branch_and_bound
from .heuristics import nearest_neighbor, nearest_neighbor_multistart, nearest_insertion, farthest_insertion, greedy
from .local_search import two_opt, three_opt, or_opt
from .metaheuristics import simulated_annealing, genetic_algorithm, ant_colony
from .approximation import mst_approx, christofides
from .advanced import savings, iterated_local_search, lin_kernighan, double_bridge
from .solver import solve, list_algorithms, list_algorithms_by_category, algorithm_category
from .benchmark import BenchmarkSuite, BenchmarkResult
from .viz import ascii_plot, tour_to_json
from .config import SolverConfig

__all__ = [
    "TSPInstance",
    "Tour",
    "generate_instance",
    "load_tsplib",
    "held_karp",
    "branch_and_bound",
    "nearest_neighbor",
    "nearest_neighbor_multistart",
    "nearest_insertion",
    "farthest_insertion",
    "greedy",
    "savings",
    "two_opt",
    "three_opt",
    "or_opt",
    "simulated_annealing",
    "genetic_algorithm",
    "ant_colony",
    "mst_approx",
    "christofides",
    "iterated_local_search",
    "lin_kernighan",
    "double_bridge",
    "solve",
    "list_algorithms",
    "list_algorithms_by_category",
    "algorithm_category",
    "BenchmarkSuite",
    "BenchmarkResult",
    "ascii_plot",
    "tour_to_json",
    "SolverConfig",
]

__version__ = "2.0.0"