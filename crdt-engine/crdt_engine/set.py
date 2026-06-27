"""
Set CRDTs: G-Set, 2P-Set, LWW-Set, OR-Set.

All sets are state-based (CvRDT).  Elements must be hashable.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Set, Tuple


class GSet:
    """Grow-only set (CvRDT).  Once an element is added it can never be removed."""

    def __init__(self) -> None:
        self._elements: Set[Any] = set()

    def add(self, element: Any) -> None:
        self._elements.add(element)

    def add_all(self, elements: Iterable[Any]) -> None:
        for e in elements:
            self.add(e)

    def contains(self, element: Any) -> bool:
        return element in self._elements

    def __contains__(self, element: Any) -> bool:
        return element in self._elements

    def elements(self) -> Set[Any]:
        return set(self._elements)

    def value(self) -> Set[Any]:
        """Return the set of elements (current value)."""
        return set(self._elements)

    def state(self) -> Set[Any]:
        return self.value()

    def merge(self, other_state: Set[Any]) -> None:
        self._elements |= other_state

    def merge_crdt(self, other: "GSet") -> None:
        self.merge(other.state())

    def size(self) -> int:
        return len(self._elements)

    def __len__(self) -> int:
        return len(self._elements)

    def to_list(self) -> list:
        return list(self._elements)

    def to_dict(self) -> Dict:
        # Elements must be JSON-serializable by caller; we just store them.
        return {"elements": list(self._elements)}

    @classmethod
    def from_dict(cls, d: Dict) -> "GSet":
        s = cls()
        s.add_all(d["elements"])
        return s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GSet):
            return NotImplemented
        return self._elements == other._elements

    def __repr__(self) -> str:
        return f"GSet({self._elements})"


class TwoPSet:
    """Two-phase set: add-set + remove-set.

    An element is in the set if it has been added and not yet removed.
    Once removed it can never be re-added (a tombstone blocks it).
    """

    def __init__(self) -> None:
        self._added: Set[Any] = set()
        self._removed: Set[Any] = set()

    def add(self, element: Any) -> None:
        self._added.add(element)

    def remove(self, element: Any) -> None:
        if element in self._added:
            self._removed.add(element)

    def contains(self, element: Any) -> bool:
        return element in self._added and element not in self._removed

    def __contains__(self, element: Any) -> bool:
        return self.contains(element)

    def value(self) -> Set[Any]:
        return self._added - self._removed

    def state(self) -> Dict[str, Set[Any]]:
        return {"added": set(self._added), "removed": set(self._removed)}

    def merge(self, other_state: Dict[str, Set[Any]]) -> None:
        self._added |= other_state.get("added", set())
        self._removed |= other_state.get("removed", set())

    def merge_crdt(self, other: "TwoPSet") -> None:
        self.merge(other.state())

    def size(self) -> int:
        return len(self.value())

    def __len__(self) -> int:
        return self.size()

    def to_dict(self) -> Dict:
        return {"added": list(self._added), "removed": list(self._removed)}

    @classmethod
    def from_dict(cls, d: Dict) -> "TwoPSet":
        s = cls()
        for e in d["added"]:
            s._added.add(e)
        for e in d["removed"]:
            s._removed.add(e)
        return s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TwoPSet):
            return NotImplemented
        return self._added == other._added and self._removed == other._removed

    def __repr__(self) -> str:
        return f"TwoPSet(added={self._added}, removed={self._removed})"


class LWWSet:
    """Last-Writer-Wins Set.

    Each element maps to (add_time, remove_time) timestamps.
    An element is in the set if it has been added and:
      - it has not been removed, OR
      - it was removed before it was added (add_time > remove_time).
    """

    def __init__(self) -> None:
        # element -> (add_ts, remove_ts)  (None means never)
        self._add_ts: Dict[Any, float] = {}
        self._rem_ts: Dict[Any, float] = {}

    @staticmethod
    def _now() -> float:
        return time.time()

    def add(self, element: Any, ts: float | None = None) -> None:
        ts = ts if ts is not None else self._now()
        if element not in self._add_ts or ts > self._add_ts[element]:
            self._add_ts[element] = ts

    def remove(self, element: Any, ts: float | None = None) -> None:
        ts = ts if ts is not None else self._now()
        if element not in self._rem_ts or ts > self._rem_ts[element]:
            self._rem_ts[element] = ts

    def contains(self, element: Any) -> bool:
        add_t = self._add_ts.get(element)
        if add_t is None:
            return False
        rem_t = self._rem_ts.get(element)
        if rem_t is None:
            return True
        return add_t > rem_t

    def __contains__(self, element: Any) -> bool:
        return self.contains(element)

    def value(self) -> Set[Any]:
        result = set()
        for e, add_t in self._add_ts.items():
            rem_t = self._rem_ts.get(e)
            if rem_t is None or add_t > rem_t:
                result.add(e)
        return result

    def state(self) -> Dict[str, Dict[Any, float]]:
        return {"add": dict(self._add_ts), "rem": dict(self._rem_ts)}

    def merge(self, other_state: Dict[str, Dict[Any, float]]) -> None:
        for e, ts in other_state.get("add", {}).items():
            if e not in self._add_ts or ts > self._add_ts[e]:
                self._add_ts[e] = ts
        for e, ts in other_state.get("rem", {}).items():
            if e not in self._rem_ts or ts > self._rem_ts[e]:
                self._rem_ts[e] = ts

    def merge_crdt(self, other: "LWWSet") -> None:
        self.merge(other.state())

    def size(self) -> int:
        return len(self.value())

    def __len__(self) -> int:
        return self.size()

    def to_dict(self) -> Dict:
        return {"add": dict(self._add_ts), "rem": dict(self._rem_ts)}

    @classmethod
    def from_dict(cls, d: Dict) -> "LWWSet":
        s = cls()
        s._add_ts = dict(d.get("add", {}))
        s._rem_ts = dict(d.get("rem", {}))
        return s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LWWSet):
            return NotImplemented
        return self._add_ts == other._add_ts and self._rem_ts == other._rem_ts

    def __repr__(self) -> str:
        return f"LWWSet(add_ts={self._add_ts}, rem_ts={self._rem_ts})"


class ORSet:
    """Observed-Remove Set (add-wins OR-Set).

    Each add operation associates a unique tag (UID) with the element.
    Remove only deletes *observed* tags; concurrent adds with new tags
    survive the remove.
    """

    def __init__(self) -> None:
        # element -> set of add-tokens
        self._elements: Dict[Any, Set[Any]] = {}
        # global set of removed tokens (tombstones)
        self._tombstones: Set[Any] = set()
        self._counter = 0  # local token counter

    def _new_token(self) -> str:
        self._counter += 1
        return f"t{self._counter}"

    def add(self, element: Any, token: Any | None = None) -> Any:
        """Add *element* with a unique token; return the token."""
        if token is None:
            token = self._new_token()
        if element not in self._elements:
            self._elements[element] = set()
        self._elements[element].add(token)
        return token

    def remove(self, element: Any) -> None:
        """Remove all *observed* tokens for *element*."""
        if element in self._elements:
            self._tombstones |= self._elements[element]
            self._elements[element] = set()

    def remove_token(self, element: Any, token: Any) -> None:
        """Remove a single observed token for *element*."""
        if element in self._elements and token in self._elements[element]:
            self._tombstones.add(token)
            self._elements[element].discard(token)

    def contains(self, element: Any) -> bool:
        return element in self._elements and len(self._elements[element]) > 0

    def __contains__(self, element: Any) -> bool:
        return self.contains(element)

    def value(self) -> Set[Any]:
        return {e for e, toks in self._elements.items() if len(toks) > 0}

    def state(self) -> Dict:
        return {
            "elements": {k: set(v) for k, v in self._elements.items()},
            "tombstones": set(self._tombstones),
        }

    def merge(self, other_state: Dict) -> None:
        other_elements = other_state.get("elements", {})
        other_tombs = other_state.get("tombstones", set())
        # union tombstones
        self._tombstones |= other_tombs
        # merge element->tokens
        for e, toks in other_elements.items():
            if e not in self._elements:
                self._elements[e] = set()
            self._elements[e] |= toks
        # apply tombstones: remove any tombstoned tokens from live sets
        for e in self._elements:
            self._elements[e] -= self._tombstones

    def merge_crdt(self, other: "ORSet") -> None:
        self.merge(other.state())

    def size(self) -> int:
        return len(self.value())

    def __len__(self) -> int:
        return self.size()

    def to_dict(self) -> Dict:
        return {
            "elements": {k: list(v) for k, v in self._elements.items()},
            "tombstones": list(self._tombstones),
            "counter": self._counter,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "ORSet":
        s = cls()
        s._elements = {k: set(v) for k, v in d.get("elements", {}).items()}
        s._tombstones = set(d.get("tombstones", []))
        s._counter = d.get("counter", 0)
        return s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ORSet):
            return NotImplemented
        return self._elements == other._elements and self._tombstones == other._tombstones

    def __repr__(self) -> str:
        return f"ORSet(elements={self._elements}, tombstones={self._tombstones})"