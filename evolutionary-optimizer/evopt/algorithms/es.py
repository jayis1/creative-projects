"""Evolution Strategy (ES) with self-adaptive mutation strengths (µ,λ)-ES and (µ+λ)-ES."""

from __future__ import annotations

import random
import math
from typing import Optional, List
from ..core import Individual, Population
from ..problems.base import Problem, ContinuousProblem
from .base import BaseAlgorithm


class EvolutionStrategy(BaseAlgorithm):
    """(µ,λ)-ES or (µ+λ)-ES with self-adaptive step sizes.

    Each individual carries strategy parameters (step sizes) alongside the genome:
        genome = [x1, x2, ..., xn, sigma1, sigma2, ..., sigman]

    Uses the standard log-normal update rule for step sizes:
        sigma_i' = sigma_i * exp(tau' * N(0,1) + tau * N_i(0,1))

    Args:
        problem: Continuous problem to optimize.
        mu: Number of parents.
        lam: Number of offspring per generation.
        plus_strategy: If True, use (µ+λ) (parents + offspring compete); else (µ,λ).
        tau: Global learning rate (default 1/sqrt(2*n)).
        tau_prime: Individual learning rate (default 1/sqrt(2*sqrt(n))).
        initial_sigma: Initial step size (default 1.0).
        min_sigma: Minimum step size to prevent premature convergence (default 1e-8).
        maximize: Override maximize.
        seed: Random seed.
        verbose: Print progress.
    """

    def __init__(self, problem: ContinuousProblem, mu: int = 30, lam: int = 200,
                 plus_strategy: bool = True, tau: Optional[float] = None,
                 tau_prime: Optional[float] = None, initial_sigma: float = 1.0,
                 min_sigma: float = 1e-8, max_generations: int = 100,
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size=mu, max_generations=max_generations,
                         maximize=maximize, seed=seed, verbose=verbose, callbacks=callbacks)
        self.mu = mu
        self.lam = lam
        self.plus_strategy = plus_strategy
        self.initial_sigma = initial_sigma
        self.min_sigma = min_sigma
        n = problem.genome_size()
        self.n = n
        self.tau = tau if tau is not None else 1.0 / math.sqrt(2 * n)
        self.tau_prime = tau_prime if tau_prime is not None else 1.0 / math.sqrt(2 * math.sqrt(n))

    def initialize(self) -> Population:
        """Create µ parents with random genomes and initial step sizes."""
        pop = Population()
        for _ in range(self.mu):
            genome = self.problem.random_genome()
            sigmas = [self.initial_sigma] * self.n
            full_genome = genome + sigmas
            pop.append(Individual(full_genome))
        return pop

    def _extract(self, individual: Individual):
        """Split genome into solution vector and strategy parameters."""
        half = len(individual.genome) // 2
        return individual.genome[:half], individual.genome[half:]

    def _mutate(self, individual: Individual) -> Individual:
        """Apply self-adaptive mutation: update sigmas first, then perturb solution."""
        solution, sigmas = self._extract(individual)
        global_noise = random.gauss(0, 1)
        new_sigmas = []
        new_solution = []
        bounds = getattr(self.problem, 'bounds', None)
        for i in range(len(solution)):
            sigma = sigmas[i] * math.exp(self.tau_prime * global_noise + self.tau * random.gauss(0, 1))
            sigma = max(sigma, self.min_sigma)
            new_sigmas.append(sigma)
            x = solution[i] + sigma * random.gauss(0, 1)
            if bounds:
                lo, hi = bounds[i]
                x = max(lo, min(hi, x))
            new_solution.append(x)
        return Individual(new_solution + new_sigmas)

    def evolve_one_generation(self) -> Population:
        """Generate λ offspring from µ parents and select the best."""
        assert self.population is not None
        self.population.sort(maximize=self.maximize)
        parents = self.population.individuals[:self.mu]
        offspring = []
        for _ in range(self.lam):
            parent = random.choice(parents)
            child = self._mutate(parent)
            offspring.append(child)
        offspring_pop = Population(offspring)
        if self.plus_strategy:
            # (µ+λ): combine parents and offspring, select best µ
            combined = Population(parents + offspring)
            combined.sort(maximize=self.maximize)
            return Population(combined.individuals[:self.mu])
        else:
            # (µ,λ): select best µ from offspring only
            offspring_pop.sort(maximize=self.maximize)
            return Population(offspring_pop.individuals[:self.mu])