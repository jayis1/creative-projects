# Temporal Circuit

A dependency-free Python toolkit for simulating synchronous digital circuits with explicit propagation delay. Model combinational gates and registers, inspect a deterministic event trace, detect zero-delay combinational cycles, and export traces as CSV, JSON, or VCD waveforms.

## How it works

The simulator uses a discrete-event queue ordered by `(time, insertion sequence)`, so simultaneous events have stable reproducible ordering. Wires notify subscribed gates when values change. Gates schedule their output after a nonnegative delay; an inertial-style generation token invalidates stale pending transitions when an input changes again. Register elements sample their data on rising clock edges and update after their configured delay. Events at the same timestamp are drained to a fixed point, subject to a per-timestamp event budget to protect against oscillation.

## Usage

Python 3.10+, standard library only.

```python
from temporal_circuit import Circuit

c = Circuit()
a = c.input("a", 1)
b = c.input("b", 0)
y = c.and_gate("y", a, b, delay=2)
c.run(until=5)
print(y.value)  # 0
print(c.trace_json())
```

The CLI runs a small half-adder and emits a trace:

```sh
python3 cli.py --format csv
python3 cli.py --format json --until 20
python3 cli.py --format vcd --until 20
python3 -m unittest -v
```

## API

`Circuit.input(name, value=0)` creates a driven input. `and_gate`, `or_gate`, `xor_gate`, `not_gate` and `register` build components and return output wires. Values are binary integers. `run(until=None, max_events=100000)` processes events; `set_input(name, value, at=...)` schedules external input changes. Trace rows contain time, wire, old value, new value, and cause. Invalid names, values, times, and event limits raise `ValueError`.

Circuit size and simulation time are caller-controlled; `max_events` and `max_events_at_time` bound pathological activity. On budget exhaustion, the triggering event remains queued, so a caller may resume with a larger budget. The library does not model analog voltage, setup/hold violations, or metastability.

## Known Issues (Resolved)

- Event-budget exhaustion previously removed the next event before raising, making a paused simulation impossible to resume reliably. The simulator now checks both budgets before dequeueing; a regression test forces exhaustion and confirms the input event is processed after resuming with a larger budget.
