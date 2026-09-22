"""An augmented interval tree with deterministic relation queries."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Iterator
from .model import Event, Relation

@dataclass
class _Node:
    event: Event
    priority: float
    left: "_Node | None" = None
    right: "_Node | None" = None
    max_end: float = 0.0
    def __post_init__(self) -> None: self.max_end = self.event.end

def _refresh(n: _Node | None) -> None:
    if n: n.max_end = max(n.event.end, n.left.max_end if n.left else float("-inf"), n.right.max_end if n.right else float("-inf"))

def _rotate_left(n: _Node) -> _Node:
    r = n.right; assert r
    n.right = r.left; r.left = n; _refresh(n); _refresh(r); return r

def _rotate_right(n: _Node) -> _Node:
    l = n.left; assert l
    n.left = l.right; l.right = n; _refresh(n); _refresh(l); return l

class IntervalIndex:
    """Treap-backed interval index. Queries prune subtrees by maximum end."""
    def __init__(self, events: Iterable[Event] = ()) -> None:
        self._root: _Node | None = None
        self._ids: set[str] = set()
        for event in events: self.add(event)

    def add(self, event: Event) -> None:
        if event.id in self._ids: raise ValueError(f"duplicate event id: {event.id}")
        self._root = self._insert(self._root, _Node(event, self._priority(event.id)))
        self._ids.add(event.id)

    def remove(self, event_id: str) -> Event:
        removed: list[Event] = []
        self._root = self._delete(self._root, event_id, removed)
        if not removed: raise KeyError(event_id)
        self._ids.remove(event_id); return removed[0]

    def overlaps(self, start: float, end: float, label: str | None = None) -> list[Event]:
        """Return intervals intersecting [start, end), optionally by label."""
        if start >= end: raise ValueError("query start must be less than end")
        out: list[Event] = []
        def visit(n: _Node | None) -> None:
            if not n or n.max_end <= start: return
            visit(n.left)
            if n.event.start < end and n.event.end > start and (label is None or n.event.label == label): out.append(n.event)
            if n.event.start < end: visit(n.right)
        visit(self._root); return sorted(out, key=lambda e: (e.start, e.end, e.id))

    def related(self, event: Event, relation: Relation) -> list[Event]:
        return [candidate for candidate in self.overlaps(event.start - (event.end-event.start), event.end + (event.end-event.start)) if candidate.id != event.id and event.relation_to(candidate) is relation]

    def __len__(self) -> int: return len(self._ids)
    def __iter__(self) -> Iterator[Event]: return iter(self.overlaps(float("-inf"), float("inf")))

    @staticmethod
    def _priority(key: str) -> float:
        x = 2166136261
        for byte in key.encode(): x = ((x ^ byte) * 16777619) & 0xffffffff
        return x / 0xffffffff
    def _insert(self, n: _Node | None, item: _Node) -> _Node:
        if not n: return item
        if (item.event.start, item.event.id) < (n.event.start, n.event.id):
            n.left = self._insert(n.left, item)
            if n.left and n.left.priority < n.priority: n = _rotate_right(n)
        else:
            n.right = self._insert(n.right, item)
            if n.right and n.right.priority < n.priority: n = _rotate_left(n)
        _refresh(n); return n
    def _delete(self, n: _Node | None, event_id: str, removed: list[Event]) -> _Node | None:
        if not n: return None
        if n.event.id == event_id:
            removed.append(n.event)
            if not n.left: return n.right
            if not n.right: return n.left
            if n.left.priority < n.right.priority: n = _rotate_right(n); n.right = self._delete(n.right, event_id, removed)
            else: n = _rotate_left(n); n.left = self._delete(n.left, event_id, removed)
        elif (event_id, ) != ("",):
            n.left = self._delete(n.left, event_id, removed)
            if not removed: n.right = self._delete(n.right, event_id, removed)
        _refresh(n); return n
