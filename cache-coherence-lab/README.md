# Cache Coherence Lab

A dependency-free, trace-driven MESI protocol simulator makes multicore cache behavior visible: run a tiny workload and inspect line states, invalidations, dirty writebacks, and misses. Unlike a generic cache model, it checks coherence invariants after every operation.

## How it works

The simulator models private bounded caches connected by a snooping bus. Byte addresses map to cache-line tags. Reads acquire Exclusive (E) when no peer has the line and Shared (S) when a peer does; writes acquire Modified (M) and invalidate peer copies. A deterministic FIFO-by-insertion policy bounds each cache. Dirty evictions count as writebacks.

## Usage

Run the built-in demonstration:

```sh
python3 main.py
```

Run a JSON trace, where records are `[core, operation, byte_address]`:

```sh
printf '[[0,"R",0],[1,"R",0],[0,"W",0]]' > /tmp/trace.json
python3 main.py /tmp/trace.json --cores 2 --capacity 4 --line-size 16
```

The CLI prints JSON statistics and final cache contents. The Python API is `MESISimulator(...).run(records)`; run tests with `python3 -m unittest discover -s tests -v`.

Planned enhancement: explicit trace parsing validation and additional protocol diagnostics.
