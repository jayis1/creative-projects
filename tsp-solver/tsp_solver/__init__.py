"""tsp_solver — a Traveling Salesman Problem solver.

This package provides exact, approximation, and metaheuristic algorithms
for the classic NP-hard Traveling Salesman Problem (TSP).

Public API
----------
- :class:`TSPInstance` — represent a TSP instance with city coordinates or an
  explicit distance matrix.
- :class:`Tour` — an immutable tour representation with O(1) length lookup.
- :func:`solve` — convenience function that runs a named algorithm.
- Algorithm modules: :mod:`exact`, :mod:`heuristics`, :mod:`local_search`,
  :mod:`metaheuristics`, :mod:`approximation`.
- :func:`generate_instance` — generate random Euclidean instances.
- :func:`load_tsplib` — load instances from simple TSPLIB-style text files.
"""

from .instance import TSPInstance, generate_instance, load_tsplib
from .tour import Tour
from .exact import held_karp, branch_and_bound
from .heuristics import nearest_neighbor, nearest_insertion, farthest_insertion, greedy
from .local_search import two_opt, three_opt, or_opt
from .metaheuristics import simulated_annealing, genetic_algorithm, ant_colony
from .approximation import mst_approx, christofides
from .solver import solve

__all__ = [
    "TSPInstance",
    "Tour",
    "generate_instance",
    "load_tsplib",
    "held_karp",
    "branch_and_bound",
    "nearest_neighbor",
    "nearest_insertion",
    "farthest_insertion",
    "greedy",
    "two_opt",
    "three_opt",
    "or_opt",
    "simulated_annealing",
    "genetic_algorithm",
    "ant_colony",
    "mst_approx",
    "christofides",
    "solve",
]

__version__ = "1.0.0"