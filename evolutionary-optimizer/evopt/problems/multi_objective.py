"""Built-in multi-objective benchmark problems."""

from __future__ import annotations

import random
from typing import List
from .base import ContinuousProblem, Problem
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..algorithms.nsga2 import MultiObjectiveProblem


class _MultiObjectiveMixin:
    """Mixin providing multi-objective interface.

    The actual MultiObjectiveProblem class in algorithms.nsga2 inherits from Problem
    and this mixin. We define it here to avoid circular imports.
    """
    maximize_list: list

    def evaluate(self, genome) -> float:
        """Single-objective fallback: return sum of objectives."""
        objs = self.evaluate_multi(genome)  # type: ignore
        return sum(o for o, m in zip(objs, self.maximize_list) if not m) - sum(o for o, m in zip(objs, self.maximize_list) if m)

    def evaluate_multi(self, genome) -> list:
        """Return a list of objective values. Override in subclass."""
        raise NotImplementedError("Subclasses must implement evaluate_multi")


class ZDT1(_MultiObjectiveMixin, ContinuousProblem):
    """ZDT1: bi-objective problem.

    f1(x) = x1
    f2(x) = g(x) * h(f1(x), g(x))
    where g = 1 + 9*mean(x[1:])
          h = 1 - sqrt(f1/g)

    Pareto front: f2 = 1 - sqrt(f1), f1 in [0, 1].
    """

    def __init__(self, dims: int = 10):
        Problem.__init__(self, maximize=False, constraints=None)
        self.dims = dims
        self.bounds = [(0, 1)] * dims
        self.maximize_list = [False, False]

    def evaluate_multi(self, genome) -> list:
        f1 = genome[0]
        g = 1 + 9 * sum(genome[1:]) / (len(genome) - 1)
        ratio = f1 / g if g > 0 else 0
        h = 1 - max(ratio, 0) ** 0.5
        f2 = g * h
        return [f1, f2]

    def random_genome(self) -> list:
        return [random.uniform(0, 1) for _ in range(self.dims)]

    def genome_size(self) -> int:
        return self.dims


class ZDT2(_MultiObjectiveMixin, ContinuousProblem):
    """ZDT2: bi-objective problem (concave Pareto front)."""

    def __init__(self, dims: int = 10):
        Problem.__init__(self, maximize=False, constraints=None)
        self.dims = dims
        self.bounds = [(0, 1)] * dims
        self.maximize_list = [False, False]

    def evaluate_multi(self, genome) -> list:
        f1 = genome[0]
        g = 1 + 9 * sum(genome[1:]) / (len(genome) - 1)
        ratio = f1 / g if g > 0 else 0
        h = 1 - max(ratio, 0) ** 2
        f2 = g * h
        return [f1, f2]

    def random_genome(self) -> list:
        return [random.uniform(0, 1) for _ in range(self.dims)]

    def genome_size(self) -> int:
        return self.dims