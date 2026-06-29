"""Additional benchmark problems for the evolutionary optimizer."""

from __future__ import annotations

import math
import random
from typing import List
from .base import ContinuousProblem


class Ackley(ContinuousProblem):
    """Ackley function — multimodal with a deep global minimum.

    f(x) = -20*exp(-0.2*sqrt(mean(x^2))) - exp(mean(cos(2πx))) + 20 + e
    Global minimum: f(0,...,0) = 0.
    """

    def __init__(self, dims: int = 2, bounds=(-32.768, 32.768)):
        super().__init__(dims=dims, bounds=bounds, maximize=False)

    def evaluate(self, genome):
        n = len(genome)
        sum_sq = sum(x ** 2 for x in genome)
        sum_cos = sum(math.cos(2 * math.pi * x) for x in genome)
        return (-20 * math.exp(-0.2 * math.sqrt(sum_sq / n))
                - math.exp(sum_cos / n) + 20 + math.e)


class Griewank(ContinuousProblem):
    """Griewank function — many local minima, single global minimum.

    f(x) = 1 + sum(x^2)/4000 - prod(cos(x/sqrt(i)))
    Global minimum: f(0,...,0) = 0.
    """

    def __init__(self, dims: int = 2, bounds=(-600, 600)):
        super().__init__(dims=dims, bounds=bounds, maximize=False)

    def evaluate(self, genome):
        sum_sq = sum(x ** 2 for x in genome)
        prod_cos = 1.0
        for i, x in enumerate(genome, 1):
            prod_cos *= math.cos(x / math.sqrt(i))
        return 1 + sum_sq / 4000 - prod_cos


class Schwefel(ContinuousProblem):
    """Schwefel function — deceptive landscape with global minimum far from origin.

    f(x) = 418.9829*n - sum(x * sin(sqrt(|x|)))
    Global minimum: f(420.9687,...,420.9687) = 0.
    """

    def __init__(self, dims: int = 2, bounds=(-500, 500)):
        super().__init__(dims=dims, bounds=bounds, maximize=False)

    def evaluate(self, genome):
        n = len(genome)
        return 418.9829 * n - sum(x * math.sin(math.sqrt(abs(x))) for x in genome)


class Michalewicz(ContinuousProblem):
    """Michalewicz function — steep valleys and ridges.

    f(x) = -sum(sin(x) * sin(i*x^2/π)^(2*m))
    Global minimum: depends on dimensionality.
    """

    def __init__(self, dims: int = 2, bounds=(0, math.pi), m: int = 10):
        super().__init__(dims=dims, bounds=bounds, maximize=False)
        self.m = m

    def evaluate(self, genome):
        total = 0.0
        for i, x in enumerate(genome, 1):
            total += math.sin(x) * (math.sin(i * x ** 2 / math.pi)) ** (2 * self.m)
        return -total


class Zakharov(ContinuousProblem):
    """Zakharov function — unimodal with a narrow valley.

    f(x) = sum(x^2) + (sum(i*x)/2)^2 + (sum(i*x)/2)^4
    Global minimum: f(0,...,0) = 0.
    """

    def __init__(self, dims: int = 2, bounds=(-5, 10)):
        super().__init__(dims=dims, bounds=bounds, maximize=False)

    def evaluate(self, genome):
        sum_sq = sum(x ** 2 for x in genome)
        weighted = sum((i + 1) * x for i, x in enumerate(genome)) / 2
        return sum_sq + weighted ** 2 + weighted ** 4