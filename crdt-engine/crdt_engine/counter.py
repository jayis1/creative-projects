"""
Counter CRDTs: G-Counter, PN-Counter, and op-based variants.

G-Counter (Grow-only Counter)
    A state-based CvRDT where each replica maintains its own non-negative
    counter.  Merge = pointwise max.  Value = sum of all entries.

PN-Counter (Positive-Negative Counter)
    Two G-Counters: one for increments, one for decrements.
    Value = inc.value() - dec.value().
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .vector_clock import VectorClock


# ════════════════════════════════════════════════════════════════════
#  State-based (CvRDT) counters
# ════════════════════════════════════════════════════════════════════

class GCounter:
    """State-based grow-only counter (CvRDT)."""

    def __init__(self, node_id: str, state: Dict[str, int] | None = None) -> None:
        self.node_id = node_id
        self._state: Dict[str, int] = dict(state) if state else {}
        self._state.setdefault(node_id, 0)

    def increment(self, amount: int = 1) -> int:
        if amount < 0:
            raise ValueError("G-Counter increment must be non-negative")
        self._state[self.node_id] = self._state.get(self.node_id, 0) + amount
        return self._state[self.node_id]

    def value(self) -> int:
        return sum(self._state.values())

    def state(self) -> Dict[str, int]:
        return dict(self._state)

    def merge(self, other_state: Dict[str, int]) -> None:
        for nid, val in other_state.items():
            self._state[nid] = max(self._state.get(nid, 0), val)

    def merge_crdt(self, other: "GCounter") -> None:
        self.merge(other.state())

    def to_dict(self) -> Dict[str, int]:
        return {"node_id": self.node_id, "state": dict(self._state)}

    @classmethod
    def from_dict(cls, d: Dict) -> "GCounter":
        return cls(d["node_id"], d["state"])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GCounter):
            return NotImplemented
        all_keys = set(self._state) | set(other._state)
        return all(self._state.get(k, 0) == other._state.get(k, 0) for k in all_keys)

    def __repr__(self) -> str:
        return f"GCounter({self.node_id}, value={self.value()}, state={self._state})"


class PNCounter:
    """State-based positive-negative counter (CvRDT)."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._p = GCounter(node_id)  # increments
        self._n = GCounter(node_id)  # decrements

    def increment(self, amount: int = 1) -> int:
        if amount < 0:
            raise ValueError("increment amount must be non-negative")
        self._p.increment(amount)
        return self.value()

    def decrement(self, amount: int = 1) -> int:
        if amount < 0:
            raise ValueError("decrement amount must be non-negative")
        self._n.increment(amount)
        return self.value()

    def value(self) -> int:
        return self._p.value() - self._n.value()

    def state(self) -> Dict[str, Dict[str, int]]:
        return {"p": self._p.state(), "n": self._n.state()}

    def merge(self, other_state: Dict[str, Dict[str, int]]) -> None:
        self._p.merge(other_state.get("p", {}))
        self._n.merge(other_state.get("n", {}))

    def merge_crdt(self, other: "PNCounter") -> None:
        self.merge(other.state())

    def to_dict(self) -> Dict:
        return {"node_id": self.node_id, "p": self._p.state(), "n": self._n.state()}

    @classmethod
    def from_dict(cls, d: Dict) -> "PNCounter":
        obj = cls(d["node_id"])
        obj._p = GCounter(d["node_id"], d["p"])
        obj._n = GCounter(d["node_id"], d["n"])
        return obj

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PNCounter):
            return NotImplemented
        return self._p == other._p and self._n == other._n

    def __repr__(self) -> str:
        return f"PNCounter({self.node_id}, value={self.value()})"


# ════════════════════════════════════════════════════════════════════
#  Op-based (CmRDT) counters
# ════════════════════════════════════════════════════════════════════

class OpGCounter:
    """Operation-based G-Counter.

    Each increment produces an op ``{'type': 'inc', 'node': nid, 'amount': n}``
    that is delivered to all replicas.  Delivery must satisfy *reliable
    causal broadcast* for correctness, though the data structure itself
    is idempotent (at-most-once delivery suffices because we just add
    to the local slot).
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._vc = VectorClock(node_id)
        self._state: Dict[str, int] = {node_id: 0}

    def increment(self, amount: int = 1) -> Tuple[Dict, VectorClock]:
        if amount < 0:
            raise ValueError("increment must be non-negative")
        self._state[self.node_id] = self._state.get(self.node_id, 0) + amount
        self._vc.increment()
        op = {"type": "inc", "node": self.node_id, "amount": amount}
        return op, self._vc.copy()

    def apply(self, op: Dict) -> None:
        if op["type"] != "inc":
            raise ValueError(f"unexpected op type: {op['type']}")
        node = op["node"]
        self._state[node] = self._state.get(node, 0) + op["amount"]

    def value(self) -> int:
        return sum(self._state.values())

    def state(self) -> Dict[str, int]:
        return dict(self._state)

    def __repr__(self) -> str:
        return f"OpGCounter({self.node_id}, value={self.value()})"


class OpPNCounter:
    """Operation-based PN-Counter: inc and dec ops."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._inc = OpGCounter(node_id)
        self._dec = OpGCounter(node_id)

    def increment(self, amount: int = 1) -> Tuple[Dict, VectorClock]:
        if amount < 0:
            raise ValueError("increment must be non-negative")
        op, vc = self._inc.increment(amount)
        op["kind"] = "inc"
        return op, vc

    def decrement(self, amount: int = 1) -> Tuple[Dict, VectorClock]:
        if amount < 0:
            raise ValueError("decrement must be non-negative")
        op, vc = self._dec.increment(amount)
        op["kind"] = "dec"
        return op, vc

    def apply(self, op: Dict) -> None:
        kind = op.get("kind", "inc")
        if kind == "inc":
            self._inc.apply(op)
        elif kind == "dec":
            self._dec.apply(op)
        else:
            raise ValueError(f"unknown op kind: {kind}")

    def value(self) -> int:
        return self._inc.value() - self._dec.value()

    def __repr__(self) -> str:
        return f"OpPNCounter({self.node_id}, value={self.value()})"