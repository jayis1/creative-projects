"""Rastrigin function problem."""

from __future__ import annotations

import math

from .base import ContinuousProblem


class Rastrigin(ContinuousProblem):
    """f(x) = 10*n + sum(x_i^2 - 10*cos(2*pi*x_i)) — highly multimodal.

    Global minimum: f(0,...,0) = 0.
    """

    def __init__(self, dims: int = 2, bounds=(-5.12, 5.12)):
        super().__init__(dims=dims, bounds=bounds, maximize=False)

    def evaluate(self, genome):
        n = len(genome)
        return 10 * n + sum(x * x - 10 * math.cos(2 * math.pi * x) for x in genome)