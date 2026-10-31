# Cache Coherence Lab

A dependency-free, trace-driven MESI protocol simulator makes multicore cache behavior visible: run a tiny workload and inspect line states, invalidations, dirty writebacks, and misses. Unlike a generic cache model, it checks coherence invariants after every operation.

## Features and how it works

Private bounded caches share a snooping bus. Byte addresses map to line tags; reads acquire Exclusive (E) when no peer has a copy and Shared (S) when they do. Writes acquire Modified (M) and invalidate peer copies. A deterministic FIFO-by-insertion policy bounds each cache; dirty evictions and modified-owner read sharing count writebacks. Invariants are checked after every operation.

Trace records are JSON arrays `[core, operation, byte_address]`. Malformed records, invalid core/op/address, invalid simulator dimensions, unreadable files, and malformed JSON fail with a concise error and nonzero status.

## Usage

```sh
python3 main.py
python3 main.py trace.json --cores 2 --capacity 4 --line-size 16
python3 -m unittest discover -s tests -v
```

Example trace: `[[0,"R",0],[1,"R",0],[0,"W",0],[1,"R",0]]`. The CLI prints JSON statistics and each core's final cache lines. The Python API is `MESISimulator(cores=2, capacity=4, line_size=16).run(records)`.

## Tests

The standard-library suite covers read sharing, writer invalidation, dirty eviction, malformed record shapes, and rejected access arguments.

## Known Issues (Resolved)

- A write miss that invalidated another core's Modified line failed to count its required dirty intervention/writeback. The `test_writer_invalidating_modified_peer_counts_writeback` test reproduced a zero count before the fix; the write-miss invalidation path now records it.

No other reproducible defects were found in this review. The implementation is an educational simplified snooping model, not a cycle-accurate hardware simulator.
