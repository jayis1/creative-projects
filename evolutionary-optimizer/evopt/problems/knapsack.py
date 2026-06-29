"""0/1 Knapsack problem (combinatorial)."""

from __future__ import annotations

import random
from typing import List, Tuple

from .base import CombinatorialProblem


class Knapsack(CombinatorialProblem):
    """0/1 Knapsack: maximize value subject to weight constraint.

    Args:
        items: List of (weight, value) tuples.
        capacity: Maximum total weight allowed.
        maximize: Should always be True for knapsack.

    Genome representation: binary list [0, 1, ..., 0] (1 = item included).
    """

    def __init__(self, items: List[Tuple[float, float]], capacity: float, maximize: bool = True):
        super().__init__(maximize=maximize)
        if not items:
            raise ValueError("Need at least one item")
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.items = items
        self.capacity = capacity
        self.n = len(items)

    def evaluate(self, genome: List[int]) -> float:
        """Return total value of selected items, or heavily penalized value if over capacity.

        For maximization (default): infeasible solutions get -1 - overweight penalty,
        which is always worse than any feasible solution (value >= 0).
        For minimization: infeasible solutions get a large positive penalty.
        """
        total_weight = 0.0
        total_value = 0.0
        for i, bit in enumerate(genome):
            if bit:
                w, v = self.items[i]
                total_weight += w
                total_value += v
        if total_weight > self.capacity:
            # Infeasible: penalize heavily so it's always worse than feasible solutions
            overweight = total_weight - self.capacity
            if self.maximize:
                # Return negative value so it's worse than any feasible (value >= 0)
                return -1.0 - overweight
            else:
                # Return large positive value so it's worse than any feasible minimization
                return 1e6 + overweight
        return total_value

    def random_genome(self) -> List[int]:
        """Generate a random feasible or near-feasible genome."""
        # Try to generate a feasible genome by adding items randomly
        indices = list(range(self.n))
        random.shuffle(indices)
        genome = [0] * self.n
        total_w = 0.0
        for idx in indices:
            w, v = self.items[idx]
            if total_w + w <= self.capacity:
                genome[idx] = 1
                total_w += w
        return genome

    def genome_size(self) -> int:
        return self.n

    def repair(self, genome: List[int]) -> List[int]:
        """Repair: if over capacity, remove items with worst value/weight ratio."""
        total_weight = sum(self.items[i][0] for i, b in enumerate(genome) if b)
        if total_weight <= self.capacity:
            return genome
        # Sort included items by value/weight ratio (ascending = remove first)
        included = [(i, self.items[i][1] / max(self.items[i][0], 1e-12))
                    for i in range(self.n) if genome[i]]
        included.sort(key=lambda x: x[1])
        while total_weight > self.capacity and included:
            idx, _ = included.pop(0)
            genome[idx] = 0
            total_weight -= self.items[idx][0]
        return genome

    @classmethod
    def random_items(cls, n: int = 30, max_weight: float = 10.0,
                     max_value: float = 100.0, seed: int = 42) -> Tuple["Knapsack", List[Tuple[float, float]]]:
        """Generate a random knapsack instance with n items."""
        rng = random.Random(seed)
        items = [(rng.uniform(1, max_weight), rng.uniform(1, max_value)) for _ in range(n)]
        total_w = sum(w for w, _ in items)
        capacity = total_w * 0.4  # 40% of total weight
        return cls(items, capacity), items