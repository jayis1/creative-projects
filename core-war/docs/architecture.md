# Core War Architecture

## Overview

The Core War MARS simulator is organized into a modular Python package
where each module handles a distinct responsibility in the simulation
pipeline.

## Module Dependencies

```
                    ┌──────────────┐
                    │   cli.py     │  ← Command-line interface
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌─────▼─────┐ ┌───────▼────────┐
    │ config.py   │ │ loader.py │ │ strategy_      │
    │ (YAML/JSON) │ │ (.red)    │ │ analyzer.py    │
    └─────────────┘ └─────┬─────┘ └───────┬────────┘
                          │               │
                   ┌──────▼──────┐ ┌──────▼───────┐
                   │ parser.py   │ │ instruction  │
                   │ (Redcode)   │ │ .py          │
                   └──────┬──────┘ └──────────────┘
                          │
                   ┌──────▼──────┐
                   │ mars.py     │  ← Core execution engine
                   │ (MARS VM)   │
                   └──────┬──────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
       ┌──────▼─────┐ ┌───▼────┐ ┌────▼───────┐
       │scheduler.py│ │replay  │ │visualizer  │
       │(tournaments)│ │.py    │ │.py         │
       └────────────┘ └────────┘ └────────────┘

       ┌────────────┐
       │ mutator.py │  ← Genetic evolution (uses scheduler)
       └────────────┘
```

## Core Components

### Instruction (`instruction.py`)

The fundamental unit of core memory. Each cell in the MARS is an
`Instruction` containing:
- Opcode (DAT, MOV, ADD, etc.)
- Modifier (.A, .B, .AB, .BA, .F, .X, .I)
- A-operand (addressing mode + value)
- B-operand (addressing mode + value)

### Parser (`parser.py`)

Two-pass parser for Redcode source:
1. **First pass**: Extract labels, EQU constants, ORG/END pseudo-ops
2. **Second pass**: Resolve expressions and build Instruction objects

Supports:
- Labels (relative addressing)
- EQU constants
- Arithmetic expressions in operands
- All ICWS'94 opcodes, modifiers, and addressing modes

### MARS (`mars.py`)

The virtual machine that executes warriors:
- Circular memory array (core)
- Process scheduling (round-robin, multi-process via SPL)
- Full instruction execution with all addressing modes
- Step-through mode for debugging
- Execution trace recording
- Access count tracking for heatmaps
- Event callback hooks

### Scheduler (`scheduler.py`)

Manages multi-round battles and tournaments:
- `run_battle()`: N rounds between a set of warriors
- `run_tournament()`: Round-robin between all warriors
- Score tracking (3 points/win, 1/draw)

### Strategy Analyzer (`strategy_analyzer.py`)

Classifies warrior strategies by analyzing Redcode source:
- **Strategy types**: Bomber, Scanner, Replicator, Imp, Vampire, One-Shot, Silk, Stone
- **Vulnerability detection**: Identifies weaknesses (no offense, single process, etc.)
- **Metrics**: Aggressiveness (0-10), Resilience (0-10), Process estimate
- **Comparison**: Predicts winners between two warriors

### Replay (`replay.py`)

Records and replays battles:
- `BattleRecorder`: Captures per-cycle state snapshots
- `BattleReplay`: Reconstructs core state at any cycle
- JSON serialization for persistence

### Genetic Evolution (`mutator.py`)

Evolves warriors through genetic algorithms:
- `WarriorMutator`: Point mutations, crossover, structural changes
- `GeneticEvolver`: Population management, fitness evaluation, elitism
- Tournament selection with configurable parameters

### Configuration (`config.py`)

YAML/JSON configuration with validation:
- All battle parameters in one file
- Warrior file paths
- Logging and output format settings
- Template generation

## Data Flow

```
.red file → loader.py → parser.py → ParsedWarrior
                                        │
                                        ├──→ MARS.load_warrior() → execution
                                        │
                                        ├──→ StrategyAnalyzer.analyze() → AnalysisResult
                                        │
                                        ├──→ BattleScheduler.run_battle() → BattleStats
                                        │
                                        └──→ BattleRecorder.record() → BattleRecording
                                                                     │
                                                                     └──→ BattleReplay → snapshots
```