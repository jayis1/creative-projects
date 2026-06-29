"""Particle Swarm Optimization (PSO) — Kennedy & Eberhart."""

from __future__ import annotations

import random
import math
from typing import Optional, List, Dict, Any
from ..core import Individual, Population
from ..problems.base import Problem, ContinuousProblem
from .base import BaseAlgorithm


class Particle:
    """A PSO particle with position, velocity, and personal best."""

    __slots__ = ("position", "velocity", "best_position", "best_fitness", "fitness")

    def __init__(self, position: List[float], velocity: List[float]):
        self.position = position
        self.velocity = velocity
        self.best_position = list(position)
        self.best_fitness: Optional[float] = None
        self.fitness: Optional[float] = None


class ParticleSwarmOptimizer(BaseAlgorithm):
    """Standard Particle Swarm Optimization with inertia weight.

    Velocity update: v = w*v + c1*r1*(pbest - x) + c2*r2*(gbest - x)
    Position update: x = x + v

    Args:
        problem: Continuous problem.
        swarm_size: Number of particles (default 30).
        max_generations: Max iterations.
        inertia: Inertia weight w (default 0.7298).
        cognitive: Cognitive coefficient c1 (default 1.49618).
        social: Social coefficient c2 (default 1.49618).
        max_velocity: Maximum velocity as fraction of search range (default 0.2).
        clamp_velocity: If True, clamp velocity to max_velocity * range.
        maximize: Override.
        seed: Random seed.
        verbose: Print progress.
    """

    def __init__(self, problem: ContinuousProblem, swarm_size: int = 30,
                 max_generations: int = 100, inertia: float = 0.7298,
                 cognitive: float = 1.49618, social: float = 1.49618,
                 max_velocity: float = 0.2, clamp_velocity: bool = True,
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size=swarm_size, max_generations=max_generations,
                         maximize=maximize, seed=seed, verbose=verbose, callbacks=callbacks)
        self.swarm_size = swarm_size
        self.inertia = inertia
        self.cognitive = cognitive
        self.social = social
        self.max_velocity_frac = max_velocity
        self.clamp_velocity = clamp_velocity
        self.particles: List[Particle] = []
        self.global_best_position: Optional[List[float]] = None
        self.global_best_fitness: Optional[float] = None
        # Precompute max velocity per dimension
        bounds = getattr(problem, 'bounds', None)
        if bounds:
            self.max_velocities = [(bounds[i][1] - bounds[i][0]) * max_velocity for i in range(len(bounds))]
        else:
            self.max_velocities = [max_velocity] * problem.genome_size()

    def initialize(self) -> Population:
        """Initialize the swarm with random positions and velocities."""
        bounds = getattr(self.problem, 'bounds', None)
        pop = Population()
        self.particles = []
        for _ in range(self.swarm_size):
            position = self.problem.random_genome()
            if bounds:
                velocity = [random.uniform(-self.max_velocities[i], self.max_velocities[i])
                           for i in range(len(position))]
            else:
                velocity = [random.uniform(-1, 1) for _ in position]
            particle = Particle(position, velocity)
            self.particles.append(particle)
            ind = Individual(position)
            pop.append(ind)
        return pop

    def evaluate_population(self, population: Population) -> None:
        """Evaluate particles and update personal/global bests."""
        for particle, ind in zip(self.particles, population.individuals):
            if ind.fitness is None:
                fitness, violations = self.problem.evaluate_with_constraints(ind.genome)
                ind.fitness = fitness
                ind.constraints = violations
            particle.fitness = ind.fitness
            # Update personal best
            if particle.best_fitness is None:
                particle.best_fitness = particle.fitness
                particle.best_position = list(particle.position)
            elif self.maximize:
                if particle.fitness > particle.best_fitness:
                    particle.best_fitness = particle.fitness
                    particle.best_position = list(particle.position)
            else:
                if particle.fitness < particle.best_fitness:
                    particle.best_fitness = particle.fitness
                    particle.best_position = list(particle.position)
            # Update global best
            if self.global_best_fitness is None:
                self.global_best_fitness = particle.best_fitness
                self.global_best_position = list(particle.best_position)
            elif self.maximize:
                if particle.best_fitness > self.global_best_fitness:
                    self.global_best_fitness = particle.best_fitness
                    self.global_best_position = list(particle.best_position)
            else:
                if particle.best_fitness < self.global_best_fitness:
                    self.global_best_fitness = particle.best_fitness
                    self.global_best_position = list(particle.best_position)

    def evolve_one_generation(self) -> Population:
        """Update particle velocities and positions."""
        assert self.population is not None
        bounds = getattr(self.problem, 'bounds', None)
        new_pop = Population()
        for i, particle in enumerate(self.particles):
            n = len(particle.position)
            new_velocity = []
            for d in range(n):
                r1 = random.random()
                r2 = random.random()
                v = (self.inertia * particle.velocity[d]
                     + self.cognitive * r1 * (particle.best_position[d] - particle.position[d])
                     + self.social * r2 * (self.global_best_position[d] - particle.position[d]))
                if self.clamp_velocity:
                    v = max(-self.max_velocities[d], min(self.max_velocities[d], v))
                new_velocity.append(v)
            particle.velocity = new_velocity
            # Update position
            particle.position = [particle.position[d] + new_velocity[d] for d in range(n)]
            # Clip to bounds
            if bounds:
                particle.position = [max(bounds[d][0], min(bounds[d][1], particle.position[d]))
                                      for d in range(n)]
            new_pop.append(Individual(particle.position))
        return new_pop

    def update_best(self, population: Population) -> None:
        """Sync the algorithm's best_individual with the global best."""
        if self.global_best_fitness is None:
            return
        if self.best_individual is None:
            self.best_individual = Individual(list(self.global_best_position), self.global_best_fitness)
        else:
            if self.maximize:
                if self.global_best_fitness > self.best_individual.fitness:
                    self.best_individual = Individual(list(self.global_best_position), self.global_best_fitness)
            else:
                if self.global_best_fitness < self.best_individual.fitness:
                    self.best_individual = Individual(list(self.global_best_position), self.global_best_fitness)