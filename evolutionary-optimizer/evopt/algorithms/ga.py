"""Genetic Algorithm (GA) — the classic evolutionary algorithm."""

from __future__ import annotations

import random
from typing import Callable, Optional, List
from ..core import Individual, Population
from ..problems.base import Problem, ContinuousProblem
from ..operators.selection import tournament_selection
from ..operators.crossover import uniform_crossover, sbx_crossover, order_crossover
from ..operators.mutation import gaussian_mutation, bit_flip_mutation, swap_mutation, polynomial_mutation
from .base import BaseAlgorithm


class GeneticAlgorithm(BaseAlgorithm):
    """A configurable genetic algorithm.

    Automatically detects continuous, binary, or permutation problems based on genome type.
    Uses appropriate crossover and mutation operators for each type.

    Args:
        problem: The optimization problem.
        population_size: Population size (default 100).
        max_generations: Maximum generations (default 100).
        elite_size: Number of elites preserved each generation (default 1).
        tournament_k: Tournament size for selection (default 3).
        crossover_rate: Probability of crossover (default 0.85).
        mutation_rate: Per-gene mutation probability (default 0.1).
        mutation_sigma: Std for Gaussian mutation (continuous only, default 0.2).
        sbx_eta: Distribution index for SBX crossover (continuous, default 15).
        poly_eta: Distribution index for polynomial mutation (continuous, default 20).
        maximize: Override maximize direction.
        seed: Random seed.
        verbose: Print progress.
    """

    def __init__(self, problem: Problem, population_size: int = 100,
                 max_generations: int = 100, elite_size: int = 1,
                 tournament_k: int = 3, crossover_rate: float = 0.85,
                 mutation_rate: float = 0.1, mutation_sigma: float = 0.2,
                 sbx_eta: float = 15.0, poly_eta: float = 20.0,
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size, max_generations, maximize, seed, verbose, callbacks)
        self.elite_size = elite_size
        self.tournament_k = tournament_k
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.mutation_sigma = mutation_sigma
        self.sbx_eta = sbx_eta
        self.poly_eta = poly_eta
        self._genome_type: Optional[str] = None  # 'continuous', 'binary', or 'permutation'

    def _detect_genome_type(self, genome) -> str:
        """Detect genome type from a sample genome."""
        if isinstance(genome, list) and len(genome) > 0:
            sample = genome[0]
            if isinstance(sample, float):
                return "continuous"
            elif isinstance(sample, int) and len(genome) > 2:
                # Check if it's a permutation (contains all values 0..n-1)
                if sorted(genome) == list(range(len(genome))):
                    return "permutation"
                else:
                    return "binary"
            elif isinstance(sample, int):
                return "binary"
        return "continuous"  # default

    def initialize(self) -> Population:
        """Create and return the initial population."""
        pop = Population()
        for _ in range(self.population_size):
            genome = self.problem.random_genome()
            pop.append(Individual(genome))
        # Detect genome type from first individual
        if len(pop) > 0:
            self._genome_type = self._detect_genome_type(pop[0].genome)
        return pop

    def _crossover(self, p1_genome, p2_genome):
        """Apply the appropriate crossover for the genome type."""
        if self._genome_type == "continuous":
            c1, c2 = sbx_crossover(p1_genome, p2_genome, eta=self.sbx_eta, prob=self.crossover_rate)
            return c1, c2
        elif self._genome_type == "permutation":
            return order_crossover(p1_genome, p2_genome)
        else:  # binary
            return uniform_crossover(p1_genome, p2_genome, prob=0.5)

    def _mutate(self, genome):
        """Apply the appropriate mutation for the genome type."""
        if self._genome_type == "continuous":
            bounds = getattr(self.problem, 'bounds', None)
            if bounds:
                return polynomial_mutation(genome, rate=self.mutation_rate, eta=self.poly_eta, bounds=bounds)
            else:
                return gaussian_mutation(genome, rate=self.mutation_rate, sigma=self.mutation_sigma)
        elif self._genome_type == "permutation":
            # Use swap + inversion mutation
            from ..operators.mutation import swap_mutation, inversion_mutation
            g = swap_mutation(genome, rate=self.mutation_rate)
            g = inversion_mutation(g, rate=self.mutation_rate * 0.5)
            return g
        else:  # binary
            return bit_flip_mutation(genome, rate=self.mutation_rate)

    def evolve_one_generation(self) -> Population:
        """Run one generation of the GA."""
        assert self.population is not None
        # Sort population by fitness
        self.population.sort(maximize=self.maximize)
        new_individuals: List[Individual] = []

        # Elitism: copy top individuals directly
        for i in range(min(self.elite_size, len(self.population))):
            new_individuals.append(self.population[i].clone())

        # Fill rest via selection + crossover + mutation
        while len(new_individuals) < self.population_size:
            parent1 = tournament_selection(self.population, k=self.tournament_k, maximize=self.maximize)
            parent2 = tournament_selection(self.population, k=self.tournament_k, maximize=self.maximize)
            # Crossover
            if random.random() < self.crossover_rate:
                c1_genome, c2_genome = self._crossover(parent1.genome, parent2.genome)
            else:
                c1_genome, c2_genome = list(parent1.genome), list(parent2.genome)
            # Mutation
            c1_genome = self._mutate(c1_genome)
            c2_genome = self._mutate(c2_genome)
            # Repair if needed
            c1_genome = self.problem.repair(c1_genome)
            c2_genome = self.problem.repair(c2_genome)
            new_individuals.append(Individual(c1_genome))
            if len(new_individuals) < self.population_size:
                new_individuals.append(Individual(c2_genome))

        return Population(new_individuals)