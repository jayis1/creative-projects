# Architecture

This document describes the internal architecture of the Turing machine
simulator.

## Module Overview

```
turing_machine/
├── __init__.py       — Public API exports
├── __main__.py       — python -m turing_machine entry point
├── machine.py        — Core: Tape, Transition, Program, TuringMachine, MultiTapeTM
├── def_parser.py     — Definition language parser (.tm files)
├── machines.py       — Library of classic machines + TagSystem
├── debugger.py       — Step-through debugger with breakpoints
├── analysis.py       — Reachability, dead-state detection, statistics
├── serialization.py  — JSON save/load for machine states
├── universal.py      — Universal Turing Machine (encode/decode/simulate)
├── visualizer.py     — HTML animation, SVG diagram, text/CSV trace
├── composition.py    — Pipeline, Conditional, Loop composition
├── config.py         — JSON/YAML config file loading
└── cli.py            — Command-line interface (12 subcommands)
```

## Core Abstractions

### Tape

The `Tape` class represents a single infinite tape as a lazily-growing
Python list. When the head moves past either end, blank symbols are
prepended or appended. The blank symbol is configurable per tape.

Key design decisions:
- `__slots__` for memory efficiency
- At least one cell always exists (the blank)
- `to_list(strip_blanks=True)` removes leading/trailing blanks
- `render()` produces ASCII art with a `^` head marker

### Transition

A frozen dataclass representing one rule: `(state, read) → (new_state,
write, direction)`. For multi-tape machines, `write` and `direction`
are tuples. The `__post_init__` normalizes directions via
`TMDirection.parse()`.

### Program

A collection of `Transition` objects with O(1) lookup via a dict keyed
by `(state, symbol)`. Wildcard transitions (read symbol `*`) are stored
separately and matched only when no specific rule applies.

### TuringMachine

The main simulator. Supports:
- Single-tape and multi-tape execution
- History recording (opt-in via `record=True`)
- Step-by-step execution (`step()` returns False on halt)
- Reset with optional new tape
- `is_accepted()` for accept/reject semantics

Execution stops when:
1. A halt state is entered, OR
2. No transition applies (implicit reject), OR
3. `max_steps` is exceeded (safety valve)

### MultiTapeTM

Extends `TuringMachine` for n-tape machines. Transitions use tuple
values for read/write/direction. The `_lookup()` method handles
composite keys for multi-tape symbol pairs.

## Universal Turing Machine

The `universal.py` module implements a UTM that can simulate any
single-tape Turing machine:

1. **Encoding**: `encode_machine()` converts a machine + input into a
   string of 0s and 1s using a block-based encoding scheme.
2. **Decoding**: `decode_machine()` reconstructs the program from the
   encoded string.
3. **Simulation**: `UniversalTuringMachine` interprets the encoding to
   reconstruct and run the original machine. `EncodedUTM` operates
   directly on the encoded tape for a true low-level UTM.

## Composition Framework

The `composition.py` module provides high-level constructs:

- **Pipeline**: Run machines sequentially, passing output tape as input
  to the next stage.
- **Conditional**: Branch on a predicate over the tape.
- **Loop**: Repeatedly run a machine until a condition is met.

These enable building complex computations from simple machines.

## Visualizer

Generates visual representations:

- **HTML animation**: Interactive player with play/pause/seek controls
  and a visual tape display with head highlighting.
- **SVG diagram**: State-transition graph with nodes placed on a circle.
- **Text trace**: Formatted table of every execution step.
- **CSV trace**: Machine-readable execution history.

## Config Files

Supports JSON and YAML config files for machine definitions. The format
mirrors the definition language but in a structured, programmatically
generable format.

## Analysis

The analysis module performs static and dynamic analysis:

- **Reachability**: BFS over the state graph from the initial state
- **Dead states**: Reachable states that can never reach a halt
- **Unused states**: States defined but never reachable
- **Tape statistics**: Symbol counts, head position, non-blank count