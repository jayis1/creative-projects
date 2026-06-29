"""CMA-ES — Covariance Matrix Adaptation Evolution Strategy.

Implements the canonical (μ/μ_w, λ)-CMA-ES algorithm (Hansen & Ostermeier, 2001).
This is one of the most powerful derivative-free continuous optimizers, especially
effective for ill-conditioned, non-separable, and rugged landscapes.

The implementation follows the standard recipe:

1. Sample λ offspring from N(m, σ²C).
2. Evaluate all offspring and sort by fitness.
3. Update the mean m as the weighted average of the best μ offspring.
4. Update the evolution paths p_σ and p_c using cumulative step-size adaptation.
5. Update the covariance matrix C.
6. Adapt the step size σ.

References:
    Hansen, N. (2016). "The CMA Evolution Strategy: A Tutorial."
    Hansen & Ostermeier (2001). "Completely Derandomized Self-Adaptation
    in Evolution Strategies." Evolutionary Computation, 9(2), 159-195.
"""

from __future__ import annotations

import math
import random
from typing import Optional, List, Tuple

import numpy as np

from .base import BaseAlgorithm
from ..core import Individual, Population
from ..problems.base import ContinuousProblem


class CMAES(BaseAlgorithm):
    """Covariance Matrix Adaptation Evolution Strategy.

    Args:
        problem: A continuous optimization problem (must have ``bounds``).
        sigma0: Initial step size (default: 0.3 of the search range).
        population_size: Number of offspring per generation (λ). If None, defaults to
            ``4 + floor(3 * ln(n))`` where n is the dimensionality.
        max_generations: Maximum number of generations.
        seed: Random seed for reproducibility.
        verbose: If True, print progress per generation.
        callbacks: List of callback functions.

    Note:
        Requires numpy.
    """

    def __init__(self, problem: ContinuousProblem, sigma0: Optional[float] = None,
                 population_size: Optional[int] = None, max_generations: int = 100,
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size=population_size or 0,
                         max_generations=max_generations, maximize=maximize,
                         seed=seed, verbose=verbose, callbacks=callbacks)
        # Seed numpy's RNG alongside Python's random for reproducibility
        if seed is not None:
            np.random.seed(seed)
        self.n = problem.genome_size()
        n = self.n

        # Default λ from the standard recipe
        self.lam = population_size or (4 + int(3 * math.log(n)))
        self.population_size = self.lam

        # μ and recombination weights
        self.mu = self.lam // 2
        weights_raw = [math.log(self.mu + 0.5) - math.log(i + 0.5) for i in range(self.mu)]
        w_sum = sum(weights_raw)
        self.weights = [w / w_sum for w in weights_raw]
        self.mu_eff = 1.0 / sum(w * w for w in self.weights)

        # Step size
        bounds = getattr(problem, "bounds", None)
        if bounds and sigma0 is None:
            range_per_dim = [hi - lo for lo, hi in bounds]
            sigma0 = 0.3 * sum(range_per_dim) / n
        self.sigma = sigma0 or 0.3

        # Cumulation parameters
        self.cc = (4 + self.mu_eff / n) / (n + 4 + 2 * self.mu_eff / n)
        self.cs = (self.mu_eff + 2) / (n + self.mu_eff + 5)
        self.c1 = 2.0 / ((n + 1.3) ** 2 + self.mu_eff)
        self.cmu = min(1 - self.c1, 2 * (self.mu_eff - 2 + 1 / self.mu_eff) /
                       ((n + 2) ** 2 + self.mu_eff))
        self.damps = 1 + 2 * max(0, math.sqrt((self.mu_eff - 1) / (n + 1)) - 1) + self.cs

        # Expectation of ||N(0,I)||  — used in p_σ update
        self.chiN = math.sqrt(n) * (1 - 1.0 / (4 * n) + 1.0 / (21 * n ** 2))

        # State
        self.mean = np.zeros(n)
        self.C = np.eye(n)
        self.B = np.eye(n)
        self.D = np.ones(n)
        self.pc = np.zeros(n)
        self.ps = np.zeros(n)
        self._initialized = False
        self.eigen_decomposition_valid = True

    def initialize(self) -> Population:
        """Initialize the distribution mean at a random point within bounds."""
        bounds = getattr(self.problem, "bounds", None)
        if bounds:
            lo = np.array([b[0] for b in bounds])
            hi = np.array([b[1] for b in bounds])
            self.mean = np.random.uniform(lo, hi)
        else:
            self.mean = np.zeros(self.n)
        self._initialized = True
        # Create initial population (will be evaluated by base class)
        pop = Population()
        for _ in range(self.lam):
            genome = self._sample_offspring()
            pop.append(Individual(list(genome)))
        return pop

    def _ensure_eigen_decomposition(self):
        """Recompute B and D from C if the covariance has been updated."""
        if self.eigen_decomposition_valid:
            return
        # Symmetrize C for numerical stability
        self.C = (self.C + self.C.T) / 2
        eigenvalues, B = np.linalg.eigh(self.C)
        # Guard against tiny negative eigenvalues from numerical error
        eigenvalues = np.maximum(eigenvalues, 1e-20)
        self.D = np.sqrt(eigenvalues)
        self.B = B
        self.eigen_decomposition_valid = True

    def _sample_offspring(self) -> np.ndarray:
        """Sample one offspring from N(mean, σ²C). Returns the genome vector."""
        self._ensure_eigen_decomposition()
        z = np.random.standard_normal(self.n)
        return self.mean + self.sigma * (self.B @ (self.D * z))

    def _evaluate(self, genome: List[float]) -> Tuple[float, dict]:
        """Evaluate a genome with constraints. Returns (fitness, violations)."""
        return self.problem.evaluate_with_constraints(genome)

    def evolve_one_generation(self) -> Population:
        """Run one CMA-ES generation: sample, evaluate, update distribution."""
        assert self.population is not None
        n = self.n

        # Sample λ offspring and evaluate them
        offspring_genomes: List[np.ndarray] = []
        fitnesses: List[float] = []
        violations_list: List[dict] = []
        pop = Population()

        for _ in range(self.lam):
            genome = self._sample_offspring()
            genome_list = list(genome)
            # Clip to bounds
            bounds = getattr(self.problem, "bounds", None)
            if bounds:
                genome_list = [
                    max(bounds[i][0], min(bounds[i][1], genome_list[i]))
                    for i in range(n)
                ]
                genome = np.array(genome_list)
            fit, viol = self._evaluate(genome_list)
            ind = Individual(genome_list, fitness=fit)
            ind.constraints = viol
            pop.append(ind)
            offspring_genomes.append(genome)
            fitnesses.append(fit)
            violations_list.append(viol)

        # Sort by fitness (minimize by default; handle maximize by sorting reversed)
        if self.maximize:
            sorted_indices = sorted(range(self.lam), key=lambda i: -fitnesses[i])
        else:
            sorted_indices = sorted(range(self.lam), key=lambda i: fitnesses[i])

        # Update mean
        old_mean = self.mean.copy()
        top_genomes = [offspring_genomes[sorted_indices[i]] for i in range(self.mu)]
        weighted_sum = sum(w * g for w, g in zip(self.weights, top_genomes))
        self.mean = weighted_sum

        # Compute y_k = (x_k - old_mean) / σ  for the top-μ individuals
        y = [(offspring_genomes[sorted_indices[i]] - old_mean) / self.sigma
             for i in range(self.mu)]

        # Update evolution path p_σ
        self._ensure_eigen_decomposition()
        C_inv_sqrt = self.B @ np.diag(1.0 / self.D) @ self.B.T
        ps = (1 - self.cs) * self.ps + math.sqrt(self.cs * (2 - self.cs) * self.mu_eff) * \
             (C_inv_sqrt @ (self.mean - old_mean) / self.sigma)
        self.ps = ps

        # Update evolution path p_c
        h_sigma = float(np.linalg.norm(self.ps) / math.sqrt(1 - (1 - self.cs) ** (2 * (self.generation + 1)))) \
            < (1.4 + 2 / (n + 1)) * self.chiN
        self.pc = (1 - self.cc) * self.pc + h_sigma * \
                  math.sqrt(self.cc * (2 - self.cc) * self.mu_eff) * (self.mean - old_mean) / self.sigma

        # Update covariance matrix C
        rank_one = np.outer(self.pc, self.pc)
        rank_mu = sum(w * np.outer(yi, yi) for w, yi in zip(self.weights, y))
        self.C = (1 - self.c1 - self.cmu) * self.C + self.c1 * rank_one + \
                 self.cmu * rank_mu
        # Add small noise on diagonal for numerical stability
        self.C += np.eye(n) * (1e-20 * self.c1)
        self.eigen_decomposition_valid = False

        # Update step size σ
        self.sigma *= math.exp((self.cs / self.damps) *
                               (np.linalg.norm(self.ps) / self.chiN - 1))
        # Prevent σ from becoming too small or too large
        self.sigma = max(self.sigma, 1e-30)
        if bounds:
            max_range = max(hi - lo for lo, hi in bounds)
            self.sigma = min(self.sigma, max_range * 10)

        # update_best needs the population sorted appropriately
        return pop

    def update_best(self, population: Population) -> None:
        """Update best individual from the current population."""
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