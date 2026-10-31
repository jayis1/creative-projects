"""Time-dependent, FIFO-safe transit routing using a compact RAPTOR-style scan."""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
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
        if any(not isinstance(s, str) or not s for s in self.stops):
            raise ValueError("stop names must be non-empty strings")
        if not isinstance(self.trip_id, str):
            raise ValueError("trip_id must be a string")


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
        if not isinstance(max_transfers, int) or isinstance(max_transfers, bool) or not 0 <= max_transfers <= 100:
            raise ValueError("max_transfers must be an integer from 0 through 100")
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


def load_network(path: str | Path) -> Network:
    """Load a JSON schedule object with trips: [{id, stops, times}]."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read schedule JSON: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"trips"} or not isinstance(data["trips"], list):
        raise ValueError("schedule must be an object containing only a trips array")
    if len(data["trips"]) > 100_000:
        raise ValueError("schedule exceeds 100000-trip safety limit")
    trips = []
    for index, item in enumerate(data["trips"]):
        if not isinstance(item, dict) or set(item) - {"id", "stops", "times"} or not {"stops", "times"} <= set(item):
            raise ValueError(f"trip {index} must contain stops and times, with optional id")
        if not isinstance(item["stops"], list) or not all(isinstance(s, str) for s in item["stops"]):
            raise ValueError(f"trip {index} stops must be an array of strings")
        if not isinstance(item["times"], list):
            raise ValueError(f"trip {index} times must be an array")
        trip_id = item.get("id", str(index))
        if not isinstance(trip_id, str):
            raise ValueError(f"trip {index} id must be a string")
        try:
            trips.append(Trip(tuple(item["stops"]), tuple(item["times"]), trip_id))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid trip {index}: {exc}") from exc
    return Network(trips)


def journey_dict(journey: Journey) -> dict:
    """Return a JSON-ready journey representation."""
    return {"origin": journey.origin, "destination": journey.destination,
            "departure": journey.departure, "arrival": journey.arrival,
            "transfers": journey.transfers,
            "legs": [{"trip_id": leg.trip_id, "board": leg.board,
                      "alight": leg.alight, "depart": leg.depart,
                      "arrive": leg.arrive} for leg in journey.legs]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find earliest-arrival journeys in a JSON transit timetable.")
    parser.add_argument("schedule", nargs="?", help="JSON timetable path; omit for the built-in demo")
    parser.add_argument("--from-stop", dest="origin")
    parser.add_argument("--to-stop", dest="destination")
    parser.add_argument("--depart", type=int, default=0, help="earliest departure in minutes after midnight")
    parser.add_argument("--max-transfers", type=int, default=4)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        if not args.schedule:
            if args.origin or args.destination or args.json:
                parser.error("a schedule file is required for route-query options")
            print(demo())
            return 0
        if not args.origin or not args.destination:
            parser.error("--from-stop and --to-stop are required with a schedule")
        network = load_network(args.schedule)
        journey = network.route(args.origin, args.destination, args.depart, args.max_transfers)
    except ValueError as exc:
        parser.error(str(exc))
    if journey is None:
        print(json.dumps({"journey": None}) if args.json else "No journey found.")
        return 1
    if args.json:
        print(json.dumps(journey_dict(journey), ensure_ascii=False, sort_keys=True))
    else:
        print(f"Arrive {format_time(journey.arrival)} ({journey.transfers} transfer(s))")
        for leg in journey.legs:
            print(f"{leg.trip_id}: {leg.board} {format_time(leg.depart)} -> {leg.alight} {format_time(leg.arrive)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
