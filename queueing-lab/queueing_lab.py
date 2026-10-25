"""Deterministic discrete-event simulation for open queueing networks."""
from __future__ import annotations

import argparse
import heapq
import json
import math
import random
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Station:
    name: str
    servers: int
    mean_service: float


@dataclass(frozen=True)
class Route:
    source: str
    destination: str | None
    probability: float


@dataclass
class _Server:
    available: float = 0.0
    queue: list[tuple[float, int]] = field(default_factory=list)


@dataclass
class _StationState:
    spec: Station
    servers: list[_Server]
    arrivals: list[float] = field(default_factory=list)
    waits: list[float] = field(default_factory=list)
    busy_time: float = 0.0


class QueueingNetwork:
    """Simulate exponential-service stations with probabilistic routing.

    The simulator uses a single event heap. Arrival rate is expressed as
    interarrival mean, and all durations are in arbitrary consistent units.
    """

    def __init__(self, stations: Iterable[Station], routes: Iterable[Route], *, seed: int = 0):
        specs = list(stations)
        if not specs or len(specs) > 64:
            raise ValueError("network needs 1..64 stations")
        if len({s.name for s in specs}) != len(specs):
            raise ValueError("station names must be unique")
        for s in specs:
            if not s.name or s.servers < 1 or s.servers > 128 or not math.isfinite(s.mean_service) or s.mean_service <= 0:
                raise ValueError(f"invalid station: {s!r}")
        self.states = {s.name: _StationState(s, [_Server() for _ in range(s.servers)]) for s in specs}
        self.routes: dict[str, list[Route]] = {s.name: [] for s in specs}
        for route in routes:
            if route.source not in self.states or (route.destination is not None and route.destination not in self.states):
                raise ValueError(f"unknown route endpoint: {route!r}")
            if not math.isfinite(route.probability) or route.probability < 0:
                raise ValueError("route probabilities must be finite and nonnegative")
            self.routes[route.source].append(route)
        for name, outgoing in self.routes.items():
            if not outgoing or abs(sum(r.probability for r in outgoing) - 1.0) > 1e-9:
                raise ValueError(f"routes from {name!r} must sum to 1")
        self.rng = random.Random(seed)

    def run(self, *, customers: int, interarrival_mean: float, max_events: int = 2_000_000) -> dict:
        """Run a bounded batch; customers is the number entering the first station."""
        if not isinstance(customers, int) or isinstance(customers, bool) or not 1 <= customers <= 100_000:
            raise ValueError("customers must be an integer in 1..100000")
        if not math.isfinite(interarrival_mean) or interarrival_mean <= 0:
            raise ValueError("interarrival_mean must be finite and positive")
        if not isinstance(max_events, int) or max_events < customers or max_events > 2_000_000:
            raise ValueError("max_events must be an integer from customers to 2000000")

        heap: list[tuple[float, int, str, int, float]] = []
        seq = 0
        first = next(iter(self.states))
        for cid in range(customers):
            at = self.rng.expovariate(1.0 / interarrival_mean) if cid else 0.0
            heapq.heappush(heap, (at, seq, first, cid, at)); seq += 1
        completed = 0
        processed = 0
        last_time = 0.0
        while heap:
            at, _, name, cid, entered_at = heapq.heappop(heap)
            processed += 1
            if processed > max_events:
                raise RuntimeError("event limit exceeded; possible recirculating network")
            last_time = at
            state = self.states[name]
            state.arrivals.append(at)
            server = min(state.servers, key=lambda s: (max(at, s.available), len(s.queue)))
            start = max(at, server.available)
            state.waits.append(start - at)
            service = self.rng.expovariate(1.0 / state.spec.mean_service)
            finish = start + service
            server.available = finish
            state.busy_time += service
            choice = self.rng.random()
            cumulative = 0.0
            destination = None
            for route in self.routes[name]:
                cumulative += route.probability
                if choice < cumulative:
                    destination = route.destination
                    break
            if destination is None:
                completed += 1
            else:
                heapq.heappush(heap, (finish, seq, destination, cid, finish)); seq += 1
        result = {"seed": self.rng.seed if False else None}
        result = {"customers_entered": customers, "completed": completed, "events": processed, "makespan": last_time,
                  "stations": {}}
        for name, st in self.states.items():
            result["stations"][name] = {
                "visits": len(st.arrivals), "mean_wait": sum(st.waits) / len(st.waits) if st.waits else 0.0,
                "utilization": min(1.0, st.busy_time / (last_time * st.spec.servers)) if last_time else 0.0,
                "throughput": len(st.arrivals) / last_time if last_time else 0.0}
        return result


def demo(seed: int = 7, customers: int = 500) -> dict:
    stations = [Station("intake", 1, 0.8), Station("inspection", 2, 1.0), Station("repair", 1, 2.0)]
    routes = [Route("intake", "inspection", 1.0), Route("inspection", "repair", 0.25),
              Route("inspection", None, 0.75), Route("repair", "inspection", 1.0)]
    return QueueingNetwork(stations, routes, seed=seed).run(customers=customers, interarrival_mean=1.5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a reproducible service-network simulation")
    parser.add_argument("--customers", type=int, default=500)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(demo(args.seed, args.customers), indent=2, sort_keys=True))
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
