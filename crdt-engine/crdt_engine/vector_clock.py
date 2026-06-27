"""
Vector clocks for partial-order event tracking in distributed systems.

A vector clock tracks the causal ordering of events across ``n`` replicas.
Each replica has a unique ``node_id`` and maintains a monotonically-ncreasing
counter for itself.  The full vector ``(c_A, c_B, ...)`` can be compared with
the *happens-before* relation (``->``) to determine whether two events are
causally ordered or *concurrent*.
"""

from __future__ import annotations

import copy
from typing import Dict, Iterable, List, Tuple


class VectorClock:
    """A vector clock indexed by node id (string)."""

    __slots__ = ("_clock", "_node_id")

    def __init__(self, node_id: str, clock: Dict[str, int] | None = None) -> None:
        self._node_id = node_id
        self._clock: Dict[str, int] = dict(clock) if clock else {}
        # ensure own entry exists
        self._clock.setdefault(node_id, 0)

    # ------------------------------------------------------------------ #
    # Properties / accessors
    # ------------------------------------------------------------------ #
    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def clock(self) -> Dict[str, int]:
        """Return a shallow copy so external code can't mutate us."""
        return dict(self._clock)

    # alias used by some codebases
    @property
    def vector(self) -> Dict[str, int]:
        return self.clock

    def get(self, node_id: str) -> int:
        return self._clock.get(node_id, 0)

    # ------------------------------------------------------------------ #
    # Core operations
    # ------------------------------------------------------------------ #
    def increment(self, amount: int = 1) -> int:
        """Increment the local counter and return the new value."""
        if amount < 0:
            raise ValueError("increment amount must be non-negative")
        self._clock[self._node_id] = self._clock.get(self._node_id, 0) + amount
        return self._clock[self._node_id]

    def observe(self, other: "VectorClock") -> None:
        """Merge *other* into self (take pointwise max), then bump own clock."""
        for nid, val in other._clock.items():
            self._clock[nid] = max(self._clock.get(nid, 0), val)
        self._clock[self._node_id] = self._clock.get(self._node_id, 0) + 1

    def merge(self, other: "VectorClock") -> None:
        """Pointwise max merge without incrementing (pure merge)."""
        for nid, val in other._clock.items():
            self._clock[nid] = max(self._clock.get(nid, 0), val)

    def copy(self) -> "VectorClock":
        return VectorClock(self._node_id, copy.deepcopy(self._clock))

    # ------------------------------------------------------------------ #
    # Comparison
    # ------------------------------------------------------------------ #
    def __le__(self, other: "VectorClock") -> bool:
        """self <= other  (self happened-before or is equal to other)."""
        all_keys = set(self._clock) | set(other._clock)
        return all(self.get(k) <= other.get(k) for k in all_keys)

    def __lt__(self, other: "VectorClock") -> bool:
        return self <= other and self != other

    def __ge__(self, other: "VectorClock") -> bool:
        return other <= self

    def __gt__(self, other: "VectorClock") -> bool:
        return other < self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return NotImplemented
        all_keys = set(self._clock) | set(other._clock)
        return all(self.get(k) == other.get(k) for k in all_keys)

    def __hash__(self) -> int:
        return hash(tuple(sorted(self._clock.items())))

    # ------------------------------------------------------------------ #
    # Causality helpers
    # ------------------------------------------------------------------ #
    def is_concurrent_with(self, other: "VectorClock") -> bool:
        return not (self <= other or other <= self)

    @staticmethod
    def compare(a: "VectorClock", b: "VectorClock") -> str:
        """Return 'before', 'after', 'equal', or 'concurrent'."""
        if a == b:
            return "equal"
        if a < b:
            return "before"
        if a > b:
            return "after"
        return "concurrent"

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, int]:
        return self.clock

    @classmethod
    def from_dict(cls, node_id: str, d: Dict[str, int]) -> "VectorClock":
        return cls(node_id, d)

    def __repr__(self) -> str:
        inner = ", ".join(f"{k}: {v}" for k, v in sorted(self._clock.items()))
        return f"VectorClock({self._node_id}{{{inner}}})"

    def __len__(self) -> int:
        return len(self._clock)

    # ------------------------------------------------------------------ #
    # Iterable support
    # ------------------------------------------------------------------ #
    def keys(self) -> Iterable[str]:
        return self._clock.keys()

    def items(self) -> Iterable[Tuple[str, int]]:
        return self._clock.items()