"""Finite transition systems with deterministic, bounded exploration."""
from collections import deque
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable

State = Hashable

@dataclass
class TransitionSystem:
    """An explicit-state graph; states and successors are explored in input order."""
    initial: State
    transitions: dict[State, tuple[State, ...]]
    labels: dict[State, frozenset[str]]

    @classmethod
    def build(cls, initial: State, transitions: dict[State, Iterable[State]], labels: dict[State, Iterable[str]] | None = None):
        edges = {s: tuple(dict.fromkeys(t)) for s, t in transitions.items()}
        edges.setdefault(initial, ())
        for targets in tuple(edges.values()):
            for target in targets:
                edges.setdefault(target, ())
        atoms = {s: frozenset(v) for s, v in (labels or {}).items()}
        return cls(initial, edges, atoms)

    @property
    def states(self) -> tuple[State, ...]:
        """Return reachable states, breadth-first and without duplicates."""
        seen, ordered, queue = {self.initial}, [self.initial], deque([self.initial])
        while queue:
            state = queue.popleft()
            for nxt in self.transitions.get(state, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    ordered.append(nxt)
                    queue.append(nxt)
        return tuple(ordered)

    def predecessors(self, subset: set[State]) -> set[State]:
        return {s for s in self.states if any(t in subset for t in self.transitions.get(s, ()))}

    def successors(self, state: State) -> tuple[State, ...]:
        return self.transitions.get(state, ())

    def shortest_path(self, goal: Callable[[State], bool]) -> list[State] | None:
        """Find a shortest path from the initial state to a matching state."""
        queue, parent = deque([self.initial]), {self.initial: None}
        while queue:
            state = queue.popleft()
            if goal(state):
                path = []
                while state is not None:
                    path.append(state)
                    state = parent[state]
                return list(reversed(path))
            for nxt in self.successors(state):
                if nxt not in parent:
                    parent[nxt] = state
                    queue.append(nxt)
        return None
