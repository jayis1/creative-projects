# Turing Machine Simulator

A Turing machine simulator with multi-tape support, a definition language, a library of classic machines, tape visualization, debugging, serialization, halting analysis, and a command-line interface.

## Features

- **Single-tape and multi-tape machines** — the `MultiTapeTM` class supports n-tape machines with tuple-based transitions
- **Definition language** — declare machines in a human-readable `.tm` file format with directives and transition rules
- **Library of classic machines** — binary incrementer, binary decrementer, unary adder, palindrome checker, copy machine, busy beaver (BB(4)), two-tape binary adder
- **Tag system simulator** — a different computational model (Post tag system) for comparison
- **Tape visualization** — ASCII rendering of tape cells with head position marker
- **Execution history** — record every step for debugging and analysis
- **Debugger** — step-through debugger with breakpoints, watch states, and trace output
- **Serialization** — save/load complete machine states to JSON
- **Halting analysis** — reachability analysis, dead-state detection, unused-state detection, tape statistics
- **Wildcard transitions** — use `*` as a catch-all symbol for any unmatched read
- **CLI** — 8 subcommands: run, run-file, list, render, check, analyze, save, load, step
- **Pip-installable** — `pip install .` provides the `turing-machine` command

## Installation

```bash
cd turing-machine
pip install .
```

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

### CLI

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
```

## How It Works

### Tapes

Each tape is a Python list that grows lazily. When the head moves past either end, blank symbols are prepended or appended. The blank symbol is configurable per machine.

### Transitions

A transition is `(current_state, read_symbol) -> (new_state, write_symbol, direction)`. The direction is one of `L` (left), `R` (right), or `S` (stay). For multi-tape machines, `read`, `write`, and `direction` are tuples.

### Programs

A `Program` is a collection of transitions with O(1) lookup. Wildcard transitions (read symbol `*`) are matched only when no specific rule applies for the current `(state, symbol)` pair.

### Execution

A machine runs until:
1. It enters a halt state (default: `halt`, `accept`, `reject`, `HALT`, `H`), or
2. No transition applies for the current `(state, symbol)` pair (implicit reject), or
3. `max_steps` is exceeded (safety valve, default 1,000,000).

### Debugger

The `Debugger` class wraps a `TuringMachine` and provides:
- **Breakpoints**: stop when a specific state is entered
- **Conditional breakpoints**: stop when a predicate over machine state is true
- **Watch states**: print a message when a state is entered
- **Trace**: record every step for later inspection
- **Step/run/continue**: granular control over execution

### Serialization

Machines can be serialized to JSON including the full program, tape contents, head positions, current state, step count, and halt status. Use `save_machine()` / `load_machine()` for file-based persistence, or `serialize_machine()` / `deserialize_machine()` for in-memory roundtrips.

### Analysis

The analysis module provides:
- `reachable_states()`: states reachable from the initial state via BFS
- `dead_states()`: reachable states that can never reach a halt state
- `unused_states()`: states defined in the program but never reachable
- `analyze_machine()`: comprehensive analysis dict with all of the above
- `tape_statistics()`: symbol counts, head position, non-blank count

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

## Project Structure

```
turing-machine/
├── turing_machine/
│   ├── __init__.py      # Public API
│   ├── machine.py       # Tape, Transition, Program, TuringMachine, MultiTapeTM
│   ├── def_parser.py    # Definition language parser
│   ├── machines.py      # Library of classic machines + TagSystem
│   ├── debugger.py      # Step-through debugger with breakpoints
│   ├── serialization.py # JSON save/load for machine states
│   ├── analysis.py      # Reachability, dead-state detection, statistics
│   ├── cli.py           # Command-line interface (8 subcommands)
│   └── __main__.py      # python -m turing_machine entry point
├── examples/
│   ├── binary_incrementer.tm
│   ├── binary_decrementer.tm
│   ├── unary_adder.tm
│   └── palindrome_checker.tm
├── pyproject.toml
└── README.md
```

## License

MIT