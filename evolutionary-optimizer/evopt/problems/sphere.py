"""Benchmark continuous optimization problems."""

from __future__ import annotations

from .base import ContinuousProblem


class Sphere(ContinuousProblem):
    """f(x) = sum(x_i^2) — the simplest unimodal test function.

    Global minimum: f(0,...,0) = 0.
    """

    def __init__(self, dims: int = 2, bounds=(-5.12, 5.12)):
        super().__init__(dims=dims, bounds=bounds, maximize=False)

    def evaluate(self, genome):
        return sum(x * x for x in genome)