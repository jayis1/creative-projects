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

## Limits

This compact reference implementation rescans all trips per transfer round; it is best for small and medium schedule sets, not production-scale feeds. Walking transfers, calendars, service exceptions, fares, and vehicle capacity are outside its model. Schedule data must be pre-expanded into concrete trips.
