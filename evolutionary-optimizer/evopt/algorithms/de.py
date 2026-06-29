"""Differential Evolution (DE) — Storn & Price's classic algorithm."""

from __future__ import annotations

import random
from typing import Optional, List
from ..core import Individual, Population
from ..problems.base import Problem, ContinuousProblem
from .base import BaseAlgorithm


class DifferentialEvolution(BaseAlgorithm):
    """Differential Evolution with multiple mutation strategies.

    Supports strategies: 'rand/1', 'best/1', 'rand/2', 'best/2', 'current-to-best/1'.
    Uses binomial crossover by default; exponential crossover is also available.

    Args:
        problem: Continuous problem.
        population_size: Population size (default 50; should be >= 4).
        max_generations: Max generations.
        F: Scale factor for differential mutation (default 0.8).
        CR: Crossover rate (default 0.9).
        strategy: Mutation strategy (default 'rand/1').
        crossover_type: 'binomial' or 'exponential' (default 'binomial').
        maximize: Override.
        seed: Random seed.
        verbose: Print progress.
    """

    STRATEGIES = {'rand/1', 'best/1', 'rand/2', 'best/2', 'current-to-best/1'}

    def __init__(self, problem: ContinuousProblem, population_size: int = 50,
                 max_generations: int = 100, F: float = 0.8, CR: float = 0.9,
                 strategy: str = 'rand/1', crossover_type: str = 'binomial',
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size, max_generations, maximize, seed, verbose, callbacks)
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Invalid strategy '{strategy}'. Must be one of {self.STRATEGIES}")
        if crossover_type not in ('binomial', 'exponential'):
            raise ValueError("crossover_type must be 'binomial' or 'exponential'")
        if population_size < 4:
            raise ValueError("Population size must be >= 4 for DE")
        if not (0.0 <= F <= 2.0):
            raise ValueError("F must be in [0, 2]")
        if not (0.0 <= CR <= 1.0):
            raise ValueError("CR must be in [0, 1]")
        self.F = F
        self.CR = CR
        self.strategy = strategy
        self.crossover_type = crossover_type

    def initialize(self) -> Population:
        """Create the initial random population."""
        return Population([Individual(self.problem.random_genome()) for _ in range(self.population_size)])

    def _mutate_de(self, population: List[Individual], target_idx: int) -> List[float]:
        """Generate a mutant vector using the selected strategy."""
        pop_genomes = [ind.genome for ind in population]
        n = len(pop_genomes[0])
        bounds = getattr(self.problem, 'bounds', None)
        pop_size = len(pop_genomes)

        def pick_distinct(exclude_set: set, count: int) -> List[int]:
            """Pick *count* distinct indices not in *exclude_set*."""
            available = [i for i in range(pop_size) if i not in exclude_set]
            if len(available) < count:
                # Fallback: allow repeats if population too small
                return [random.choice(available) for _ in range(count)] if available else [0] * count
            return random.sample(available, count)

        # Find the best genome using already-computed fitness values (no re-evaluation)
        if self.strategy in ('best/1', 'best/2', 'current-to-best/1'):
            evaluated = [(i, ind.fitness) for i, ind in enumerate(population) if ind.fitness is not None]
            if evaluated:
                if self.maximize:
                    best_idx = max(evaluated, key=lambda x: x[1])[0]
                else:
                    best_idx = min(evaluated, key=lambda x: x[1])[0]
                best = pop_genomes[best_idx]
            else:
                best = pop_genomes[0]

        if self.strategy == 'rand/1':
            r1, r2, r3 = pick_distinct({target_idx}, 3)
            mutant = [pop_genomes[r1][i] + self.F * (pop_genomes[r2][i] - pop_genomes[r3][i]) for i in range(n)]
        elif self.strategy == 'best/1':
            r1, r2 = pick_distinct({target_idx}, 2)
            mutant = [best[i] + self.F * (pop_genomes[r1][i] - pop_genomes[r2][i]) for i in range(n)]
        elif self.strategy == 'rand/2':
            r1, r2, r3, r4, r5 = pick_distinct({target_idx}, 5)
            mutant = [pop_genomes[r1][i] + self.F * (pop_genomes[r2][i] - pop_genomes[r3][i])
                      + self.F * (pop_genomes[r4][i] - pop_genomes[r5][i]) for i in range(n)]
        elif self.strategy == 'best/2':
            r1, r2, r3, r4 = pick_distinct({target_idx}, 4)
            mutant = [best[i] + self.F * (pop_genomes[r1][i] - pop_genomes[r2][i])
                      + self.F * (pop_genomes[r3][i] - pop_genomes[r4][i]) for i in range(n)]
        elif self.strategy == 'current-to-best/1':
            r1, r2 = pick_distinct({target_idx}, 2)
            target = pop_genomes[target_idx]
            mutant = [target[i] + self.F * (best[i] - target[i]) + self.F * (pop_genomes[r1][i] - pop_genomes[r2][i])
                      for i in range(n)]
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        # Clip to bounds
        if bounds:
            mutant = [max(bounds[i][0], min(bounds[i][1], mutant[i])) for i in range(n)]
        return mutant

    def _crossover_de(self, target: List[float], mutant: List[float]) -> List[float]:
        """Binomial or exponential crossover between target and mutant."""
        n = len(target)
        if self.crossover_type == 'binomial':
            trial = list(target)
            j_rand = random.randint(0, n - 1)
            for i in range(n):
                if random.random() <= self.CR or i == j_rand:
                    trial[i] = mutant[i]
        else:  # exponential
            trial = list(target)
            start = random.randint(0, n - 1)
            i = start
            while True:
                trial[i] = mutant[i]
                i = (i + 1) % n
                if random.random() > self.CR or i == start:
                    break
        return trial

    def evolve_one_generation(self) -> Population:
        """Generate the next population via DE mutation-crossover-selection."""
        assert self.population is not None
        pop_list = list(self.population.individuals)
        new_individuals = []
        for i, target in enumerate(pop_list):
            mutant_genome = self._mutate_de(pop_list, i)
            trial_genome = self._crossover_de(target.genome, mutant_genome)
            trial_genome = self.problem.repair(trial_genome)
            trial = Individual(trial_genome)
            # Evaluate trial
            fitness, violations = self.problem.evaluate_with_constraints(trial_genome)
            trial.fitness = fitness
            trial.constraints = violations
            # Selection: keep trial if better than or equal to target
            if self.maximize:
                if trial.fitness >= target.fitness:
                    new_individuals.append(trial)
                else:
                    new_individuals.append(target.clone())
            else:
                if trial.fitness <= target.fitness:
                    new_individuals.append(trial)
                else:
                    new_individuals.append(target.clone())
        return Population(new_individuals)