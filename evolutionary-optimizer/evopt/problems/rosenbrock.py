"""Rosenbrock function problem."""

from __future__ import annotations

from .base import ContinuousProblem


class Rosenbrock(ContinuousProblem):
    """f(x) = sum(100*(x_{i+1} - x_i^2)^2 + (1 - x_i)^2) — the 'banana' function.

    Global minimum: f(1,...,1) = 0.
    """

    def __init__(self, dims: int = 2, bounds=(-2.048, 2.048)):
        super().__init__(dims=dims, bounds=bounds, maximize=False)

    def evaluate(self, genome):
        n = len(genome)
        return sum(100 * (genome[i + 1] - genome[i] ** 2) ** 2 + (1 - genome[i]) ** 2 for i in range(n - 1))