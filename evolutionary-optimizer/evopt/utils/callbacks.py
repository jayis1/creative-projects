"""Termination criteria and adaptive operators for evolutionary algorithms."""

from __future__ import annotations

from typing import Optional, Callable, Any
from ..core import Population


class TerminationCriterion:
    """Base class for termination criteria. Call as a callback."""

    def __call__(self, algorithm) -> bool:
        raise NotImplementedError

    def _finish(self, algorithm, reason: str):
        algorithm.max_generations = algorithm.generation
        algorithm.termination_reason = reason
        algorithm.terminated = True


class MaxGenerations(TerminationCriterion):
    """Stop after a maximum number of generations."""

    def __init__(self, max_gen: int):
        self.max_gen = max_gen

    def __call__(self, algorithm) -> bool:
        if algorithm.generation >= self.max_gen:
            self._finish(algorithm, f"Max generations reached: {self.max_gen}")
            return True
        algorithm.max_generations = self.max_gen
        return False


class FitnessThreshold(TerminationCriterion):
    """Stop when best fitness reaches or crosses a threshold."""

    def __init__(self, threshold: float, maximize: bool = False):
        self.threshold = threshold
        self.maximize = maximize

    def __call__(self, algorithm) -> bool:
        if algorithm.best_individual is None or algorithm.best_individual.fitness is None:
            return False
        fit = algorithm.best_individual.fitness
        if self.maximize:
            if fit >= self.threshold:
                self._finish(algorithm, f"Fitness threshold reached: {fit} >= {self.threshold}")
                return True
        else:
            if fit <= self.threshold:
                self._finish(algorithm, f"Fitness threshold reached: {fit} <= {self.threshold}")
                return True
        return False


class Stagnation(TerminationCriterion):
    """Stop if best fitness hasn't improved by more than epsilon for *patience* generations."""

    def __init__(self, patience: int = 20, epsilon: float = 1e-8):
        self.patience = patience
        self.epsilon = epsilon
        self._best = None
        self._stagnant = 0

    def __call__(self, algorithm) -> bool:
        if algorithm.best_individual is None or algorithm.best_individual.fitness is None:
            return False
        fit = algorithm.best_individual.fitness
        if self._best is None or abs(fit - self._best) > self.epsilon:
            self._best = fit
            self._stagnant = 0
        else:
            self._stagnant += 1
            if self._stagnant >= self.patience:
                self._finish(algorithm, f"Stagnation: no improvement for {self.patience} generations")
                return True
        return False


class TimeLimit(TerminationCriterion):
    """Stop after a wall-clock time limit (seconds)."""

    def __init__(self, seconds: float):
        self.seconds = seconds
        self._start = None

    def __call__(self, algorithm) -> bool:
        import time
        if self._start is None:
            self._start = time.time()
        elapsed = time.time() - self._start
        if elapsed >= self.seconds:
            self._finish(algorithm, f"Time limit reached: {elapsed:.1f}s >= {self.seconds}s")
            return True
        return False


class Convergence(TerminationCriterion):
    """Stop when population standard deviation falls below a threshold (population converged)."""

    def __init__(self, min_std: float = 1e-6):
        self.min_std = min_std

    def __call__(self, algorithm) -> bool:
        if algorithm.population is None:
            return False
        std = algorithm.population.fitness_std()
        if std is not None and std < self.min_std:
            self._finish(algorithm, f"Population converged: std={std:.2e} < {self.min_std}")
            return True
        return False


class AdaptiveMutationRate:
    """Callback that adapts mutation rate based on population diversity.

    If diversity drops below a threshold, increase mutation rate to escape local optima.
    If diversity is high, decrease mutation rate to exploit good solutions.
    """

    def __init__(self, low_diversity: float = 0.1, high_diversity: float = 0.5,
                 min_rate: float = 0.001, max_rate: float = 0.5):
        self.low_diversity = low_diversity
        self.high_diversity = high_diversity
        self.min_rate = min_rate
        self.max_rate = max_rate

    def __call__(self, algorithm):
        if algorithm.population is None or not hasattr(algorithm, 'mutation_rate'):
            return
        diversity = algorithm.population.diversity()
        if diversity < self.low_diversity:
            # Increase mutation to escape
            algorithm.mutation_rate = min(algorithm.mutation_rate * 1.5, self.max_rate)
        elif diversity > self.high_diversity:
            # Decrease mutation to exploit
            algorithm.mutation_rate = max(algorithm.mutation_rate * 0.9, self.min_rate)


class AdaptiveInertia:
    """Callback that linearly decreases PSO inertia weight over generations.

    Starts at w_start and linearly decreases to w_end, encouraging exploration early
    and exploitation later.
    """

    def __init__(self, w_start: float = 0.9, w_end: float = 0.4):
        self.w_start = w_start
        self.w_end = w_end

    def __call__(self, algorithm):
        if not hasattr(algorithm, 'inertia'):
            return
        progress = algorithm.generation / max(algorithm.max_generations, 1)
        algorithm.inertia = self.w_start - (self.w_start - self.w_end) * progress