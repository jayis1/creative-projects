"""Core data structures: Individual and Population."""

from __future__ import annotations

import random
import copy
from typing import Any, Callable, List, Optional, Sequence, Dict, Tuple
import hashlib
import json


class Individual:
    """A single candidate solution in a population.

    Attributes:
        genome: The genetic material (list, tuple, or other sequence).
        fitness: The objective value (lower is better by default; can be None).
        secondary_fitness: Optional secondary objective for multi-objective problems.
        constraints: Dict of constraint name -> violation value (0 means satisfied).
        metadata: Dict for bookkeeping (age, lineage, etc.).
    """

    __slots__ = ("genome", "fitness", "secondary_fitness", "constraints", "metadata", "_id")

    _next_id = 0

    def __init__(self, genome: Any, fitness: Optional[float] = None):
        self.genome = genome
        self.fitness = fitness
        self.secondary_fitness: Optional[float] = None
        self.constraints: Dict[str, float] = {}
        self.metadata: Dict[str, Any] = {}
        self._id = Individual._next_id
        Individual._next_id += 1

    @property
    def id(self) -> int:
        return self._id

    def clone(self) -> "Individual":
        """Return a deep copy of this individual (new id)."""
        clone = Individual(copy.deepcopy(self.genome), self.fitness)
        clone.secondary_fitness = self.secondary_fitness
        clone.constraints = dict(self.constraints)
        clone.metadata = dict(self.metadata)
        return clone

    def genome_signature(self) -> str:
        """Return a hashable signature of the genome for deduplication."""
        try:
            return hashlib.md5(json.dumps(self.genome, sort_keys=True, default=str).encode()).hexdigest()
        except (TypeError, ValueError):
            return str(self.genome)

    def __repr__(self) -> str:
        fit = f"{self.fitness:.6g}" if isinstance(self.fitness, (int, float)) else str(self.fitness)
        return f"Individual(id={self._id}, fitness={fit}, genome={self.genome!r})"

    def __lt__(self, other: "Individual") -> bool:
        """Compare by fitness; raises if either fitness is None."""
        if self.fitness is None or other.fitness is None:
            raise ValueError("Cannot compare individuals with None fitness")
        return self.fitness < other.fitness

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Individual):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


class Population:
    """A collection of Individual objects with utility methods.

    Args:
        individuals: List of Individual objects.
    """

    def __init__(self, individuals: Optional[List[Individual]] = None):
        self.individuals: List[Individual] = individuals if individuals is not None else []

    def __len__(self) -> int:
        return len(self.individuals)

    def __iter__(self):
        return iter(self.individuals)

    def __getitem__(self, idx) -> Individual:
        return self.individuals[idx]

    def append(self, ind: Individual) -> None:
        self.individuals.append(ind)

    def extend(self, others: Sequence[Individual]) -> None:
        self.individuals.extend(others)

    def best(self, maximize: bool = False) -> Optional[Individual]:
        """Return the individual with the best (min or max) fitness."""
        evaluated = [ind for ind in self.individuals if ind.fitness is not None]
        if not evaluated:
            return None
        return max(evaluated, key=lambda i: i.fitness) if maximize else min(evaluated, key=lambda i: i.fitness)

    def worst(self, maximize: bool = False) -> Optional[Individual]:
        evaluated = [ind for ind in self.individuals if ind.fitness is not None]
        if not evaluated:
            return None
        return min(evaluated, key=lambda i: i.fitness) if maximize else max(evaluated, key=lambda i: i.fitness)

    def average_fitness(self) -> Optional[float]:
        evaluated = [ind.fitness for ind in self.individuals if ind.fitness is not None]
        if not evaluated:
            return None
        return sum(evaluated) / len(evaluated)

    def fitness_std(self) -> Optional[float]:
        import math
        evaluated = [ind.fitness for ind in self.individuals if ind.fitness is not None]
        n = len(evaluated)
        if n < 2:
            return None
        mean = sum(evaluated) / n
        return math.sqrt(sum((f - mean) ** 2 for f in evaluated) / (n - 1))

    def sort(self, maximize: bool = False) -> None:
        """Sort individuals by fitness in-place (ascending by default)."""
        self.individuals.sort(key=lambda i: (i.fitness is None, i.fitness), reverse=maximize)

    def filter_evaluated(self) -> "Population":
        """Return a new Population containing only evaluated individuals."""
        return Population([ind for ind in self.individuals if ind.fitness is not None])

    def unique(self) -> "Population":
        """Return a new Population with duplicate genomes removed (keeps first)."""
        seen = set()
        result = []
        for ind in self.individuals:
            sig = ind.genome_signature()
            if sig not in seen:
                seen.add(sig)
                result.append(ind)
        return Population(result)

    def diversity(self) -> float:
        """Return the fraction of unique genomes in the population (0..1)."""
        if not self.individuals:
            return 0.0
        sigs = {ind.genome_signature() for ind in self.individuals}
        return len(sigs) / len(self.individuals)

    def sample(self, k: int) -> List[Individual]:
        """Return k random individuals (without replacement)."""
        return random.sample(self.individuals, min(k, len(self.individuals)))

    def __repr__(self) -> str:
        return f"Population(size={len(self.individuals)}, best={self.best()})"


def random_population(generator: Callable[[], Any], size: int) -> Population:
    """Create a population by calling *generator* *size* times."""
    if size < 0:
        raise ValueError("Population size must be non-negative")
    return Population([Individual(generator()) for _ in range(size)])