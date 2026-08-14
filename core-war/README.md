# ⚔️ Core War — MARS Redcode Simulator

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 162](https://img.shields.io/badge/tests-162%20passing-brightgreen.svg)](#tests)
[![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-blue.svg)](#changelog)

> A full implementation of Core War, the classic programming game where assembly-like programs ("warriors") battle for control of a virtual computer's memory. Implements the **ICWS'94 standard** with a complete MARS (Memory Array Redcode Simulator), Redcode parser, battle scheduler, tournament system, strategy analyzer, battle replay, and genetic algorithm for evolving warriors.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Writing Warriors](#writing-warriors)
- [Strategy Analysis](#strategy-analysis)
- [Battle Recording & Replay](#battle-recording--replay)
- [Genetic Evolution](#genetic-evolution)
- [Configuration](#configuration)
- [Built-in Warriors](#built-in-warriors)
- [Architecture](#architecture)
- [Instruction Set](#instruction-set-icws94)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core Engine
- **Full ICWS'94 instruction set**: 16 opcodes, 7 modifiers, 8 addressing modes
- **Redcode parser**: Labels, EQU constants, ORG/END pseudo-ops, arithmetic expressions, case-insensitive
- **MARS virtual machine**: Circular memory, round-robin process scheduling, SPL multi-process support
- **Step-through mode**: Execute one cycle at a time for debugging
- **Execution trace**: Optional trace recording for analysis
- **Access tracking**: Per-address execution count for heatmaps
- **Event hooks**: `on_execute` callback for real-time observation

### Battle Management
- **Battle scheduler**: Multi-round battles with randomized positions
- **Tournament system**: Round-robin between all warriors with standings
- **Score tracking**: 3 points per win, 1 per draw, 0 per loss

### Analysis & Visualization
- **Strategy analyzer**: Classifies warriors as Bomber, Scanner, Replicator, Imp, etc.
- **Vulnerability detection**: Identifies weaknesses and suggests improvements
- **Aggressiveness/resilience ratings**: 0-10 scale for each warrior
- **Core memory visualization**: Heatmap, opcode frequency summary, battle log
- **Disassembler**: Convert core instructions back to Redcode text

### Advanced Features (v3.0)
- **Battle recording & replay**: Record battles as JSON, replay cycle-by-cycle
- **Genetic evolution**: Automatically evolve warriors using a genetic algorithm
- **Configuration files**: YAML/JSON config for battles and tournaments
- **Structured logging**: Configurable log levels with file output
- **9 CLI subcommands**: battle, tournament, trace, dump, core-dump, step, validate, analyze, evolve

---

## Installation

### From Source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/core-war

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dependencies
pip install -e ".[dev]"
pip install pyyaml
```

### Requirements

- Python 3.10+
- PyYAML (for config file support)
- pytest (for running tests, included in `[dev]` extras)

### Verify Installation

```bash
# Run the test suite
python3 -m pytest tests/ -v

# Validate a warrior
python3 -m core_war.cli validate warriors/dwarf.red

# Run a quick battle
python3 -m core_war.cli --core-size 100 --max-cycles 50 battle warriors/imp.red warriors/dwarf.red
```

---

## Quick Start

### CLI

```bash
# Battle between two warriors (10 rounds)
python3 -m core_war.cli --rounds 10 battle warriors/imp.red warriors/dwarf.red

# Round-robin tournament with 5 warriors
python3 -m core_war.cli --rounds 5 tournament warriors/imp.red warriors/dwarf.red warriors/stone.red warriors/paper.red warriors/scanner.red

# Analyze a warrior's strategy
python3 -m core_war.cli analyze warriors/dwarf.red

# Step through a battle 10 cycles at a time
python3 -m core_war.cli --max-cycles 100 step warriors/imp.red warriors/dwarf.red --steps 10

# Record a battle and save to file
python3 -m core_war.cli --max-cycles 500 replay warriors/imp.red warriors/dwarf.red --record --replay-file battle.json

# Replay a recorded battle
python3 -m core_war.cli replay --replay-file battle.json

# Evolve warriors with a genetic algorithm
python3 -m core_war.cli evolve --opponents warriors/dwarf.red warriors/stone.red --generations 10 --population 20 --output warriors/evolved.red
```

### Python API

```python
from core_war import (
    load_warrior, MARS, BattleScheduler, StrategyAnalyzer,
    BattleRecorder, BattleReplay, BattleConfig, GeneticEvolver,
)

# Load warriors
imp = load_warrior("warriors/imp.red")
dwarf = load_warrior("warriors/dwarf.red")

# Run a single battle
mars = MARS(core_size=8000, max_cycles=80000, seed=42)
mars.reset()
mars.load_warrior(imp)
mars.load_warrior(dwarf)
result = mars.run()
print(f"Winner: {result.winner}, Cycles: {result.cycles}")

# Run a tournament
warriors = [load_warrior(f"warriors/{n}.red") for n in ["imp", "dwarf", "stone", "paper"]]
scheduler = BattleScheduler(rounds=10, seed=42)
result = scheduler.run_tournament(warriors)
for rank, stat in enumerate(result.standings, 1):
    print(f"#{rank} {stat.name}: {stat.wins}W {stat.losses}L {stat.draws}D (score={stat.score:.0f})")

# Analyze warrior strategy
analyzer = StrategyAnalyzer()
analysis = analyzer.analyze(dwarf)
print(f"Strategy: {analysis.strategy.value}")
print(f"Aggressiveness: {analysis.estimated_aggressiveness}/10")
print(f"Resilience: {analysis.estimated_resilience}/10")

# Record and replay a battle
recorder = BattleRecorder()
mars = MARS(core_size=1000, max_cycles=500, seed=42)
recording = recorder.record(mars, [imp, dwarf])
recording.save("battle.json")

# Load and replay
loaded = type(recording).from_file("battle.json")
replay = BattleReplay(loaded)
for snapshot in replay.play():
    print(f"Cycle {snapshot.cycle}: {snapshot.alive_warriors}")
```

---

## CLI Reference

```
core-war — MARS simulator for Redcode warriors

Global Options:
  --core-size N       Core memory size (default: 8000)
  --max-cycles N      Max cycles per round (default: 80000)
  --seed N            Random seed for reproducibility
  --rounds N          Number of rounds (default: 10)
  --config PATH       Load settings from YAML/JSON config file
  --log-level LEVEL   Logging level (DEBUG, INFO, WARNING, ERROR)
  --log-file PATH     Log file path
  --output-format F   Output format: table, json, csv
  --version           Show version

Commands:
  battle     <warriors...>           Run a multi-round battle
  tournament <warriors...>           Run a round-robin tournament
  trace      <warrior>               Trace single warrior execution
  dump       <warrior>               Dump parsed instructions
  core-dump  <warriors...>           Show final core memory state
  step       <warriors...>           Step through a battle
  validate   <warrior>               Validate a warrior file
  analyze    <warrior>               Analyze strategy & vulnerabilities
  replay     [warriors...]           Record/replay battles
  evolve     [options]               Evolve warriors (genetic algorithm)
  config     <output>                Create template config file
```

### Example: Analyze Output

```
============================================================
  WARRIOR ANALYSIS: dwarf
============================================================

  Strategy:          Bomber
  Secondary:         Stone
  Instructions:      4
  Start offset:      0
  Has SPL:           False
  Has JMP:           True
  Scanning:          False
  Bombing:           True
  Replication:       False
  Self-modifying:    True
  Uses indirect:     True
  Process estimate:  1

  Aggressiveness:    6/10
  Resilience:        3/10

  Opcode frequency:
    ADD     1 ( 25.0%) █████
    MOV     1 ( 25.0%) █████
    JMP     1 ( 25.0%) █████
    DAT     1 ( 25.0%) █████

  Vulnerabilities (3):
    🔵 [LOW] Single-process warrior — vulnerable to single DAT hit
    🟡 [MEDIUM] Self-modifying code without process redundancy
    ℹ️ [INFO] Entry point at first instruction — predictable start location

  Summary: dwarf: Bomber with Stone elements (4 instructions) aggression=6/10 resilience=3/10 (3 vulnerabilities)
============================================================
```

---

## Python API

### Core Classes

```python
from core_war import MARS, BattleScheduler, StrategyAnalyzer
from core_war import BattleRecorder, BattleReplay, GeneticEvolver
from core_war import BattleConfig, load_warrior, load_warrior_from_string
```

### MARS (Virtual Machine)

```python
mars = MARS(core_size=8000, max_cycles=80000, max_processes=8000, seed=42)
mars.reset()
mars.load_warrior(warrior, position=None)  # None = random position

# Full run
result = mars.run()  # → BattleResult

# Step-by-step
while mars.step():
    alive = [w.name for w in mars.warriors if w.alive]
    print(f"Cycle {mars.cycle}: {alive}")

# Enable trace
mars.trace_enabled = True
mars.run()
for entry in mars.trace[:10]:
    print(f"  {entry['warrior']} PC={entry['pc']}: {entry['instruction']}")

# Event hook
mars.on_execute = lambda name, pc, instr: print(f"{name} @ {pc}: {instr}")
```

### Strategy Analyzer

```python
analyzer = StrategyAnalyzer()
result = analyzer.analyze(warrior)

print(result.strategy.value)          # "Bomber"
print(result.estimated_aggressiveness) # 6
print(result.estimated_resilience)     # 3

for v in result.vulnerabilities:
    print(f"  [{v.severity}] {v.description}")

# Compare two warriors
comparison = analyzer.compare(warrior1, warrior2)
print(comparison["predicted_winner"])
```

### Battle Recording & Replay

```python
# Record
recorder = BattleRecorder(max_snapshots=10000)
mars = MARS(core_size=8000, max_cycles=80000, seed=42)
recording = recorder.record(mars, [imp, dwarf])
recording.save("battle.json")

# Replay
from core_war import BattleRecording
recording = BattleRecording.from_file("battle.json")
replay = BattleReplay(recording)

for snapshot in replay.play():
    print(f"Cycle {snapshot.cycle}: alive={snapshot.alive_warriors}")

# Get core state at any cycle
core_at_100 = replay.get_core_at(100)
```

### Genetic Evolution

```python
from core_war import GeneticEvolver, load_warrior

opponents = [load_warrior("warriors/dwarf.red")]
seeds = [load_warrior("warriors/imp.red")]

evolver = GeneticEvolver(
    population_size=20,
    generations=10,
    opponents=opponents,
    core_size=8000,
    max_cycles=5000,
    mutation_rate=0.15,
    seed=42,
)

best = evolver.evolve(seed_warriors=seeds)
print(f"Best: {best.name}, fitness={best.fitness:.1f}")
print(f"Win rate: {best.win_rate:.1%}")

# Save evolved warrior
evolver.save_best("warriors/evolved.red")
```

### Configuration

```python
from core_war import BattleConfig

# Create from code
config = BattleConfig(core_size=8000, max_cycles=80000, rounds=10, seed=42)

# Load from file
config = BattleConfig.from_file("config.yaml")

# Save to file
config.save("my_config.json")

# Use with scheduler
scheduler = BattleScheduler(
    core_size=config.core_size,
    max_cycles=config.max_cycles,
    rounds=config.rounds,
    seed=config.seed,
)
```

---

## Writing Warriors

Warriors are written in Redcode, saved as `.red` files:

```redcode
; My Warrior — A comment
        ORG     start       ; Entry point

step    EQU     4           ; Constant definition

start   ADD     #step, bomb ; Increment bomb pointer
        MOV     bomb, @bomb ; Drop bomb at pointer
        JMP     start       ; Loop back
bomb    DAT     #0, #0      ; The bomb
```

### Redcode Syntax

| Element | Syntax | Description |
|---------|--------|-------------|
| Comments | `; text` | Everything after `;` is ignored |
| Labels | `name` | Start with letter, alphanumeric + underscore |
| Constants | `name EQU value` | Substituted in expressions |
| ORG | `ORG label` | Set entry point |
| END | `END [label]` | End of source (optional entry point) |
| Expressions | `2+3`, `label-1` | Arithmetic in operands |

### Addressing Mode Symbols

| Symbol | Mode | Description |
|--------|------|-------------|
| `#` | Immediate | Use value directly |
| `$` | Direct | Relative to current instruction (default) |
| `@` | Indirect-B | Indirect via B-field pointer |
| `*` | Indirect-A | Indirect via A-field pointer |
| `{` | Predec-B | Predecrement B-field, then indirect |
| `<` | Predec-A | Predecrement A-field, then indirect |
| `}` | Postinc-B | Indirect via B, then increment |
| `>` | Postinc-A | Indirect via A, then increment |

---

## Strategy Analysis

The strategy analyzer classifies warriors into strategy types:

| Strategy | Description |
|----------|-------------|
| **Bomber** | Drops DAT bombs throughout core |
| **Scanner** | Scans core for enemy code and attacks |
| **Replicator** | Copies itself to multiple locations |
| **Imp** | Self-replicating forward-copier |
| **Vampire** | Steals enemy processes via JMP |
| **One-Shot** | Attempts a quick kill then dies |
| **Silk** | Fast replicator that spreads quickly |
| **Stone** | Compact bomber (3-5 instructions) |
| **Hybrid** | Combines multiple strategies |

Each warrior receives:
- **Aggressiveness** (0-10): How offensive the warrior is
- **Resilience** (0-10): How hard to kill
- **Vulnerability list**: Identified weaknesses with recommendations

---

## Battle Recording & Replay

The replay system records per-cycle state snapshots:

```python
# Record a battle
recorder = BattleRecorder(max_snapshots=10000)
recording = recorder.record(mars, [warrior1, warrior2])

# Save to JSON
recording.save("battle.json")

# Load and replay
recording = BattleRecording.from_file("battle.json")
replay = BattleReplay(recording)

# Iterate through cycles
for snapshot in replay.play():
    print(f"Cycle {snapshot.cycle}: {snapshot.alive_warriors}")

# Reconstruct core at any point
core = replay.get_core_at(500)
```

---

## Genetic Evolution

The genetic evolver automatically creates warriors through evolutionary computation:

```python
evolver = GeneticEvolver(
    population_size=20,
    generations=10,
    opponents=[load_warrior("warriors/dwarf.red")],
    mutation_rate=0.15,
    seed=42,
)

best = evolver.evolve(seed_warriors=[load_warrior("warriors/imp.red")])
print(f"Best warrior: {best.name} (fitness={best.fitness:.1f})")
evolver.save_best("warriors/evolved.red")
```

**How it works:**
1. Initialize population (seed warriors + random individuals)
2. Evaluate fitness (battle against opponents, score = 3×wins + draws)
3. Select survivors (tournament selection + elitism)
4. Create children (crossover + mutation)
5. Repeat for N generations

**Mutation operations:**
- Point mutation (change opcode, modifier, mode, or value)
- Instruction swap, insertion, deletion

---

## Configuration

Create a config file:

```bash
python3 -m core_war.cli config my_config.yaml
```

Example `config.yaml`:

```yaml
core_size: 8000
max_cycles: 80000
rounds: 10
seed: 42
warriors:
  - warriors/imp.red
  - warriors/dwarf.red
  - warriors/stone.red
log_level: INFO
output_format: table
```

Use the config:

```bash
python3 -m core_war.cli --config my_config.yaml battle
```

---

## Built-in Warriors

| Warrior | Type | Strategy | Aggr. | Resil. | Description |
|---------|------|----------|-------|--------|-------------|
| **Imp** | Replicator | Imp | 1/10 | 4/10 | Copies itself forward each cycle. Nearly unkillable but can't kill. |
| **Imp-Spiral** | Replicator | Imp | 2/10 | 6/10 | Uses SPL to create multiple imp processes. Harder to kill. |
| **Dwarf** | Bomber | Bomber/Stone | 6/10 | 3/10 | Drops DAT bombs at regular intervals. Classic beginner warrior. |
| **Stone** | Bomber | Bomber/Stone | 7/10 | 3/10 | Compact bomber using indirect addressing. |
| **Paper** | Replicator | Replicator | 4/10 | 9/10 | Copies itself to new locations and splits. Spreads exponentially. |
| **Scanner** | Hunter | Scanner/Bomber | 10/10 | 2/10 | Scans core for non-empty cells and bombs them. |
| **Kamikaze** | Bomber | One-Shot | 8/10 | 1/10 | Aggressive bomber that self-destructs after dropping all bombs. |

---

## Architecture

```
core-war/
├── core_war/
│   ├── __init__.py             # Package exports (v3.0.0)
│   ├── opcodes.py              # Opcode, Modifier, AddressMode enums
│   ├── instruction.py          # Instruction dataclass (core memory cell)
│   ├── parser.py               # Redcode parser (labels, EQU, ORG, expressions)
│   ├── mars.py                 # MARS virtual machine (execution engine)
│   ├── scheduler.py            # Battle scheduler (multi-round, tournaments)
│   ├── disassembler.py         # Disassembler (instruction → Redcode text)
│   ├── visualizer.py           # Core memory heatmap, summary, battle log
│   ├── loader.py               # Warrior file loading utilities
│   ├── config.py               # Configuration management (YAML/JSON)
│   ├── logging_config.py       # Structured logging setup
│   ├── strategy_analyzer.py    # Warrior strategy analysis & classification
│   ├── replay.py               # Battle recording and replay system
│   ├── mutator.py              # Genetic algorithm for warrior evolution
│   └── cli.py                  # CLI interface (9 subcommands)
├── warriors/                   # 7 built-in warrior files
├── examples/                   # 4 example scripts
├── tests/                      # 162 tests (95 original + 67 new)
├── docs/                       # Architecture documentation
├── .github/workflows/          # CI configuration (GitHub Actions)
├── config.yaml                 # Example config file
├── pyproject.toml              # Package configuration (v3.0.0)
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT license
└── README.md                   # This file
```

See [docs/architecture.md](docs/architecture.md) for detailed module dependency diagrams and data flow.

---

## Instruction Set (ICWS'94)

| Opcode | Description |
|--------|-------------|
| `DAT`  | Data / terminate process |
| `MOV`  | Copy instruction |
| `ADD`  | Add |
| `SUB`  | Subtract |
| `MUL`  | Multiply |
| `DIV`  | Divide |
| `MOD`  | Modulo |
| `JMP`  | Jump |
| `JMZ`  | Jump if zero |
| `JMN`  | Jump if non-zero |
| `DJN`  | Decrement and jump if non-zero |
| `SPL`  | Split into new process |
| `CMP`/`SEQ` | Skip if equal |
| `SNE`  | Skip if not equal |
| `SLT`  | Skip if less than |
| `NOP`  | No operation |

**Modifiers**: `.A`, `.B`, `.AB`, `.BA`, `.F`, `.X`, `.I` — specify which fields an opcode operates on.

**Addressing Modes**: `#` (immediate), `$` (direct), `@` (indirect via B), `*` (indirect via A), `{` (predec B), `<` (predec A), `}` (postinc B), `>` (postinc A).

---

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `core_size` | 8000 | Size of circular memory array |
| `max_cycles` | 80000 | Cycles before draw is declared |
| `max_processes` | 8000 | Max processes per warrior |
| `min_separation` | 100 | Min distance between warrior load positions |
| `rounds` | 10 | Number of rounds per battle |
| `seed` | None | Random seed for reproducibility |

---

## Known Issues (Resolved)

The following bugs were found and fixed during the bug hunt phase:

1. **Label named "end" treated as END pseudo-op** — Labels matching pseudo-op names (like `end`) were incorrectly skipped. Fixed by checking if the token following `END` is an opcode.

2. **Immediate addressing in comparisons (SEQ/SNE/SLT)** — When using immediate addressing mode (`#`), comparison instructions compared the instruction against itself. Fixed by adding `_compare_with_modes` and `_compare_less_with_modes` methods.

3. **Immediate addressing in conditional jumps (JMZ/JMN/DJN)** — Same issue as comparisons. Fixed by special-casing immediate mode to use operand value directly.

4. **Dead code in `_execute_instruction`** — Four unused variable assignments removed.

5. **`_safe_eval` security** — Verified character filter rejects code injection. Added test.

6. **Division by zero in expressions** — Verified `ParseError` is raised. Added test.

7. **DIV/MOD by zero in opcodes** — Verified returns 0 instead of crashing. Added test.

8. **Warrior loading wrap-around** — Verified correct; fixed test expectations.

9. **SPL at max processes** — Verified no crash; added test.

10. **Arithmetic overflow wrapping** — Verified all arithmetic wraps via mod core_size; added tests.

---

## Changelog

### v3.0.0 (Comprehensive Improvement)

**New Modules:**
- `config.py` — Configuration management (YAML/JSON, validation, templates)
- `logging_config.py` — Structured logging with configurable levels
- `strategy_analyzer.py` — Warrior strategy classification and vulnerability detection
- `replay.py` — Battle recording (per-cycle snapshots) and replay system
- `mutator.py` — Genetic algorithm for evolving warriors (mutation, crossover, selection)

**New CLI Commands:**
- `analyze` — Analyze warrior strategy, vulnerabilities, and metrics
- `replay` — Record battles to JSON and replay them
- `evolve` — Evolve warriors using a genetic algorithm
- `config` — Create template configuration files

**Enhancements:**
- CLI now supports `--config` flag to load settings from YAML/JSON
- CLI supports `--output-format` (table, json, csv)
- CLI supports `--log-level` and `--log-file` for structured logging
- `Instruction` class: added `is_dat_zero()` and `pack()` methods
- Type hints added throughout new code
- `from __future__ import annotations` for forward compatibility
- pyproject.toml updated with dependencies, optional deps, classifiers, URLs

**Testing:**
- 67 new tests added (162 total, all passing)
- Tests cover config, strategy analyzer, replay, genetic evolution, CLI, enhanced instruction

**Infrastructure:**
- GitHub Actions CI workflow (Python 3.10-3.13, coverage, CLI testing)
- CONTRIBUTING.md with development guidelines
- LICENSE file (MIT)
- config.yaml example file
- 4 example scripts (analyze, record/replay, evolve, config)
- docs/architecture.md with module dependency diagrams

### v2.0.0 (Enhance Phase)

- Disassembler module
- Core memory visualizer (heatmap/summary/battle log)
- Warrior file loader utilities
- Step-through execution mode
- Access tracking
- On_execute callback hook
- 2 new warriors (imp-spiral, kamikaze)
- pyproject.toml
- 3 new CLI subcommands (core-dump, step, validate)

### v1.0.0 (Initial Release)

- Full ICWS'94 Redcode instruction set (16 opcodes, 7 modifiers, 8 modes)
- Redcode parser (labels, EQU, ORG/END, expressions)
- MARS virtual machine
- Battle scheduler and tournament system
- 5 built-in warriors
- CLI with 7 subcommands

---

## Roadmap

- [ ] **Graphical visualizer**: Tkinter/PyQt real-time core view
- [ ] **ICWS'88 compatibility mode**: Support the older standard
- [ ] **PMARS-compatible parser**: Handle PMARS-specific extensions
- [ ] **Warrior optimizer**: Automatically optimize warrior code
- [ ] **Multi-core battles**: Battles across multiple cores simultaneously
- [ ] **Network tournament server**: Real-time battles over TCP
- [ ] **Web visualizer**: Browser-based core memory view
- [ ] **Cython optimization**: Performance-critical paths in Cython
- [ ] **Evolved warrior library**: Collection of best evolved warriors
- [ ] **Advanced genetic features**: Co-evolution, speciation, niching

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up the development environment
- Adding new features, warriors, or opcodes
- Running tests and submitting pull requests
- Code style and architecture overview

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

## Tests

```bash
# Run all 162 tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=core_war --cov-report=term-missing

# Run only new module tests
python3 -m pytest tests/test_new_modules.py -v
```