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
                 incubation_days: int = 3, infectious_days: int = 5, seed: int = 1,
                 topology: str = "ring", intervention_day: int | None = None,
                 beta_multiplier: float = 1.0):
        discrete = (population, contacts_per_person, incubation_days, infectious_days)
        if any(type(value) is not int for value in discrete): raise ValueError("population, degree, and stage durations must be integers")
        if intervention_day is not None and type(intervention_day) is not int: raise ValueError("intervention_day must be an integer")
        if population < 2: raise ValueError("population must be at least 2")
        if not 0 <= contacts_per_person < population: raise ValueError("contacts_per_person must be in [0, population)")
        if not 0 <= beta <= 1: raise ValueError("beta must be between 0 and 1")
        if incubation_days < 1 or infectious_days < 1: raise ValueError("stage durations must be positive")
        if topology not in {"ring", "random"}: raise ValueError("topology must be 'ring' or 'random'")
        if intervention_day is not None and intervention_day < 0: raise ValueError("intervention_day must be non-negative")
        if not 0 <= beta_multiplier <= 1: raise ValueError("beta_multiplier must be in [0, 1]")
        self.rng, self.beta = random.Random(seed), beta
        self.incubation_days, self.infectious_days = incubation_days, infectious_days
        self.intervention_day, self.beta_multiplier = intervention_day, beta_multiplier
        self.people = self._make_graph(population, contacts_per_person, topology)
        self.state, self.elapsed = ["S"] * population, [0] * population
        self.state[0] = "E"
        self.history, self.day = [], 0
        self._record()

    def _make_graph(self, n: int, degree: int, topology: str) -> tuple[Person, ...]:
        """Build ring-lattice contacts or a bounded-degree randomized graph."""
        order = list(range(n)); self.rng.shuffle(order)
        neighbors = [set() for _ in range(n)]
        if topology == "ring":
            for pos, u in enumerate(order):
                for offset in range(1, degree // 2 + 1):
                    v = order[(pos + offset) % n]
                    neighbors[u].add(v); neighbors[v].add(u)
                if degree % 2 and n % 2 == 0 and pos < n // 2:
                    v = order[pos + n // 2]
                    neighbors[u].add(v); neighbors[v].add(u)
        else:
            # Greedy shuffled matching maintains the requested maximum degree.
            remaining = list(order)
            for u in order:
                candidates = [v for v in remaining if v != u and len(neighbors[u]) < degree and len(neighbors[v]) < degree]
                self.rng.shuffle(candidates)
                for v in candidates[:max(0, degree - len(neighbors[u]))]:
                    neighbors[u].add(v); neighbors[v].add(u)
                if u in remaining: remaining.remove(u)
        return tuple(Person(tuple(sorted(row))) for row in neighbors)

    def counts(self) -> dict[str, int]:
        return {key: self.state.count(key) for key in "SEIR"}

    def _record(self) -> None:
        self.history.append({"day": self.day, **self.counts()})

    def step(self) -> dict[str, int]:
        """Advance synchronously; newly infected nodes cannot transmit today."""
        newly_exposed, next_state, next_elapsed = set(), self.state.copy(), self.elapsed.copy()
        transmission = self.beta * (self.beta_multiplier if self.intervention_day is not None and self.day >= self.intervention_day else 1.0)
        for i, status in enumerate(self.state):
            if status == "I":
                for contact in self.people[i].contacts:
                    if self.state[contact] == "S" and self.rng.random() < transmission:
                        newly_exposed.add(contact)
            if status in ("E", "I"):
                next_elapsed[i] += 1
                limit = self.incubation_days if status == "E" else self.infectious_days
                if next_elapsed[i] >= limit:
                    next_state[i] = "I" if status == "E" else "R"
                    next_elapsed[i] = 0
        for i in newly_exposed: next_state[i], next_elapsed[i] = "E", 0
        self.state, self.elapsed = next_state, next_elapsed
        self.day += 1; self._record()
        return self.history[-1].copy()

    def run(self, max_days: int = 365) -> list[dict[str, int]]:
        if type(max_days) is not int or max_days < 0: raise ValueError("max_days must be a non-negative integer")
        for _ in range(max_days):
            if not any(s in ("E", "I") for s in self.state): break
            self.step()
        return [row.copy() for row in self.history]

    def summary(self) -> dict[str, int | float]:
        c = self.counts()
        ever = len(self.state) - c["S"]
        return {"days": self.day, "population": len(self.state), "ever_infected": ever,
                "attack_rate": ever / len(self.state),
                "peak_infectious": max(row["I"] for row in self.history), **c}

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--contacts", type=int, default=4)
    parser.add_argument("--beta", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--topology", choices=("ring", "random"), default="ring")
    parser.add_argument("--intervention-day", type=int)
    parser.add_argument("--beta-multiplier", type=float, default=1.0)
    parser.add_argument("--demo", action="store_true", help="run a small reproducible example")
    args = parser.parse_args(argv)
    try:
        sim = Epidemic(40 if args.demo else args.population, args.contacts, args.beta,
                       seed=args.seed, topology=args.topology, intervention_day=args.intervention_day,
                       beta_multiplier=args.beta_multiplier)
        print(json.dumps({"summary": sim.summary(), "history": sim.run(args.days)}, indent=2))
    except ValueError as exc: parser.error(str(exc))
    return 0

if __name__ == "__main__": raise SystemExit(main())
