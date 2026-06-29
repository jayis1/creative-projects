"""Island Model Genetic Algorithm — parallel subpopulations with migration."""

from __future__ import annotations

import random
from typing import Optional, List, Callable
from ..core import Individual, Population
from ..problems.base import Problem
from .ga import GeneticAlgorithm
from .base import BaseAlgorithm


class IslandModelGA(BaseAlgorithm):
    """Island Model GA: multiple subpopulations evolving in parallel with periodic migration.

    Each island runs an independent GA. Every *migration_interval* generations,
    the best individuals from each island migrate to a randomly chosen neighbor island.

    Args:
        problem: The optimization problem.
        num_islands: Number of islands (subpopulations).
        island_size: Individuals per island.
        max_generations: Total generations per island.
        migration_interval: Generations between migrations.
        migration_rate: Fraction of each island's best individuals that migrate.
        topology: Migration topology — 'ring', 'random', or 'fully_connected'.
        elite_size: Elites per island.
        tournament_k: Tournament size.
        crossover_rate: Crossover probability.
        mutation_rate: Mutation probability.
        seed: Random seed.
        verbose: Print progress.
    """

    TOPOLOGIES = {'ring', 'random', 'fully_connected'}

    def __init__(self, problem: Problem, num_islands: int = 4, island_size: int = 25,
                 max_generations: int = 100, migration_interval: int = 10,
                 migration_rate: float = 0.1, topology: str = 'ring',
                 elite_size: int = 1, tournament_k: int = 3,
                 crossover_rate: float = 0.85, mutation_rate: float = 0.1,
                 maximize: Optional[bool] = None, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size=num_islands * island_size,
                         max_generations=max_generations, maximize=maximize,
                         seed=seed, verbose=verbose, callbacks=callbacks)
        if topology not in self.TOPOLOGIES:
            raise ValueError(f"topology must be one of {self.TOPOLOGIES}")
        self.num_islands = num_islands
        self.island_size = island_size
        self.migration_interval = migration_interval
        self.migration_rate = migration_rate
        self.topology = topology
        self.elite_size = elite_size
        self.tournament_k = tournament_k
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.islands: List[GeneticAlgorithm] = []
        self._build_topology()

    def _build_topology(self):
        """Build the migration topology (adjacency list)."""
        self.neighbors: List[List[int]] = [[] for _ in range(self.num_islands)]
        if self.topology == 'ring':
            for i in range(self.num_islands):
                self.neighbors[i] = [(i + 1) % self.num_islands]
        elif self.topology == 'fully_connected':
            for i in range(self.num_islands):
                self.neighbors[i] = [j for j in range(self.num_islands) if j != i]
        # 'random' topology: neighbors assigned at migration time

    def _get_migration_target(self, source: int) -> int:
        """Get a migration target island for the given source island."""
        if self.topology == 'random':
            targets = [j for j in range(self.num_islands) if j != source]
            return random.choice(targets) if targets else source
        elif self.neighbors[source]:
            return random.choice(self.neighbors[source])
        return source

    def initialize(self) -> Population:
        """Initialize all islands with independent random populations."""
        all_individuals = []
        self.islands = []
        for i in range(self.num_islands):
            island = GeneticAlgorithm(
                self.problem, population_size=self.island_size,
                max_generations=0,  # We control the loop
                elite_size=self.elite_size, tournament_k=self.tournament_k,
                crossover_rate=self.crossover_rate, mutation_rate=self.mutation_rate,
                maximize=self.maximize, seed=None, verbose=False
            )
            island_pop = island.initialize()
            island.evaluate_population(island_pop)
            island.population = island_pop
            island.update_best(island_pop)
            island.record_statistics()
            self.islands.append(island)
            all_individuals.extend(island_pop.individuals)
        return Population(all_individuals)

    def evolve_one_generation(self) -> Population:
        """Evolve each island one generation, then perform migration if needed."""
        all_individuals = []
        for island in self.islands:
            island.generation += 1
            new_pop = island.evolve_one_generation()
            island.evaluate_population(new_pop)
            island.population = new_pop
            island.update_best(new_pop)
            island.record_statistics()
            all_individuals.extend(new_pop.individuals)

        # Migration
        if self.generation > 0 and self.generation % self.migration_interval == 0:
            self._migrate()
            # Rebuild all_individuals after migration
            all_individuals = []
            for island in self.islands:
                all_individuals.extend(island.population.individuals)
            if self.verbose:
                self.logger.debug(f"Migration at generation {self.generation}")

        return Population(all_individuals)

    def _migrate(self):
        """Migrate best individuals between islands."""
        num_migrants = max(1, int(self.island_size * self.migration_rate))
        migrants_out = {}  # target_island -> list of individuals

        for i, island in enumerate(self.islands):
            island.population.sort(maximize=self.maximize)
            # Take best individuals as migrants
            migrants = [island.population.individuals[j].clone()
                        for j in range(min(num_migrants, len(island.population)))]
            target = self._get_migration_target(i)
            if target not in migrants_out:
                migrants_out[target] = []
            migrants_out[target].extend(migrants)

        # Add migrants to target islands, replacing worst individuals
        for target_idx, migrants in migrants_out.items():
            island = self.islands[target_idx]
            island.population.sort(maximize=self.maximize)
            # Replace worst individuals with migrants
            for j, migrant in enumerate(migrants):
                replace_idx = len(island.population) - 1 - j
                if replace_idx >= 0:
                    island.population.individuals[replace_idx] = migrant

    def update_best(self, population: Population) -> None:
        """Update the global best from all islands."""
        for island in self.islands:
            if island.best_individual is None:
                continue
            if self.best_individual is None:
                self.best_individual = island.best_individual.clone()
            else:
                if self.maximize:
                    if island.best_individual.fitness > self.best_individual.fitness:
                        self.best_individual = island.best_individual.clone()
                else:
                    if island.best_individual.fitness < self.best_individual.fitness:
                        self.best_individual = island.best_individual.clone()