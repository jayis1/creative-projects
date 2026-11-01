"""Deterministic, event-driven SEIR epidemic simulation on contact networks."""
from __future__ import annotations
import argparse
import json
import random
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Person:
    """A node in the static contact graph."""
    contacts: tuple[int, ...]

class Epidemic:
    """Discrete-day stochastic SEIR model with reproducible random seed."""
    def __init__(self, population: int, contacts_per_person: int = 4, beta: float = 0.25,
                 incubation_days: int = 3, infectious_days: int = 5, seed: int = 1):
        if population < 2: raise ValueError("population must be at least 2")
        if not 0 <= contacts_per_person < population: raise ValueError("contacts_per_person must be in [0, population)")
        if not 0 <= beta <= 1: raise ValueError("beta must be between 0 and 1")
        if incubation_days < 1 or infectious_days < 1: raise ValueError("stage durations must be positive")
        self.rng = random.Random(seed)
        self.beta, self.incubation_days, self.infectious_days = beta, incubation_days, infectious_days
        self.people = self._make_graph(population, contacts_per_person)
        self.state, self.elapsed = ["S"] * population, [0] * population
        self.state[0] = "E"
        self.history, self.day = [], 0
        self._record()

    def _make_graph(self, n: int, degree: int) -> tuple[Person, ...]:
        """Build an undirected ring-lattice; odd degrees use opposite pairs."""
        order = list(range(n)); self.rng.shuffle(order)
        neighbors = [set() for _ in range(n)]
        for pos, u in enumerate(order):
            for offset in range(1, degree // 2 + 1):
                v = order[(pos + offset) % n]
                neighbors[u].add(v); neighbors[v].add(u)
        if degree % 2 and n % 2 == 0:
            for pos, u in enumerate(order[:n // 2]):
                v = order[pos + n // 2]
                neighbors[u].add(v); neighbors[v].add(u)
        return tuple(Person(tuple(sorted(row))) for row in neighbors)

    def counts(self) -> dict[str, int]:
        return {key: self.state.count(key) for key in "SEIR"}

    def _record(self) -> None:
        self.history.append({"day": self.day, **self.counts()})

    def step(self) -> dict[str, int]:
        """Advance synchronously: newly infected nodes cannot transmit today."""
        newly_exposed, next_state, next_elapsed = set(), self.state.copy(), self.elapsed.copy()
        for i, status in enumerate(self.state):
            if status == "I":
                for contact in self.people[i].contacts:
                    if self.state[contact] == "S" and self.rng.random() < self.beta:
                        newly_exposed.add(contact)
            if status in ("E", "I"):
                next_elapsed[i] += 1
                limit = self.incubation_days if status == "E" else self.infectious_days
                if next_elapsed[i] >= limit:
                    next_state[i] = "I" if status == "E" else "R"
                    next_elapsed[i] = 0
        for i in newly_exposed:
            next_state[i], next_elapsed[i] = "E", 0
        self.state, self.elapsed = next_state, next_elapsed
        self.day += 1; self._record()
        return self.history[-1].copy()

    def run(self, max_days: int = 365) -> list[dict[str, int]]:
        if max_days < 0: raise ValueError("max_days must be non-negative")
        for _ in range(max_days):
            if not any(s in ("E", "I") for s in self.state): break
            self.step()
        return [row.copy() for row in self.history]

    def summary(self) -> dict[str, int]:
        c = self.counts()
        return {"days": self.day, "population": len(self.state), "ever_infected": c["I"] + c["R"], **c}

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--contacts", type=int, default=4)
    parser.add_argument("--beta", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--demo", action="store_true", help="run a small reproducible example")
    args = parser.parse_args(argv)
    try:
        sim = Epidemic(40 if args.demo else args.population, args.contacts, args.beta, seed=args.seed)
        print(json.dumps({"summary": sim.summary(), "history": sim.run(args.days)}, indent=2))
    except ValueError as exc:
        parser.error(str(exc))
    return 0

if __name__ == "__main__": raise SystemExit(main())
