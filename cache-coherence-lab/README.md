# Cache Coherence Lab

A dependency-free, trace-driven MESI simulator for exploring how private caches coordinate over a snooping bus. Feed it a short multicore access trace and inspect cache states, read/write totals, invalidations, misses, evictions, and dirty writebacks.

## Contents

- [Features and model](#features-and-model)
- [Quick start](#quick-start)
- [Trace format and Python API](#trace-format-and-python-api)
- [Architecture](#architecture)
- [Tests](#tests)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Recent improvements](#recent-improvements)

## Features and model

- Private bounded caches with deterministic FIFO-by-insertion eviction.
- MESI read sharing, exclusive ownership, modified writes, and peer invalidation.
- Counters for reads, writes, hits, misses, sharing, invalidations, evictions, and writebacks.
- Coherence invariants checked after each access.
- Clear input errors from the CLI; no third-party dependencies.

This is an educational simplified snooping model, not a cycle-accurate hardware simulator. Byte addresses map to line tags using integer division by `line_size`.

## Quick start

Requires Python 3.9+.

```sh
cd cache-coherence-lab
python3 main.py
python3 main.py trace.json --cores 2 --capacity 4 --line-size 16
python3 -m unittest discover -s tests -v
```

With no trace file, the CLI runs a built-in example and prints a JSON report. The report includes separate `reads` and `writes` totals, which sum to the number of successfully executed accesses.

## Trace format and Python API

A trace is a JSON array of `[core, operation, byte_address]` records. For example, save this as `trace.json`:

```json
[[0, "R", 0], [1, "R", 0], [0, "W", 0], [1, "R", 0]]
```

Run it with `python3 main.py trace.json`. Core indexes are zero-based, operations are `R` or `W`, and addresses are nonnegative integers. Invalid dimensions, malformed records, unreadable files, and malformed JSON produce an error and nonzero exit status.

The same simulator is available as a small Python API:

```python
from coherence import MESISimulator

sim = MESISimulator(cores=2, capacity=4, line_size=16)
states = sim.run([[0, "R", 0], [1, "R", 0], [0, "W", 0]])
print(states)       # ['E', 'S', 'M']
print(sim.report())
```

## Architecture

`main.py` parses command-line options, loads JSON, and renders the report. `coherence.py` owns the simulator state machine, cache capacity policy, counters, and invariant checks. `tests/test_coherence.py` exercises protocol transitions and invalid input using Python's standard-library `unittest` framework.

## Tests

Run offline with `python3 -m unittest discover -s tests -v`. Tests cover shared reads, invalidation, dirty writebacks, capacity eviction, trace shape validation, operation totals, and invalid arguments.

## Roadmap

- Add selectable cache replacement policies while retaining FIFO as the default.
- Add optional per-access transition traces for teaching/debugging.
- Compare MESI behavior with another coherence protocol.

## Contributing

Keep the simulator dependency-free and preserve the documented `python3 main.py` quick start. Add a focused `unittest` case for each behavior change, then run the full command above. Please keep changes confined to this project directory.

## Recent improvements

- Added read/write operation totals to reports and strict rejection of booleans where integer core indexes or addresses are required.
- Added regression tests for operation totals and boolean input validation.
- Previously fixed writeback accounting when a write miss invalidates a modified peer; retained the regression test and known educational-model limitation.