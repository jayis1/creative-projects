"""NSGA-II — Non-dominated Sorting Genetic Algorithm (Deb et al., 2002)."""

from __future__ import annotations

import random
import math
from abc import abstractmethod
from typing import Optional, List, Tuple, Dict, Any
from ..core import Individual, Population
from ..problems.base import Problem, ContinuousProblem
from ..operators.crossover import sbx_crossover
from ..operators.mutation import polynomial_mutation
from .base import BaseAlgorithm


def dominates(objs_a: List[float], objs_b: List[float], maximize: List[bool]) -> bool:
    """Return True if solution A dominates solution B.

    A dominates B iff A is at least as good in all objectives and strictly better in at least one.
    """
    at_least_one_better = False
    for a, b, m in zip(objs_a, objs_b, maximize):
        if m:  # maximize
            if a < b:
                return False
            if a > b:
                at_least_one_better = True
        else:  # minimize
            if a > b:
                return False
            if a < b:
                at_least_one_better = True
    return at_least_one_better


def fast_non_dominated_sort(population: List[Individual], objectives: List[List[float]],
                             maximize: List[bool]) -> List[List[int]]:
    """Perform fast non-dominated sorting. Returns list of fronts (each a list of indices).

    Args:
        population: List of individuals.
        objectives: List of objective vectors (one per individual).
        maximize: List of booleans (one per objective).
    """
    n = len(population)
    domination_count = [0] * n
    dominated_set = [[] for _ in range(n)]
    fronts: List[List[int]] = [[]]

    for i in range(n):
        for j in range(i + 1, n):
            if dominates(objectives[i], objectives[j], maximize):
                dominated_set[i].append(j)
                domination_count[j] += 1
            elif dominates(objectives[j], objectives[i], maximize):
                domination_count[i] += 1
        if domination_count[i] == 0:
            fronts[0].append(i)

    k = 0
    while fronts[k]:
        next_front = []
        for i in fronts[k]:
            for j in dominated_set[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    next_front.append(j)
        k += 1
        if next_front:
            fronts.append(next_front)
        else:
            break
    return fronts


def crowding_distance(objectives: List[List[float]], front: List[int],
                       maximize: List[bool]) -> Dict[int, float]:
    """Compute crowding distance for individuals in a front.

    Args:
        objectives: All objective vectors.
        front: Indices of individuals in the current front.
        maximize: Objective direction flags.
    """
    n = len(front)
    distances = {i: 0.0 for i in front}
    if n <= 2:
        for i in front:
            distances[i] = float('inf')
        return distances
    num_objectives = len(objectives[0])
    for m in range(num_objectives):
        # Sort front by objective m
        sorted_front = sorted(front, key=lambda i: objectives[i][m], reverse=maximize[m])
        # Boundary individuals get infinite distance
        distances[sorted_front[0]] = float('inf')
        distances[sorted_front[-1]] = float('inf')
        obj_min = objectives[sorted_front[0]][m]
        obj_max = objectives[sorted_front[-1]][m]
        denom = obj_max - obj_min if obj_max != obj_min else 1e-12
        for k in range(1, n - 1):
            if distances[sorted_front[k]] == float('inf'):
                continue
            distances[sorted_front[k]] += (objectives[sorted_front[k + 1]][m] - objectives[sorted_front[k - 1]][m]) / denom
    return distances


class MultiObjectiveProblem(Problem):
    """Base class for multi-objective problems.

    Subclasses must implement evaluate_multi(genome) -> List[float] returning multiple objectives.
    """

    def __init__(self, maximize_list: List[bool]):
        super().__init__(maximize=False, constraints=None)
        self.maximize_list = maximize_list

    def evaluate(self, genome) -> float:
        """Single-objective fallback: return sum of objectives (for compatibility)."""
        objs = self.evaluate_multi(genome)
        return sum(o for o, m in zip(objs, self.maximize_list) if not m) - sum(o for o, m in zip(objs, self.maximize_list) if m)

    @abstractmethod
    def evaluate_multi(self, genome) -> List[float]:
        """Return a list of objective values."""
        ...

    def random_genome(self) -> List[float]:
        """Default: random real vector in [-5, 5]. Override as needed."""
        return [random.uniform(-5, 5) for _ in range(2)]


class NSGA2(BaseAlgorithm):
    """NSGA-II multi-objective optimizer.

    Args:
        problem: A MultiObjectiveProblem instance.
        population_size: Population size (default 100).
        max_generations: Max generations.
        crossover_rate: SBX crossover probability (default 0.9).
        mutation_rate: Polynomial mutation rate (default 1/n).
        sbx_eta: SBX distribution index (default 20).
        poly_eta: Polynomial mutation distribution index (default 20).
        seed: Random seed.
        verbose: Print progress.
    """

    def __init__(self, problem: "MultiObjectiveProblem", population_size: int = 100,
                 max_generations: int = 100, crossover_rate: float = 0.9,
                 mutation_rate: Optional[float] = None, sbx_eta: float = 20.0,
                 poly_eta: float = 20.0, seed: Optional[int] = None,
                 verbose: bool = False, callbacks=None):
        super().__init__(problem, population_size, max_generations, maximize=False, seed=seed, verbose=verbose, callbacks=callbacks)
        self.crossover_rate = crossover_rate
        self.sbx_eta = sbx_eta
        self.poly_eta = poly_eta
        n = problem.genome_size() if problem.genome_size() else 2
        self.mutation_rate = mutation_rate if mutation_rate is not None else 1.0 / n
        self.pareto_front: List[Individual] = []
        self._objectives_cache: Dict[int, List[float]] = {}

    def _get_objectives(self, ind: Individual) -> List[float]:
        """Get cached objectives for an individual."""
        if ind.id not in self._objectives_cache:
            self._objectives_cache[ind.id] = self.problem.evaluate_multi(ind.genome)  # type: ignore
        return self._objectives_cache[ind.id]

    def evaluate_population(self, population: Population) -> None:
        """Evaluate individuals and store objectives in metadata."""
        for ind in population.individuals:
            if ind.fitness is None:
                objs = self.problem.evaluate_multi(ind.genome)  # type: ignore
                ind.metadata['objectives'] = objs
                # Use first objective as fitness for sorting compatibility
                ind.fitness = objs[0]
                self._objectives_cache[ind.id] = objs

    def initialize(self) -> Population:
        """Create initial random population."""
        pop = Population()
        for _ in range(self.population_size):
            genome = self.problem.random_genome()
            ind = Individual(genome)
            objs = self.problem.evaluate_multi(genome)  # type: ignore
            ind.metadata['objectives'] = objs
            ind.fitness = objs[0]
            self._objectives_cache[ind.id] = objs
            pop.append(ind)
        return pop

    def evolve_one_generation(self) -> Population:
        """Run one generation of NSGA-II: selection, crossover, mutation, environmental selection."""
        assert self.population is not None
        parents_pop = self.population
        # Get all objectives
        all_objs = [self._get_objectives(ind) for ind in parents_pop.individuals]
        maximize_list = self.problem.maximize_list  # type: ignore

        # Non-dominated sort
        fronts = fast_non_dominated_sort(parents_pop.individuals, all_objs, maximize_list)

        # Compute crowding distances
        for front in fronts:
            crowding = crowding_distance(all_objs, front, maximize_list)
            for idx in front:
                parents_pop.individuals[idx].metadata['crowding'] = crowding[idx]

        # Generate offspring via tournament selection (based on rank + crowding)
        offspring = []
        bounds = getattr(self.problem, 'bounds', None)
        while len(offspring) < self.population_size:
            # Binary tournament: compare by (front rank, -crowding distance)
            p1 = self._tournament(parents_pop, fronts)
            p2 = self._tournament(parents_pop, fronts)
            # SBX crossover
            if random.random() < self.crossover_rate:
                c1, c2 = sbx_crossover(p1.genome, p2.genome, eta=self.sbx_eta, prob=1.0)
            else:
                c1, c2 = list(p1.genome), list(p2.genome)
            # Polynomial mutation
            c1 = polynomial_mutation(c1, rate=self.mutation_rate, eta=self.poly_eta, bounds=bounds)
            c2 = polynomial_mutation(c2, rate=self.mutation_rate, eta=self.poly_eta, bounds=bounds)
            offspring.append(Individual(c1))
            if len(offspring) < self.population_size:
                offspring.append(Individual(c2))

        # Combine parents + offspring
        combined = Population(list(parents_pop.individuals) + offspring)
        # Evaluate new offspring
        for ind in offspring:
            if ind.fitness is None:
                objs = self.problem.evaluate_multi(ind.genome)  # type: ignore
                ind.metadata['objectives'] = objs
                ind.fitness = objs[0]
                self._objectives_cache[ind.id] = objs

        # Environmental selection: non-dominated sort + crowding distance
        combined_objs = [self._get_objectives(ind) for ind in combined.individuals]
        fronts = fast_non_dominated_sort(combined.individuals, combined_objs, maximize_list)
        new_pop = []
        for front in fronts:
            if len(new_pop) + len(front) <= self.population_size:
                new_pop.extend(front)
            else:
                # Sort this front by crowding distance and take the best
                crowding = crowding_distance(combined_objs, front, maximize_list)
                sorted_front = sorted(front, key=lambda i: -crowding[i])
                remaining = self.population_size - len(new_pop)
                new_pop.extend(sorted_front[:remaining])
                break
        # Convert indices to individuals
        selected = [combined.individuals[i] for i in new_pop]
        # Store Pareto front (front 0)
        self.pareto_front = [combined.individuals[i] for i in fronts[0]]
        return Population(selected)

    def _tournament(self, population: Population, fronts: List[List[int]]) -> Individual:
        """Binary tournament selection based on rank and crowding distance."""
        # Pick two random individuals
        i1 = random.randint(0, len(population) - 1)
        i2 = random.randint(0, len(population) - 1)
        while i2 == i1:
            i2 = random.randint(0, len(population) - 1)
        # Determine ranks
        rank1 = rank2 = -1
        for r, front in enumerate(fronts):
            if i1 in front:
                rank1 = r
            if i2 in front:
                rank2 = r
            if rank1 >= 0 and rank2 >= 0:
                break
        if rank1 < rank2:
            return population.individuals[i1]
        elif rank2 < rank1:
            return population.individuals[i2]
        else:
            # Same front: compare crowding distance (higher is better)
            c1 = population.individuals[i1].metadata.get('crowding', 0)
            c2 = population.individuals[i2].metadata.get('crowding', 0)
            if c1 >= c2:
                return population.individuals[i1]
            return population.individuals[i2]