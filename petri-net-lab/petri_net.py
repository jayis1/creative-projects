"""A bounded, deterministic Petri-net simulator and reachability explorer."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Transition:
    name: str
    consume: tuple[tuple[str, int], ...]
    produce: tuple[tuple[str, int], ...]


class PetriNet:
    """Weighted place/transition net; markings are immutable token-count tuples."""
    def __init__(self, places: Mapping[str, int], transitions: tuple[Transition, ...]):
        if not places or any(not p for p in places):
            raise ValueError("at least one named place is required")
        if any(type(n) is not int or n < 0 for n in places.values()):
            raise ValueError("initial tokens must be non-negative integers")
        self.places = tuple(places)
        self.initial = tuple(places[p] for p in self.places)
        self.index = {p: i for i, p in enumerate(self.places)}
        names = set()
        for t in transitions:
            if not t.name or t.name in names:
                raise ValueError("transition names must be unique and non-empty")
            names.add(t.name)
            for arcs in (t.consume, t.produce):
                seen = set()
                for place, weight in arcs:
                    if place not in self.index or place in seen:
                        raise ValueError(f"invalid or duplicate arc place: {place}")
                    if type(weight) is not int or weight <= 0:
                        raise ValueError("arc weights must be positive integers")
                    seen.add(place)
        self.transitions = transitions

    def enabled(self, marking: tuple[int, ...], t: Transition) -> bool:
        self._check_marking(marking)
        return all(marking[self.index[p]] >= w for p, w in t.consume)

    def fire(self, marking: tuple[int, ...], t: Transition) -> tuple[int, ...]:
        if t not in self.transitions:
            raise ValueError("transition does not belong to this net")
        if not self.enabled(marking, t):
            raise ValueError(f"transition {t.name!r} is not enabled")
        result = list(marking)
        for p, w in t.consume:
            result[self.index[p]] -= w
        for p, w in t.produce:
            result[self.index[p]] += w
        return tuple(result)

    def simulate(self, steps: int, schedule: tuple[str, ...] | None = None) -> list[tuple[int, ...]]:
        if type(steps) is not int or not 0 <= steps <= 1_000_000:
            raise ValueError("steps must be an integer between 0 and 1,000,000")
        by_name = {t.name: t for t in self.transitions}
        if schedule is not None and any(n not in by_name for n in schedule):
            raise ValueError("schedule names an unknown transition")
        trace = [self.initial]
        for i in range(steps):
            if schedule is not None and i >= len(schedule):
                break
            candidates = [by_name[schedule[i]]] if schedule is not None else list(self.transitions)
            chosen = next((t for t in candidates if self.enabled(trace[-1], t)), None)
            if chosen is None:
                break
            trace.append(self.fire(trace[-1], chosen))
        return trace

    def reachable(self, max_states: int = 10_000, token_cap: int = 100) -> set[tuple[int, ...]]:
        """Explore all markings, bounding state count and each place's tokens."""
        if type(max_states) is not int or not 1 <= max_states <= 1_000_000:
            raise ValueError("max_states must be in 1..1,000,000")
        if type(token_cap) is not int or token_cap < 0:
            raise ValueError("token_cap must be non-negative")
        seen = {self.initial}
        queue = deque([self.initial])
        while queue:
            marking = queue.popleft()
            for t in self.transitions:
                if self.enabled(marking, t):
                    nxt = self.fire(marking, t)
                    if max(nxt, default=0) > token_cap:
                        continue
                    if nxt not in seen:
                        if len(seen) >= max_states:
                            raise RuntimeError("reachability state limit exceeded")
                        seen.add(nxt)
                        queue.append(nxt)
        return seen

    def _check_marking(self, marking: tuple[int, ...]) -> None:
        if len(marking) != len(self.places) or any(type(n) is not int or n < 0 for n in marking):
            raise ValueError("marking must contain one non-negative integer per place")
