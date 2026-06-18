# Turing Machine Simulator

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests: 115](https://img.shields.io/badge/tests-115%20passed-brightgreen.svg)
![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-green.svg)

A full-featured Turing machine simulator supporting single-tape and multi-tape
machines, a Universal Turing Machine, a definition language, an interactive
visualizer, a machine composition framework, halting analysis, debugging,
serialization, and a comprehensive CLI.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Python API](#python-api)
- [Definition Language](#definition-language)
- [Universal Turing Machine](#universal-turing-machine)
- [Visualization](#visualization)
- [Machine Composition](#machine-composition)
- [Config Files](#config-files)
- [CLI Reference](#cli-reference)
- [Built-in Machines](#built-in-machines)
- [Architecture](#architecture)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

- **Single-tape and multi-tape machines** — the `MultiTapeTM` class supports n-tape machines with tuple-based transitions
- **Universal Turing Machine** — encode any single-tape machine and simulate it via the UTM
- **Definition language** — declare machines in a human-readable `.tm` file format
- **Config files** — load machines from JSON or YAML configuration files
- **Library of classic machines** — binary incrementer/decrementer, unary adder, palindrome checker, copy machine, busy beaver (BB(2,3,4)), two-tape binary adder
- **Tag system simulator** — a different computational model (Post tag system) for comparison
- **Tape visualization** — ASCII rendering of tape cells with head position marker
- **HTML animations** — interactive step-by-step replay with play/pause/seek controls
- **SVG diagrams** — state-transition graphs rendered as SVG
- **CSV/text traces** — export execution history for analysis
- **Machine composition** — Pipeline, Conditional, and Loop constructs for chaining machines
- **Execution history** — record every step for debugging and analysis
- **Debugger** — step-through debugger with breakpoints, watch states, and trace output
- **Serialization** — save/load complete machine states to JSON
- **Halting analysis** — reachability analysis, dead-state detection, unused-state detection, tape statistics
- **Wildcard transitions** — use `*` as a catch-all symbol for any unmatched read
- **CLI** — 12 subcommands: run, run-file, list, render, check, analyze, save, load, step, visualize, compose, universal, config
- **Pip-installable** — `pip install .` provides the `turing-machine` command
- **Comprehensive test suite** — 115 tests covering all modules

## Installation

```bash
cd turing-machine
pip install .                          # minimal install
pip install ".[dev]"                    # with pytest, pytest-cov, pyyaml
pip install ".[yaml]"                   # just YAML config support
```

**Requirements**: Python 3.10+

## Quick Start

### Python API

```python
from turing_machine import TuringMachine, MultiTapeTM, Debugger, TagSystem
from turing_machine.machines import binary_incrementer, two_tape_adder

# Run a built-in machine
prog = binary_incrementer()
tm = TuringMachine(prog, initial_state="s0", tape=["1","0","1","1"],
                   blank="_", halt_states={"halt"})
tm.run()
print(tm.tapes[0].to_list())  # ['1', '1', '0', '0']  (1011 + 1 = 1100)

# Two-tape binary adder
prog = two_tape_adder()
tm = MultiTapeTM(prog, initial_state="scan", tapes=[["1","0","1"],["1","1"]],
                 blank="_", halt_states={"halt"}, num_tapes=2)
tm.run()
print(tm.tapes[0].to_list())  # ['1', '0', '0', '0']  (101 + 11 = 1000)

# Tag system
ts = TagSystem({"a": "bc", "b": "a", "c": "aaa"}, m=2)
ts.initialize(["a", "a", "a"])
ts.run()
print(ts.tape, ts.steps)  # halts after some steps

# Debugger with breakpoints
prog = binary_incrementer()
tm = TuringMachine(prog, initial_state="s0", tape=["1","0","1","1"],
                   blank="_", halt_states={"halt"})
dbg = Debugger(tm)
dbg.add_breakpoint("add")  # break when entering "add" state
dbg.run()  # runs until breakpoint or halt
print(dbg.status())
```

### Definition Language

Create a `.tm` file:

```
# Binary incrementer
blank: _
start: s0
halt:  halt

s0  0 -> 0 R s0
s0  1 -> 1 R s0
s0  _ -> _ L add
add 0 -> 1 S halt
add 1 -> 0 L add
add _ -> 1 S halt
```

Run it:

```bash
turing-machine run-file examples/binary_incrementer.tm --input 1011
```

## Universal Turing Machine

The UTM can simulate any single-tape Turing machine by encoding it as a
string of 0s and 1s on the tape:

```python
from turing_machine import TuringMachine, encode_machine, simulate
from turing_machine.machines import binary_incrementer

prog = binary_incrementer()
tm = TuringMachine(prog, initial_state="s0", tape=["1","0","1","1"],
                   blank="_", halt_states={"halt"})

# Encode the machine + input
encoded = encode_machine(tm, ["1","0","1","1"])
print(f"Encoded: {encoded}")

# Simulate via UTM — produces identical results
final = simulate(tm, ["1","0","1","1"])
print(f"Final state: {final}")
```

CLI:

```bash
turing-machine universal binary_incrementer --input 1011
```

## Visualization

### HTML Animation

Generate an interactive HTML animation with play/pause/seek controls:

```bash
turing-machine visualize binary_incrementer --input 1011 --format html -o anim.html
```

Open `anim.html` in a browser to see the step-by-step replay.

### SVG State Diagram

```bash
turing-machine visualize binary_incrementer --format svg -o diagram.svg
```

### Text Trace

```bash
turing-machine visualize binary_incrementer --input 1011 --format text
```

Output:
```
 Step  State         Tape                                      Rule
--------------------------------------------------------------------------------
    0  s0            _                                         (s0, _) -> (add, _, L)
    1  add           _                                         (add, _) -> (halt, 1, S)
--------------------------------------------------------------------------------
Final state: halt  Steps: 2  Halted: True
```

### CSV Trace

```bash
turing-machine visualize binary_incrementer --input 1011 --format csv -o trace.csv
```

## Machine Composition

Chain machines together into complex computations:

```python
from turing_machine import Pipeline, Conditional, Loop, compose
from turing_machine.machines import binary_incrementer, binary_decrementer

# Pipeline: run machines sequentially
pipe = Pipeline()
pipe.add(binary_incrementer(), "s0", "halt", "_", "incr1")
pipe.add(binary_incrementer(), "s0", "halt", "_", "incr2")
result = pipe.run(["1", "0", "1"])  # 101 -> 110 -> 111
print(result)  # ['1', '1', '1']

# Conditional: branch on tape contents
cond = Conditional()
cond.set_predicate(lambda tape: 0 if "1" in tape else 1)
cond.add_branch(binary_incrementer(), "s0", "halt", "_", "incr")
cond.add_branch(binary_decrementer(), "s0", "halt", "_", "decr")
result = cond.run(["1", "0", "1"])

# Loop: repeat until condition is met
loop = Loop()
loop.set_machine(binary_incrementer(), "s0", "halt", "_")
loop.set_condition(lambda tape, i: i < 5)
result = loop.run(["0"])  # increment 5 times

# Quick compose helper
pipe = compose(
    (binary_incrementer(), "s0", "halt"),
    (binary_incrementer(), "s0", "halt"),
)
```

CLI:

```bash
turing-machine compose binary_incrementer:s0:halt binary_incrementer:s0:halt --input 101
```

## Config Files

Load machines from JSON or YAML:

```bash
turing-machine config examples/binary_incrementer.json --input 1011
turing-machine config examples/binary_incrementer.yaml --input 1011
```

JSON format:

```json
{
  "name": "binary_incrementer",
  "blank": "_",
  "start": "s0",
  "halt": ["halt"],
  "tapes": 1,
  "transitions": [
    {"state": "s0", "read": "0", "write": "0", "move": "R", "next": "s0"},
    {"state": "s0", "read": "1", "write": "1", "move": "R", "next": "s0"},
    {"state": "s0", "read": "_", "write": "_", "move": "L", "next": "add"},
    {"state": "add", "read": "0", "write": "1", "move": "S", "next": "halt"},
    {"state": "add", "read": "1", "write": "0", "move": "L", "next": "add"},
    {"state": "add", "read": "_", "write": "1", "move": "S", "next": "halt"}
  ]
}
```

## CLI Reference

```bash
# List built-in machines
turing-machine list

# Run a built-in machine
turing-machine run binary_incrementer --input 1011
turing-machine run busy_beaver_4
turing-machine run copy_machine --input 111
turing-machine run binary_decrementer --input 1100

# Step through a machine
turing-machine step binary_incrementer --input 1011 --n 5

# Check if a string is a palindrome
turing-machine check 101    # ACCEPT
turing-machine check 100    # REJECT

# Analyze a machine's structure
turing-machine analyze binary_incrementer --input 1011
turing-machine analyze binary_incrementer --json

# Run a definition file
turing-machine run-file examples/palindrome_checker.tm --input 101

# Save machine state to JSON
turing-machine save binary_incrementer --input 1011 --output state.json

# Load and display saved state
turing-machine load state.json

# Render a tape
turing-machine render --input 10110

# Trace execution (prints each step to stderr)
turing-machine run binary_incrementer --input 1011 --trace

# JSON output
turing-machine run binary_incrementer --input 1011 --json

# Visualize (HTML/SVG/text/CSV)
turing-machine visualize binary_incrementer --input 1011 --format html -o anim.html
turing-machine visualize binary_incrementer --format svg -o diagram.svg
turing-machine visualize binary_incrementer --input 1011 --format text
turing-machine visualize binary_incrementer --input 1011 --format csv -o trace.csv

# Compose machines into a pipeline
turing-machine compose binary_incrementer:s0:halt binary_incrementer:s0:halt --input 101

# Run via Universal Turing Machine
turing-machine universal binary_incrementer --input 1011

# Load and run from config file
turing-machine config examples/binary_incrementer.json --input 1011
turing-machine config examples/binary_incrementer.yaml --input 1011
```

## Built-in Machines

| Machine | Description |
|---------|-------------|
| `binary_incrementer` | Increments a binary number (MSB-first) |
| `binary_decrementer` | Decrements a binary number (MSB-first) |
| `unary_adder` | Adds two unary numbers separated by a blank |
| `palindrome_checker` | Accepts if the tape is a binary palindrome |
| `copy_machine` | Copies a block of 1s: `1^k` → `1^k _ 1^k` |
| `busy_beaver_4` | The 4-state Busy Beaver champion (13 ones, 107 steps) |
| `two_tape_adder` | 2-tape binary adder (tape0 + tape1 → tape0) |

## Definition Language Reference

### Directives

| Directive | Example | Description |
|-----------|---------|-------------|
| `blank:` | `blank: _` | Sets the blank symbol |
| `start:` | `start: s0` | Sets the initial state |
| `halt:` | `halt: halt accept reject` | Sets halt states (space or comma separated) |
| `tapes:` | `tapes: 2` | Number of tapes (for multi-tape machines) |
| `comment:` | `comment: My machine` | Optional description |

### Transitions (single-tape)

```
state  read  ->  write  move  new_state
```

Example: `s0  0 -> 0 R s0`

### Transitions (multi-tape)

```
state  (read1 read2 ...)  ->  (write1 write2 ...)  (move1 move2 ...)  new_state
```

Example: `q0 (0 _) -> (1 0) (R S) q1`

### Comments

Lines starting with `#` or `//` are comments. Inline comments after `#` are also supported.

## Architecture

```
turing-machine/
├── turing_machine/
│   ├── __init__.py       # Public API exports
│   ├── __main__.py       # python -m turing_machine entry point
│   ├── machine.py        # Core: Tape, Transition, Program, TuringMachine, MultiTapeTM
│   ├── def_parser.py     # Definition language parser (.tm files)
│   ├── machines.py       # Library of classic machines + TagSystem
│   ├── debugger.py       # Step-through debugger with breakpoints
│   ├── analysis.py       # Reachability, dead-state detection, statistics
│   ├── serialization.py  # JSON save/load for machine states
│   ├── universal.py       # Universal Turing Machine (encode/decode/simulate)
│   ├── visualizer.py     # HTML animation, SVG diagram, text/CSV trace
│   ├── composition.py    # Pipeline, Conditional, Loop composition
│   ├── config.py         # JSON/YAML config file loading
│   └── cli.py            # Command-line interface (12 subcommands)
├── tests/
│   ├── conftest.py                       # Shared imports
│   ├── test_tape.py                      # Tape and TMDirection tests
│   ├── test_program.py                   # Transition and Program tests
│   ├── test_machines.py                   # Built-in machine tests
│   ├── test_parser.py                     # Definition language parser tests
│   ├── test_serialization_analysis.py     # Serialization, analysis, debugger tests
│   ├── test_universal.py                 # UTM tests
│   └── test_visualizer_composition.py    # Visualizer, composition, config tests
├── examples/
│   ├── binary_incrementer.tm
│   ├── binary_incrementer.json
│   ├── binary_incrementer.yaml
│   ├── binary_decrementer.tm
│   ├── unary_adder.tm
│   ├── palindrome_checker.tm
│   ├── busy_beaver_2.tm
│   ├── binary_not.tm
│   └── unary_multiplier.tm
├── docs/
│   └── architecture.md
├── pyproject.toml
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

See [docs/architecture.md](docs/architecture.md) for a detailed architecture overview.

### How It Works

#### Tapes

Each tape is a Python list that grows lazily. When the head moves past either end, blank symbols are prepended or appended. The blank symbol is configurable per machine.

#### Transitions

A transition is `(current_state, read_symbol) -> (new_state, write_symbol, direction)`. The direction is one of `L` (left), `R` (right), or `S` (stay). For multi-tape machines, `read`, `write`, and `direction` are tuples.

#### Programs

A `Program` is a collection of transitions with O(1) lookup. Wildcard transitions (read symbol `*`) are matched only when no specific rule applies for the current `(state, symbol)` pair.

#### Execution

A machine runs until:
1. It enters a halt state (default: `halt`, `accept`, `reject`, `HALT`, `H`), or
2. No transition applies for the current `(state, symbol)` pair (implicit reject), or
3. `max_steps` is exceeded (safety valve, default 1,000,000).

#### Universal Turing Machine

The UTM encodes a machine's transition table as blocks of 1s separated by 0s. Each transition `(q, a) → (q', b, d)` becomes `1^(q+1) 0 1^(a+1) 0 1^(b+1) 0 1^(d) 0 1^(q'+1)`. Transitions are separated by `00` and the rules/input by `000`.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=turing_machine --cov-report=term-missing

# Run a single test file
pytest tests/test_machines.py -v
```

The test suite covers:
- Tape operations (read, write, move, grow, render, copy)
- Transition and Program (lookup, wildcard, states, symbols)
- All built-in machines (correctness of algorithms)
- Definition language parser (directives, transitions, multi-tape, errors)
- Serialization (tape, program, machine roundtrips, file I/O)
- Analysis (reachability, dead states, unused states, statistics)
- Debugger (breakpoints, conditional breakpoints, watch, step, reset)
- Universal Turing Machine (encoding, decoding, simulation)
- Visualizer (text trace, HTML, SVG, CSV)
- Composition (pipeline, conditional, loop, compose helper)
- Config files (JSON/YAML loading, saving, error handling)

## Known Issues (Resolved)

All bugs found during development and bug-hunt phases have been fixed:

1. **`reset()` lost multi-tape configuration** — Calling `reset()` on a multi-tape machine would create only a single tape instead of preserving the `num_tapes` count. Fixed by checking `self.num_tapes` and creating the correct number of tapes.

2. **`is_accepted()` returned True for implicit rejects** — A machine that halted because no transition was found (implicit reject) would incorrectly report `is_accepted() == True`. Fixed to only return True for explicit accept/halt states.

3. **`Tape.to_list()` returned empty list for empty tape** — When a `Tape` was initialized with an empty list `[]`, `to_list()` would return `[]` instead of `["_"]`. Fixed by ensuring at least one cell (the blank) is always present.

4. **`Tape.__init__` with empty list** — `Tape("_", [])` would create a tape with zero cells. Fixed by initializing with `[blank]` when the input list is empty.

5. **`encode_machine()` crashed on tuple directions** — Multi-tape machines have tuple directions like `(L, R)`, but `encode_machine()` tried to look up `str(t.direction)`. Fixed by extracting the first element of tuple directions.

6. **`TagSystem.run()` history always populated** — The `step()` method unconditionally appended to `history`, ignoring the `record` parameter. Fixed by adding a `_recording` flag.

7. **`Transition` state field confusion** — The original `Transition` dataclass used `state` as both the current state and the new state. Fixed by adding an explicit `new_state` field.

8. **Binary incrementer algorithm** — The original incrementer wrote a `1` at the blank after the number and then carried. Fixed with a proper scan-right-then-add-with-carry algorithm.

9. **Copy machine looped infinitely** — The copy machine didn't track the separator between original and copied blocks. Fixed with a proper separator-aware algorithm.

10. **Busy Beaver BB(4) table was wrong** — The original BB(4) transition table was incomplete. Fixed with the verified champion table.

11. **UTM encoding ambiguity** — The original "111" separator could appear within rule encodings. Fixed by using "000" as the separator (cannot appear within valid rules).

## Roadmap

- [ ] **Interactive REPL** — a shell-like interface for exploratory machine building
- [ ] **2D cellular automata** — extend the framework to 2D tape structures
- [ ] **Nondeterministic TMs** — support for nondeterministic transitions with backtracking
- [ ] **Performance mode** — compiled/cached transitions for high-step-count machines
- [ ] **More built-in machines** — binary multiplier, sorting networks, prime sieve
- [ ] **Web playground** — a browser-based interface using PyScript
- [ ] **Export to LaTeX** — generate LaTeX diagrams for academic papers
- [ ] **Benchmarking suite** — compare step counts across machine implementations

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and guidelines for adding new machines.

## Changelog

### v3.0.0 (2026-06-18) — Comprehensive Improvement

- **Added Universal Turing Machine** (`universal.py`) with encoding, decoding, and simulation
- **Added visualizer** (`visualizer.py`) with HTML animation, SVG diagram, text trace, and CSV export
- **Added machine composition** (`composition.py`) with Pipeline, Conditional, and Loop
- **Added config file support** (`config.py`) for JSON and YAML machine definitions
- **Added 4 new CLI subcommands**: visualize, compose, universal, config
- **Added comprehensive test suite** — 115 tests across 7 test files
- **Added GitHub Actions CI** with multi-version Python testing
- **Added CONTRIBUTING.md** and **LICENSE**
- **Added docs/architecture.md** with detailed module documentation
- **Added example files**: JSON/YAML configs, busy_beaver_2.tm, binary_not.tm, unary_multiplier.tm
- **Updated pyproject.toml** with full metadata, optional dependencies, and pytest config
- **Bumped version** from 2.0.0 to 3.0.0

### v2.0.0 — Enhancement Phase

- Added step-through debugger with breakpoints and watch states
- Added JSON serialization (save/load machine states)
- Added halting analysis (reachability, dead-state detection, tape statistics)
- Added tag system simulator
- Added two-tape binary adder
- Added 4 new CLI subcommands (analyze, save, load, step)
- Fixed 10 bugs from the initial implementation

### v1.0.0 — Initial Release

- Single-tape and multi-tape Turing machines
- Definition language parser
- Library of 6 classic machines
- Tape visualization
- CLI with 5 subcommands

## License

MIT