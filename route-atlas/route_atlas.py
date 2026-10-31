"""Time-dependent, FIFO-safe transit routing using a compact RAPTOR-style scan."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Trip:
    """A scheduled vehicle journey; stop_times are absolute minutes after midnight."""
    stops: tuple[str, ...]
    times: tuple[int, ...]
    trip_id: str = ""

    def __post_init__(self) -> None:
        if len(self.stops) < 2 or len(self.stops) != len(self.times):
            raise ValueError("a trip needs matching stop/time sequences of length >= 2")
        if any(not isinstance(t, int) or isinstance(t, bool) or t < 0 for t in self.times):
            raise ValueError("times must be non-negative integer minutes")
        if any(a > b for a, b in zip(self.times, self.times[1:])):
            raise ValueError("trip times must be nondecreasing")
        if any(not s for s in self.stops):
            raise ValueError("stop names must be non-empty")


@dataclass(frozen=True)
class Leg:
    trip_id: str
    board: str
    alight: str
    depart: int
    arrive: int


@dataclass(frozen=True)
class Journey:
    origin: str
    destination: str
    departure: int
    arrival: int
    legs: tuple[Leg, ...]

    @property
    def transfers(self) -> int:
        return max(0, len(self.legs) - 1)


class Network:
    """Immutable schedule collection with earliest-arrival, transfer-bounded search.

    Each round scans all trips once, boarding only at stops reached in the
    previous round. This is deliberately optimized for small timetable feeds,
    with deterministic tie-breaking and no third-party dependencies.
    """
    def __init__(self, trips: Iterable[Trip]):
        self.trips = tuple(trips)
        self._by_stop: dict[str, list[tuple[Trip, int]]] = {}
        for trip in self.trips:
            for i, stop in enumerate(trip.stops):
                self._by_stop.setdefault(stop, []).append((trip, i))

    def route(self, origin: str, destination: str, departure: int,
              max_transfers: int = 4) -> Journey | None:
        if not origin or not destination:
            raise ValueError("origin and destination must be non-empty")
        if not isinstance(departure, int) or isinstance(departure, bool) or departure < 0:
            raise ValueError("departure must be a non-negative integer minute")
        if not isinstance(max_transfers, int) or isinstance(max_transfers, bool) or max_transfers < 0:
            raise ValueError("max_transfers must be a non-negative integer")
        if origin == destination:
            return Journey(origin, destination, departure, departure, ())
        # labels map reachable stop to arrival and complete leg sequence.
        labels: dict[str, tuple[int, tuple[Leg, ...]]] = {origin: (departure, ())}
        best: tuple[int, tuple[Leg, ...]] | None = None
        # Round 0 permits one vehicle; each further round one transfer.
        for _round in range(max_transfers + 1):
            previous = labels.copy()
            updated = labels.copy()
            for trip in self.trips:
                board_index = None
                board_time = None
                for i, stop in enumerate(trip.stops):
                    label = previous.get(stop)
                    if label is not None and label[0] <= trip.times[i]:
                        candidate = (label[0], i)
                        if board_time is None or candidate < (board_time, board_index):
                            board_time, board_index = candidate
                    if board_index is not None and i > board_index:
                        prior_legs = previous[trip.stops[board_index]][1]
                        leg = Leg(trip.trip_id, trip.stops[board_index], stop,
                                  trip.times[board_index], trip.times[i])
                        route_legs = prior_legs + (leg,)
                        old = updated.get(stop)
                        if old is None or (trip.times[i], len(route_legs), tuple(x.trip_id for x in route_legs)) < (old[0], len(old[1]), tuple(x.trip_id for x in old[1])):
                            updated[stop] = (trip.times[i], route_legs)
            labels = updated
            if destination in labels:
                result = labels[destination]
                if best is None or result[0] < best[0]:
                    best = result
        if best is None:
            return None
        return Journey(origin, destination, departure, best[0], best[1])


def format_time(minutes: int) -> str:
    """Format absolute minute-of-day values, retaining day offsets after 24h."""
    if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 0:
        raise ValueError("minutes must be a non-negative integer")
    day, minute = divmod(minutes, 1440)
    return f"{minute // 60:02d}:{minute % 60:02d}" + (f" (+{day}d)" if day else "")


def demo() -> str:
    network = Network([
        Trip(("Harbor", "Museum", "Central"), (480, 491, 502), "T1"),
        Trip(("Central", "Garden", "Airport"), (508, 520, 537), "T2"),
        Trip(("Harbor", "Market", "Airport"), (484, 509, 542), "T3"),
    ])
    journey = network.route("Harbor", "Airport", 475)
    assert journey is not None
    return "\n".join([f"Arrive {format_time(journey.arrival)} ({journey.transfers} transfer(s))"] +
                     [f"{leg.trip_id}: {leg.board} {format_time(leg.depart)} -> {leg.alight} {format_time(leg.arrive)}" for leg in journey.legs])


if __name__ == "__main__":
    print(demo())
