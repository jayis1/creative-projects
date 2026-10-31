# Route Atlas

A standard timetable lookup often favors a single transfer count or treats routes as static edges. Route Atlas instead scans scheduled trips round by round, selecting the earliest feasible arrival with a bounded number of transfers.

## Run it

From this directory:

```sh
python3 route_atlas.py
python3 -m unittest -v
```

Demo output:

```text
Arrive 08:57 (1 transfer(s))
T1: Harbor 08:00 -> Central 08:22
T2: Central 08:28 -> Airport 08:57
```

## How it works

`Trip` stores an ordered stop list and absolute-minute schedule. `Network.route()` maintains earliest-arrival labels and scans each trip for the earliest reachable boarding stop. Each scan round permits another vehicle leg, while an explicit `max_transfers` bound keeps work predictable. Ties resolve deterministically by arrival time, leg count, then trip identifiers. The implementation uses only Python's standard library.

Times are nonnegative integer minutes from the beginning of the service day; values above 1440 represent later days. Trips may contain repeated stops and nondecreasing (including equal) times. The model assumes a FIFO timetable: earlier arrival at a stop is never worse than later arrival for onward journeys.

## Python example

```python
from route_atlas import Network, Trip

network = Network([Trip(("A", "B", "C"), (480, 492, 510), "R1")])
journey = network.route("A", "C", departure=475, max_transfers=2)
print(journey.arrival, journey.legs)
```

`route()` returns `None` when no connection is found within the transfer bound. An origin-to-itself query returns an empty journey at the requested time. Invalid schedule values and search limits raise `ValueError`.

## JSON timetable and CLI

A schedule is an object with one `trips` array; each trip has an optional string `id`, a `stops` array, and a `times` array:

```json
{"trips":[{"id":"R1","stops":["A","B","C"],"times":[480,492,510]}]}
```

Run a query and receive a human-readable itinerary:

```sh
python3 route_atlas.py sample_network.json --from-stop A --to-stop D --depart 475 --max-transfers 2
```

Use `--json` for machine-readable results. Invalid JSON, malformed trips, missing files, and invalid query values produce an argparse error. Inputs are capped at 100,000 trips; this limits schedule loading, while callers should still use appropriate feed sizes.

## Changelog

- Added strict JSON timetable loading and a runnable query CLI.
- Added JSON journey serialization and bounded input validation.
- Added sample timetable and tests for import, export, CLI routing, and malformed files.

## Known Issues (Resolved)

- The source and tests were reviewed for malformed schedule values, empty/unreachable searches, transfer-limit behavior, midnight rollover, and bounded work.
- `Trip` previously accepted truthy non-string stop labels and non-string trip IDs from direct Python callers. Added explicit type checks; `test_trip_rejects_non_string_stops_and_ids` reproduced both failures before the fix and now passes.
- Search previously accepted arbitrarily large `max_transfers`, allowing avoidable unbounded round scans. Capped the value at 100; `test_transfer_bound_is_capped` reproduced the missing rejection before the fix and now passes.

## Limits

This compact reference implementation rescans all trips per transfer round; it is best for small and medium schedule sets, not production-scale feeds. Walking transfers, calendars, service exceptions, fares, and vehicle capacity are outside its model. Schedule data must be pre-expanded into concrete trips.
