# Turing Machine Simulator

A Turing machine simulator with multi-tape support, a definition language, a library of classic machines, tape visualization, and a command-line interface.

## Features

- **Single-tape and multi-tape machines** — the `MultiTapeTM` class supports n-tape machines with tuple-based transitions
- **Definition language** — declare machines in a human-readable `.tm` file format with directives and transition rules
- **Library of classic machines** — binary incrementer, unary adder, palindrome checker, copy machine, busy beaver (BB(4))
- **Tape visualization** — ASCII rendering of tape cells with head position marker
- **Execution history** — record every step for debugging and analysis
- **Wildcard transitions** — use `*` as a catch-all symbol for any unmatched read
- **CLI** — run built-in machines, run definition files, list machines, check palindromes, render tapes
- **Pip-installable** — `pip install .` provides the `turing-machine` command

## Installation

```bash
cd turing-machine
pip install .
```

## Quick Start

### Python API

```python
from turing_machine import TuringMachine, Program, TMDirection as D
from turing_machine.machines import binary_incrementer

# Run a built-in machine
prog = binary_incrementer()
tm = TuringMachine(prog, initial_state="s0", tape=["1","0","1","1"],
                   blank="_", halt_states={"halt"})
tm.run()
print(tm.tapes[0].to_list())  # ['1', '1', '0', '0']  (1011 + 1 = 1100)
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

# Check if a string is a palindrome
turing-machine check 101    # ACCEPT
turing-machine check 100    # REJECT

# Run a definition file
turing-machine run-file examples/palindrome_checker.tm --input 101

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

## Built-in Machines

| Machine | Description |
|---------|-------------|
| `binary_incrementer` | Increments a binary number (MSB-first) |
| `unary_adder` | Adds two unary numbers separated by a blank |
| `palindrome_checker` | Accepts if the tape is a binary palindrome |
| `copy_machine` | Copies a block of 1s: `1^k` → `1^k _ 1^k` |
| `busy_beaver_4` | The 4-state Busy Beaver champion (13 ones, 107 steps) |

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
│   ├── machines.py      # Library of classic machines
│   ├── cli.py           # Command-line interface
│   └── __main__.py      # python -m turing_machine entry point
├── examples/
│   ├── binary_incrementer.tm
│   ├── unary_adder.tm
│   └── palindrome_checker.tm
├── pyproject.toml
└── README.md
```

## License

MIT