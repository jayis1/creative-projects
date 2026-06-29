"""Built-in multi-objective benchmark problems."""

from __future__ import annotations

import random
from typing import List
from ..algorithms.nsga2 import MultiObjectiveProblem
from .base import ContinuousProblem


class ZDT1(MultiObjectiveProblem):
    """ZDT1: bi-objective problem.

    f1(x) = x1
    f2(x) = g(x) * h(f1(x), g(x))
    where g = 1 + 9*mean(x[1:])
          h = 1 - sqrt(f1/g)

    Pareto front: f2 = 1 - sqrt(f1), f1 in [0, 1].
    """

    def __init__(self, dims: int = 10):
        super().__init__(maximize_list=[False, False])
        self.dims = dims
        self.bounds = [(0, 1)] * dims

    def evaluate_multi(self, genome) -> List[float]:
        f1 = genome[0]
        g = 1 + 9 * sum(genome[1:]) / (len(genome) - 1)
        ratio = f1 / g if g > 0 else 0
        h = 1 - max(ratio, 0) ** 0.5
        f2 = g * h
        return [f1, f2]

    def random_genome(self) -> List[float]:
        return [random.uniform(0, 1) for _ in range(self.dims)]

    def genome_size(self) -> int:
        return self.dims


class ZDT2(MultiObjectiveProblem):
    """ZDT2: bi-objective problem (concave Pareto front)."""

    def __init__(self, dims: int = 10):
        super().__init__(maximize_list=[False, False])
        self.dims = dims
        self.bounds = [(0, 1)] * dims

    def evaluate_multi(self, genome) -> List[float]:
        f1 = genome[0]
        g = 1 + 9 * sum(genome[1:]) / (len(genome) - 1)
        ratio = f1 / g if g > 0 else 0
        h = 1 - max(ratio, 0) ** 2
        f2 = g * h
        return [f1, f2]

    def random_genome(self) -> List[float]:
        return [random.uniform(0, 1) for _ in range(self.dims)]

    def genome_size(self) -> int:
        return self.dims