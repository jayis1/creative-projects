# Vector Clock Simulator

A standalone causal-tracing toolkit that turns distributed-process event logs into Lamport timestamps, vector clocks, and concurrency reports.

Run it from this directory:

```bash
python3 cli.py a b --event a:local --event a:send:b:job --event b:receive:a:done
```

Example output:

```text
a: local L=1 V=(1, 0)
a: send L=2 V=(2, 0)
b: receive L=3 V=(2, 1)
concurrent pairs: 0
```

## How it works

Each process owns one vector-clock component. Local and send events increment their component. A receive merges the latest known sender vector before incrementing the receiver. Vector comparison gives a partial order: if neither vector dominates the other, the events are concurrent. The immutable `Event` records preserve both Lamport and vector timestamps for auditability.

## Aggregate analysis

Use `--summary` for machine-friendly counts of events, message directions, concurrency, and the causal frontier:

```bash
python3 cli.py a b --event a:local --event b:local --summary
```

The API exposes the same information through `trace.summary()` and returns the currently maximal events with `trace.causal_frontier()`.

## Python API

```python
from vector_clock_sim import Trace
trace = Trace(("worker-a", "worker-b"))
trace.record([("worker-a", "send", "worker-b", "task")])
print(trace.to_json())
```

The JSON format stores process names and event vectors and can be loaded with `load_json`. Invalid process names, malformed actions, unknown event kinds, and incomplete send/receive actions raise `TraceError` instead of being silently accepted.

## Tests

```bash
python3 -m pytest -q
```

The project uses only the Python standard library at runtime. `pytest` is needed for the test suite.
