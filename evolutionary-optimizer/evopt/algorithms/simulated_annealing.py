"""Simulated Annealing — a classic metaheuristic optimizer.

Simulated Annealing (SA) explores the search space by proposing random moves
and accepting them based on the Metropolis criterion. The "temperature"
controls the acceptance probability of worse solutions: early in the run, the
high temperature allows the algorithm to escape local optima; as the
temperature cools, the search converges toward a local (ideally global) optimum.

This implementation supports:
    - Multiple cooling schedules (geometric, linear, logarithmic).
    - Custom move operators (perturbation functions).
    - Optional restart on stagnation.
    - Works with continuous problems; can be adapted to combinatorial problems
      via a custom move function.

Reference:
    Kirkpatrick, S., Gelatt, C. D., & Vecchi, M. P. (1983).
    "Optimization by Simulated Annealing." Science, 220(4598), 671-680.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Optional, List

from .base import BaseAlgorithm
from ..core import Individual, Population
from ..problems.base import Problem, ContinuousProblem


class SimulatedAnnealing(BaseAlgorithm):
    """Simulated Annealing optimizer.

    Args:
        problem: The optimization problem.
        initial_temperature: Starting temperature T0 (default 1.0).
        final_temperature: Stopping temperature (default 1e-8).
        cooling_schedule: 'geometric', 'linear', or 'logarithmic'.
        cooling_rate: Multiplicative factor for geometric schedule (default 0.95).
        steps_per_temperature: Number of moves attempted at each temperature (default 20).
        move_fn: Optional custom move function ``(genome, temperature) -> new_genome``.
            If None, uses Gaussian perturbation for continuous problems.
        move_sigma: Std for Gaussian move (continuous, default 0.1).
        restart_on_stagnation: If True, reheat the temperature when no improvement
            is seen for ``stagnation_patience`` consecutive temperatures.
        stagnation_patience: Number of temperatures without improvement before reheat.
        reheat_factor: Factor to multiply temperature by on restart (default 0.5).
        max_generations: Maximum number of temperature steps.
        seed: Random seed.
        verbose: Print progress.
        callbacks: List of callback functions.
    """

    SCHEDULES = {"geometric", "linear", "logarithmic"}

    def __init__(self, problem: Problem, initial_temperature: float = 1.0,
                 final_temperature: float = 1e-8,
                 cooling_schedule: str = "geometric",
                 cooling_rate: float = 0.95,
                 steps_per_temperature: int = 20,
                 move_fn: Optional[Callable] = None,
                 move_sigma: float = 0.1,
                 restart_on_stagnation: bool = True,
                 stagnation_patience: int = 50,
                 reheat_factor: float = 0.5,
                 max_generations: int = 500,
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size=1, max_generations=max_generations,
                         maximize=maximize, seed=seed, verbose=verbose, callbacks=callbacks)
        if cooling_schedule not in self.SCHEDULES:
            raise ValueError(f"cooling_schedule must be one of {self.SCHEDULES}")
        if initial_temperature <= 0:
            raise ValueError("initial_temperature must be > 0")
        if not (0 < cooling_rate <= 1):
            raise ValueError("cooling_rate must be in (0, 1]")
        if steps_per_temperature < 1:
            raise ValueError("steps_per_temperature must be >= 1")
        self.initial_temperature = initial_temperature
        self.final_temperature = final_temperature
        self.cooling_schedule = cooling_schedule
        self.cooling_rate = cooling_rate
        self.steps_per_temperature = steps_per_temperature
        self.move_fn = move_fn
        self.move_sigma = move_sigma
        self.restart_on_stagnation = restart_on_stagnation
        self.stagnation_patience = stagnation_patience
        self.reheat_factor = reheat_factor

        self.temperature = initial_temperature
        self.current_genome = None
        self.current_fitness = None
        self._stagnation_count = 0
        self._restarts = 0
        self._acceptance_stats = {"accepted": 0, "rejected": 0, "total": 0}

    def _default_move(self, genome, temperature: float):
        """Default Gaussian perturbation move for continuous problems."""
        result = list(genome)
        bounds = getattr(self.problem, "bounds", None)
        sigma = self.move_sigma * max(temperature, 1e-10)
        for i in range(len(result)):
            result[i] += random.gauss(0, sigma)
            if bounds:
                lo, hi = bounds[i]
                result[i] = max(lo, min(hi, result[i]))
        return result

    def initialize(self) -> Population:
        """Initialize with a single random individual."""
        genome = self.problem.random_genome()
        fitness, violations = self.problem.evaluate_with_constraints(genome)
        self.current_genome = genome
        self.current_fitness = fitness
        self.temperature = self.initial_temperature
        self._stagnation_count = 0
        ind = Individual(genome, fitness=fitness)
        ind.constraints = violations
        return Population([ind])

    def evolve_one_generation(self) -> Population:
        """Run one temperature step: attempt ``steps_per_temperature`` moves."""
        move_fn = self.move_fn or self._default_move
        best_genome = self.current_genome
        best_fitness = self.current_fitness

        for _ in range(self.steps_per_temperature):
            candidate = move_fn(self.current_genome, self.temperature)
            candidate = self.problem.repair(candidate)
            cand_fitness, cand_viol = self.problem.evaluate_with_constraints(candidate)
            self._acceptance_stats["total"] += 1

            delta = cand_fitness - self.current_fitness
            if self.maximize:
                accept = delta > 0 or random.random() < math.exp(min(delta / max(self.temperature, 1e-30), 0))
            else:
                accept = delta < 0 or random.random() < math.exp(min(-delta / max(self.temperature, 1e-30), 0))

            if accept:
                self.current_genome = candidate
                self.current_fitness = cand_fitness
                self._acceptance_stats["accepted"] += 1
                # Track best seen
                if self.maximize:
                    if cand_fitness > best_fitness:
                        best_fitness = cand_fitness
                        best_genome = candidate
                else:
                    if cand_fitness < best_fitness:
                        best_fitness = cand_fitness
                        best_genome = candidate
            else:
                self._acceptance_stats["rejected"] += 1

        # Check stagnation
        if best_fitness == self.current_fitness:
            self._stagnation_count += 1
        else:
            self._stagnation_count = 0

        # Restart (reheat) on stagnation
        if self.restart_on_stagnation and self._stagnation_count >= self.stagnation_patience:
            self.temperature = max(self.temperature * (1.0 / self.reheat_factor),
                                   self.initial_temperature * 0.5)
            self._stagnation_count = 0
            self._restarts += 1
            if self.verbose:
                self.logger.debug(f"Reheating to T={self.temperature:.4f} (restart #{self._restarts})")

        # Cool down
        self._cool_down()

        # Return a single-individual population with the best genome
        ind = Individual(best_genome, fitness=best_fitness)
        return Population([ind])

    def _cool_down(self):
        """Apply the cooling schedule to reduce the temperature."""
        if self.cooling_schedule == "geometric":
            self.temperature *= self.cooling_rate
        elif self.cooling_schedule == "linear":
            step = (self.initial_temperature - self.final_temperature) / max(self.max_generations, 1)
            self.temperature = max(self.initial_temperature - step * self.generation,
                                    self.final_temperature)
        elif self.cooling_schedule == "logarithmic":
            # T_k = T0 / ln(k + 2)
            self.temperature = self.initial_temperature / math.log(self.generation + 2)

    def should_terminate(self) -> bool:
        """Terminate when max_generations reached or temperature is too low."""
        if self.generation >= self.max_generations:
            return True
        if self.temperature <= self.final_temperature:
            self.terminated = True
            self.termination_reason = (
                f"Temperature below threshold: {self.temperature:.2e} <= {self.final_temperature}"
            )
            return True
        return False

    def update_best(self, population: Population) -> None:
        """Update best from the current population (single individual)."""
        if len(population) == 0:
            return
        best = population.individuals[0]
        if best.fitness is None:
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

    @property
    def acceptance_rate(self) -> float:
        """Fraction of proposed moves that were accepted (0..1)."""
        total = self._acceptance_stats["total"]
        if total == 0:
            return 0.0
        return self._acceptance_stats["accepted"] / total