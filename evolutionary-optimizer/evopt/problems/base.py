"""Problem definitions for evolutionary optimization."""

from __future__ import annotations

import random
import math
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Sequence, Optional, Callable


class Problem(ABC):
    """Base class for optimization problems.

    Subclasses must implement:
        - evaluate(genome) -> float (the objective to minimize/maximize)
        - random_genome() -> Any (a random initial solution)
        - genome_size() -> int (dimensionality, if applicable)

    Attributes:
        maximize: If True, higher fitness is better; if False (default), lower is better.
        constraints: List of constraint functions, each returning a violation value (0 = satisfied).
    """

    def __init__(self, maximize: bool = False, constraints: Optional[List[Callable]] = None):
        self.maximize = maximize
        self.constraints = constraints or []

    @abstractmethod
    def evaluate(self, genome: Any) -> float:
        """Evaluate a genome and return a scalar fitness."""
        ...

    @abstractmethod
    def random_genome(self) -> Any:
        """Generate a random genome."""
        ...

    def genome_size(self) -> int:
        """Return the dimensionality of the genome (default: 0)."""
        return 0

    def evaluate_with_constraints(self, genome: Any) -> Tuple[float, dict]:
        """Evaluate the genome and compute constraint violations.

        Returns (fitness, constraint_dict).
        If any constraint is violated, the fitness is penalized.
        """
        raw = self.evaluate(genome)
        violations = {}
        total_violation = 0.0
        for i, c in enumerate(self.constraints):
            v = c(genome)
            if v > 0:
                violations[f"c{i}"] = v
                total_violation += v
        if total_violation > 0:
            # Penalty: add large constant + violation to push infeasible solutions away
            if not self.maximize:
                raw = raw + 1e6 + total_violation * 100
            else:
                raw = raw - 1e6 - total_violation * 100
        return raw, violations

    def is_feasible(self, genome: Any) -> bool:
        """Check if genome satisfies all constraints."""
        return all(c(genome) <= 0 for c in self.constraints)

    def repair(self, genome: Any) -> Any:
        """Repair an infeasible genome. Default: return unchanged."""
        return genome


class ContinuousProblem(Problem):
    """Base class for continuous optimization problems over a hyperbox.

    Args:
        dims: Number of dimensions.
        bounds: (low, high) for each dimension, or a single (low, high) tuple applied to all dims.
        maximize: Whether to maximize.
    """

    def __init__(self, dims: int = 2, bounds: Tuple[float, float] = (-5.0, 5.0), maximize: bool = False, constraints=None):
        super().__init__(maximize=maximize, constraints=constraints)
        if dims < 1:
            raise ValueError("dims must be >= 1")
        self.dims = dims
        if isinstance(bounds, tuple) and len(bounds) == 2 and not isinstance(bounds[0], (list, tuple)):
            self.bounds = [bounds] * dims  # type: ignore
        elif isinstance(bounds, (list, tuple)) and len(bounds) == dims:
            self.bounds = list(bounds)
        else:
            raise ValueError(f"bounds must be (low, high) or a list of {dims} such tuples")

    def random_genome(self) -> List[float]:
        """Generate a random genome within bounds."""
        return [random.uniform(lo, hi) for lo, hi in self.bounds]

    def genome_size(self) -> int:
        return self.dims

    def repair(self, genome: Sequence[float]) -> List[float]:
        """Clip genome values to bounds."""
        return [max(lo, min(hi, x)) for x, (lo, hi) in zip(genome, self.bounds)]


class CombinatorialProblem(Problem):
    """Base class for combinatorial problems (permutations, subsets, etc.)."""

    def __init__(self, maximize: bool = False, constraints=None):
        super().__init__(maximize=maximize, constraints=constraints)