"""Base algorithm class and common utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict, Any
from ..core import Individual, Population
from ..problems.base import Problem
from ..utils.statistics import Statistics
from ..utils.logging_utils import get_logger


class BaseAlgorithm(ABC):
    """Base class for all evolutionary algorithms.

    Args:
        problem: The optimization problem to solve.
        population_size: Number of individuals in the population.
        max_generations: Maximum number of generations.
        maximize: Override problem.maximize if needed.
        seed: Random seed for reproducibility.
        verbose: If True, print progress.
        callbacks: List of callback functions called after each generation.
    """

    def __init__(self, problem: Problem, population_size: int = 100,
                 max_generations: int = 100, maximize: Optional[bool] = None,
                 seed: Optional[int] = None, verbose: bool = False,
                 callbacks: Optional[List[Callable]] = None):
        self.problem = problem
        self.population_size = population_size
        self.max_generations = max_generations
        self.maximize = maximize if maximize is not None else problem.maximize
        self.seed = seed
        self.verbose = verbose
        self.callbacks = callbacks or []
        self.logger = get_logger(self.__class__.__name__, verbose)

        self.population: Optional[Population] = None
        self.generation: int = 0
        self.statistics = Statistics()
        self.best_individual: Optional[Individual] = None
        self.history: List[Dict[str, Any]] = []
        self.terminated: bool = False
        self.termination_reason: str = ""

        if seed is not None:
            import random as _random
            _random.seed(seed)

    @abstractmethod
    def initialize(self) -> Population:
        """Create the initial population."""
        ...

    @abstractmethod
    def evolve_one_generation(self) -> Population:
        """Run one generation of evolution and return the new population."""
        ...

    def evaluate_population(self, population: Population) -> None:
        """Evaluate all unevaluated individuals in the population."""
        for ind in population.individuals:
            if ind.fitness is None:
                fitness, violations = self.problem.evaluate_with_constraints(ind.genome)
                ind.fitness = fitness
                ind.constraints = violations

    def update_best(self, population: Population) -> None:
        """Update self.best_individual if a new best is found."""
        best = population.best(maximize=self.maximize)
        if best is None:
            return
        if self.best_individual is None:
            self.best_individual = best.clone()
        else:
            if self.maximize:
                if best.fitness > self.best_individual.fitness:
                    self.best_individual = best.clone()
            else:
                if best.fitness < self.best_individual.fitness:
                    self.best_individual = best.clone()

    def record_statistics(self) -> None:
        """Record statistics for the current generation."""
        if self.population is None:
            return
        gen_stats = {
            "generation": self.generation,
            "best_fitness": self.best_individual.fitness if self.best_individual else None,
            "avg_fitness": self.population.average_fitness(),
            "std_fitness": self.population.fitness_std(),
            "diversity": self.population.diversity(),
            "population_size": len(self.population),
        }
        self.history.append(gen_stats)
        self.statistics.update(gen_stats)
        if self.verbose:
            best_str = f"{gen_stats['best_fitness']:.6g}" if gen_stats['best_fitness'] is not None else "N/A"
            avg_str = f"{gen_stats['avg_fitness']:.6g}" if gen_stats['avg_fitness'] is not None else "N/A"
            self.logger.info(
                f"Gen {self.generation}: best={best_str} "
                f"avg={avg_str} "
                f"diversity={gen_stats['diversity']:.3f}"
            )

    def should_terminate(self) -> bool:
        """Check termination criteria. Override for custom criteria."""
        return self.generation >= self.max_generations

    def run(self) -> Individual:
        """Run the evolutionary algorithm and return the best individual."""
        import random as _random
        if self.seed is not None:
            _random.seed(self.seed)
            # Also seed numpy if available (for CMA-ES and other numpy-based algorithms)
            try:
                import numpy as _np
                _np.random.seed(self.seed)
            except ImportError:
                pass

        self.population = self.initialize()
        self.evaluate_population(self.population)
        self.update_best(self.population)
        self.record_statistics()
        self._run_callbacks()

        while not self.should_terminate():
            self.generation += 1
            self.population = self.evolve_one_generation()
            self.evaluate_population(self.population)
            self.update_best(self.population)
            self.record_statistics()
            self._run_callbacks()

        # Respect termination reason set by should_terminate() or callbacks;
        # only default to max_generations if no reason was set.
        if not self.terminated or not self.termination_reason:
            self.terminated = True
            self.termination_reason = f"Reached max_generations={self.max_generations}"
        if self.verbose:
            self.logger.info(f"Algorithm terminated: {self.termination_reason}")
            self.logger.info(f"Best fitness: {self.best_individual.fitness if self.best_individual else 'N/A'}")
        return self.best_individual

    def _run_callbacks(self):
        for cb in self.callbacks:
            cb(self)