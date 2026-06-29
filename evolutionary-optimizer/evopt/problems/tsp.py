"""Traveling Salesman Problem (combinatorial)."""

from __future__ import annotations

import random
import math
from typing import List, Tuple

from .base import CombinatorialProblem


class TSP(CombinatorialProblem):
    """Euclidean TSP: find the shortest tour visiting all cities exactly once.

    Args:
        cities: List of (x, y) coordinates.
        maximize: If False (default), minimize tour length.

    Genome representation: a permutation [0, 1, ..., n-1] of city indices.
    """

    def __init__(self, cities: List[Tuple[float, float]], maximize: bool = False):
        super().__init__(maximize=maximize)
        if len(cities) < 2:
            raise ValueError("Need at least 2 cities for TSP")
        self.cities = cities
        self.n = len(cities)
        self._dist_cache = {}
        self._precompute_distances()

    def _precompute_distances(self):
        """Precompute pairwise distances for speed."""
        for i in range(self.n):
            for j in range(i + 1, self.n):
                dx = self.cities[i][0] - self.cities[j][0]
                dy = self.cities[i][1] - self.cities[j][1]
                d = math.sqrt(dx * dx + dy * dy)
                self._dist_cache[(i, j)] = d
                self._dist_cache[(j, i)] = d

    def dist(self, i: int, j: int) -> float:
        return self._dist_cache[(i, j)]

    def evaluate(self, genome: List[int]) -> float:
        """Total tour length: genome[0] -> genome[1] -> ... -> genome[0]."""
        total = 0.0
        n = len(genome)
        for i in range(n):
            total += self.dist(genome[i], genome[(i + 1) % n])
        return total

    def random_genome(self) -> List[int]:
        """Return a random permutation of [0, 1, ..., n-1]."""
        perm = list(range(self.n))
        random.shuffle(perm)
        return perm

    def genome_size(self) -> int:
        return self.n

    def repair(self, genome: List[int]) -> List[int]:
        """Repair a permutation (ensure all cities present exactly once)."""
        missing = set(range(self.n)) - set(genome)
        if not missing:
            return genome
        # Replace duplicates with missing cities
        seen = set()
        result = []
        for g in genome:
            if g in seen:
                result.append(missing.pop())
            else:
                result.append(g)
                seen.add(g)
        return result

    @classmethod
    def random_cities(cls, n: int = 20, seed: int = 42) -> "TSP":
        """Generate a random TSP instance with n cities in [0,100)x[0,100)."""
        rng = random.Random(seed)
        cities = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
        return cls(cities)