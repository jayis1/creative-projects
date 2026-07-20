"""Unified solver dispatcher with optional local-search refinement."""

from __future__ import annotations

from typing import Optional

from .instance import TSPInstance
from .tour import Tour
from .exact import held_karp, branch_and_bound
from .heuristics import nearest_neighbor, nearest_neighbor_multistart, nearest_insertion, farthest_insertion, greedy
from .local_search import two_opt, three_opt, or_opt
from .metaheuristics import simulated_annealing, genetic_algorithm, ant_colony
from .approximation import mst_approx, christofides
from .advanced import savings, iterated_local_search, lin_kernighan


_ALGORITHMS = {
    "held_karp": held_karp,
    "branch_and_bound": branch_and_bound,
    "nearest_neighbor": nearest_neighbor,
    "nearest_neighbor_multistart": nearest_neighbor_multistart,
    "nearest_insertion": nearest_insertion,
    "farthest_insertion": farthest_insertion,
    "greedy": greedy,
    "savings": savings,
    "mst_approx": mst_approx,
    "christofides": christofides,
    "two_opt": two_opt,
    "three_opt": three_opt,
    "or_opt": or_opt,
    "simulated_annealing": simulated_annealing,
    "genetic_algorithm": genetic_algorithm,
    "ant_colony": ant_colony,
    "iterated_local_search": iterated_local_search,
    "lin_kernighan": lin_kernighan,
}

_ALGORITHM_CATEGORIES = {
    "exact": ["held_karp", "branch_and_bound"],
    "approximation": ["mst_approx", "christofides"],
    "construction": ["nearest_neighbor", "nearest_neighbor_multistart", "nearest_insertion", "farthest_insertion", "greedy", "savings"],
    "local_search": ["two_opt", "three_opt", "or_opt"],
    "metaheuristic": ["simulated_annealing", "genetic_algorithm", "ant_colony", "iterated_local_search", "lin_kernighan"],
}


def list_algorithms() -> list[str]:
    """Return the names of all available algorithms, sorted."""
    return sorted(_ALGORITHMS.keys())


def list_algorithms_by_category() -> dict[str, list[str]]:
    """Return algorithms grouped by category."""
    return dict(_ALGORITHM_CATEGORIES)


def algorithm_category(name: str) -> Optional[str]:
    """Return the category of an algorithm, or None if unknown."""
    for cat, algos in _ALGORITHM_CATEGORIES.items():
        if name in algos:
            return cat
    return None


_STOCHASTIC = {"simulated_annealing", "genetic_algorithm", "ant_colony",
               "nearest_neighbor_multistart", "iterated_local_search", "lin_kernighan"}


def solve(
    instance: TSPInstance,
    algorithm: str = "nearest_neighbor",
    *,
    refine: Optional[str] = None,
    seed: Optional[int] = None,
    **kwargs,
) -> Tour:
    """Solve a TSP instance with the named algorithm.

    Parameters
    ----------
    instance : TSPInstance
    algorithm : str
        One of the keys returned by :func:`list_algorithms`.
    refine : str, optional
        Local search to apply after the main algorithm. One of
        ``"two_opt"``, ``"three_opt"``, ``"or_opt"``.
    seed : int, optional
        RNG seed for stochastic algorithms.
    **kwargs
        Algorithm-specific keyword arguments.

    Raises
    ------
    ValueError
        If *algorithm* or *refine* is not recognized.
    """
    if algorithm not in _ALGORITHMS:
        raise ValueError(
            f"Unknown algorithm {algorithm!r}. Available: {list_algorithms()}"
        )
    func = _ALGORITHMS[algorithm]
    if algorithm in _STOCHASTIC and seed is not None:
        kwargs.setdefault("seed", seed)
    tour = func(instance, **kwargs)
    if refine is not None:
        refiners = {"two_opt": two_opt, "three_opt": three_opt, "or_opt": or_opt}
        if refine not in refiners:
            raise ValueError(f"Unknown refiner {refine!r}. Available: {list(refiners)}")
        tour = refiners[refine](instance, tour)
    return tour