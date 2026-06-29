"""Memetic Algorithm — GA with local search refinement."""

from __future__ import annotations

import random
from typing import Optional, Callable, List
from ..core import Individual, Population
from ..problems.base import Problem, ContinuousProblem
from .ga import GeneticAlgorithm


class MemeticAlgorithm(GeneticAlgorithm):
    """Memetic Algorithm: GA with local search applied to offspring.

    After crossover and mutation, a local search is applied to each offspring
    to refine the solution before evaluation. This combines global exploration (GA)
    with local exploitation (hill climbing).

    Args:
        problem: The optimization problem (must be continuous).
        local_search_rate: Fraction of offspring that receive local search (default 0.1).
        local_search_steps: Number of local search steps per individual (default 10).
        local_search_sigma: Step size for local search perturbations (default 0.01).
        All other GA parameters.
    """

    def __init__(self, problem: ContinuousProblem, population_size: int = 100,
                 max_generations: int = 100, elite_size: int = 1,
                 tournament_k: int = 3, crossover_rate: float = 0.85,
                 mutation_rate: float = 0.1, mutation_sigma: float = 0.2,
                 sbx_eta: float = 15.0, poly_eta: float = 20.0,
                 local_search_rate: float = 0.1, local_search_steps: int = 10,
                 local_search_sigma: float = 0.01,
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size, max_generations, elite_size,
                        tournament_k, crossover_rate, mutation_rate, mutation_sigma,
                        sbx_eta, poly_eta, maximize, seed, verbose, callbacks)
        self.local_search_rate = local_search_rate
        self.local_search_steps = local_search_steps
        self.local_search_sigma = local_search_sigma

    def _local_search(self, genome: List[float]) -> List[float]:
        """Hill-climbing local search: try small perturbations, keep if better."""
        best_genome = list(genome)
        best_fitness, _ = self.problem.evaluate_with_constraints(best_genome)
        for _ in range(self.local_search_steps):
            candidate = [g + random.gauss(0, self.local_search_sigma) for g in best_genome]
            candidate = self.problem.repair(candidate)
            fit, _ = self.problem.evaluate_with_constraints(candidate)
            if self.maximize:
                if fit > best_fitness:
                    best_genome = candidate
                    best_fitness = fit
            else:
                if fit < best_fitness:
                    best_genome = candidate
                    best_fitness = fit
        return best_genome

    def evolve_one_generation(self) -> Population:
        """Run one generation with local search refinement."""
        assert self.population is not None
        self.population.sort(maximize=self.maximize)
        new_individuals: List[Individual] = []

        # Elitism
        for i in range(min(self.elite_size, len(self.population))):
            new_individuals.append(self.population[i].clone())

        while len(new_individuals) < self.population_size:
            parent1 = self._select_parent()
            parent2 = self._select_parent()
            if random.random() < self.crossover_rate:
                c1_genome, c2_genome = self._crossover(parent1.genome, parent2.genome)
            else:
                c1_genome, c2_genome = list(parent1.genome), list(parent2.genome)
            c1_genome = self._mutate(c1_genome)
            c2_genome = self._mutate(c2_genome)
            c1_genome = self.problem.repair(c1_genome)
            c2_genome = self.problem.repair(c2_genome)
            # Local search
            if random.random() < self.local_search_rate:
                c1_genome = self._local_search(c1_genome)
            if random.random() < self.local_search_rate:
                c2_genome = self._local_search(c2_genome)
            new_individuals.append(Individual(c1_genome))
            if len(new_individuals) < self.population_size:
                new_individuals.append(Individual(c2_genome))

        return Population(new_individuals)

    def _select_parent(self):
        """Tournament selection helper."""
        from ..operators.selection import tournament_selection
        return tournament_selection(self.population, k=self.tournament_k, maximize=self.maximize)