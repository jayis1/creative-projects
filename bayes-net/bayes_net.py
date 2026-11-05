"""Exact inference for small discrete Bayesian networks (stdlib only)."""
from __future__ import annotations

from itertools import product
from math import isfinite


class BayesNet:
    """A binary-variable DAG represented by conditional probability tables."""

    def __init__(self):
        self.parents: dict[str, tuple[str, ...]] = {}
        self.tables: dict[str, dict[tuple[bool, ...], float]] = {}

    def add_node(self, name: str, parents: list[str], table: dict[tuple[bool, ...], float]) -> None:
        if not isinstance(name, str) or not name or name in self.parents:
            raise ValueError("node name must be a unique non-empty string")
        if len(set(parents)) != len(parents) or name in parents:
            raise ValueError("parents must be unique and cannot include the node")
        if any(parent not in self.parents for parent in parents):
            raise ValueError("parents must be added before their child")
        expected = set(product((False, True), repeat=len(parents)))
        if set(table) != expected:
            raise ValueError(f"table must contain exactly {len(expected)} parent assignments")
        cleaned = {}
        for assignment, p in table.items():
            if not isinstance(p, (int, float)) or isinstance(p, bool) or not isfinite(p) or not 0 <= p <= 1:
                raise ValueError("probabilities must be finite numbers in [0, 1]")
            cleaned[tuple(assignment)] = float(p)
        self.parents[name] = tuple(parents)
        self.tables[name] = cleaned

    def _validate_assignment(self, assignment: dict[str, bool], *, partial: bool = True) -> None:
        if not isinstance(assignment, dict):
            raise ValueError("assignments must be dictionaries")
        for name, value in assignment.items():
            if name not in self.parents:
                raise ValueError(f"unknown variable: {name}")
            if type(value) is not bool:
                raise ValueError(f"{name} must be assigned a boolean")

    def _joint(self, assignment: dict[str, bool]) -> float:
        weight = 1.0
        for name, parents in self.parents.items():
            p_true = self.tables[name][tuple(assignment[p] for p in parents)]
            weight *= p_true if assignment[name] else 1.0 - p_true
        return weight

    def distribution(self, query: str, evidence: dict[str, bool]) -> dict[bool, float]:
        """Return normalized P(query | evidence) by exhaustive enumeration."""
        if query not in self.parents:
            raise ValueError(f"unknown query variable: {query}")
        self._validate_assignment(evidence)
        weights = {False: 0.0, True: 0.0}
        free = [name for name in self.parents if name not in evidence]
        for values in product((False, True), repeat=len(free)):
            assignment = dict(evidence)
            assignment.update(zip(free, values))
            weights[assignment[query]] += self._joint(assignment)
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("evidence has zero probability")
        return {value: weight / total for value, weight in weights.items()}

    def probability(self, query: str, evidence: dict[str, bool]) -> float:
        """Return P(query=True | evidence)."""
        return self.distribution(query, evidence)[True]
