# Elevator Dispatch

A deterministic, discrete-time elevator fleet simulator that compares car assignments for a stream of passenger calls. It is useful for exploring dispatch tradeoffs without a GUI or third-party packages.

## How it works

Requests are processed by call time. For each request, the simulator estimates each car's earliest pickup as the later of the request time or the car's availability, plus travel from its current floor. It assigns the request to the minimum-pickup car (lowest index wins ties), then records pickup, arrival, wait, and ride durations.

This is a deliberately bounded single-trip model: a car is committed to one passenger request at a time, and requests are not grouped or reordered. Floor numbers start at zero.

## Quick start

Run a reproducible demo:

```sh
python3 main.py --demo
```

Read a JSON scenario:

```json
{
  "floors": 8,
  "cars": 2,
  "requests": [
    {"time": 0, "origin": 0, "destination": 5},
    {"time": 2, "origin": 4, "destination": 1}
  ]
}
```

Save as `scenario.json` and run `python3 main.py scenario.json`. Output is JSON; each row includes the original request, assigned car, pickup and arrival times, wait, and ride duration. Add `--summary` to report request count, total/average/maximum wait, and per-car assignment counts instead. For example, `python3 main.py --demo --summary` prints aggregate metrics.

## Validation and limits

Times must be nonnegative integers, floors must be in range, and a request must travel between distinct floors. The simulator supports 1–64 cars. Input files are read-only and no shell commands or external dependencies are used. The simplified model does not simulate passenger capacity, multi-stop routes, door dwell, or car movement while idle.

## Known Issues (Resolved)

- The public Python API previously accepted fractional request times and floor counts (and boolean car counts), which could yield non-integral scheduling results or treat `True` as one car. `test_direct_api_rejects_non_integer_values` reproduced the invalid acceptance before the fix; the API now requires exact integers for times, floors, and car counts.

## Testing

Run `python3 -m unittest discover -s tests -v` from this directory. The suite covers assignment timing, chronological ordering, empty schedules, invalid bounds/types, and aggregate metrics.
