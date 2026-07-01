# Nonogram Solver — Architecture

## Overview

The nonogram-solver is a pure-Python library for solving, generating, and
playing nonogram (Picross/Hanjie/Griddlers) puzzles. It uses no external
dependencies beyond the Python standard library (PyYAML is optional for
YAML config support).

## Module Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI (cli.py)                      │
│  12 subcommands: solve, generate, validate, hint,   │
│  presets, analyze, render, count, batch,            │
│  benchmark, web, config                              │
├─────────────────────────────────────────────────────┤
│  Web Server (web.py)    │  Batch (batch.py)         │
│  Interactive browser     │  Multi-file solving      │
│  solver via http.server  │  + report generation      │
├──────────────────────────┼──────────────────────────┤
│  Benchmark (benchmark.py)│  Stats (stats.py)        │
│  Performance measurement │  Solver instrumentation   │
├──────────────────────────┴──────────────────────────┤
│                    Solver (solver.py)                 │
│  Constraint propagation + MRV backtracking            │
│  + solution counting + uniqueness checking           │
├─────────────────────────────────────────────────────┤
│               LineSolver (line_solver.py)            │
│  Overlap method + constraint propagation per line    │
│  + feasibility verification + result caching         │
├─────────────────────────────────────────────────────┤
│                    Board (board.py)                   │
│  Grid + clues + query/mutation helpers               │
│  + serialization (to_dict/from_dict)                │
├──────────────┬──────────────┬────────────────────────┤
│ I/O (io.py)  │ Renderer     │ Analyzer (analyzer.py) │
│ JSON/NON/PNG │ (renderer.py)│ Difficulty grading     │
│ SVG          │ ANSI/HTML    │                        │
├──────────────┴──────────────┴────────────────────────┤
│  Generator (generator.py) │ Player (player.py)      │
│  Random puzzle creation    │ Interactive play+hints │
├───────────────────────────┼────────────────────────┤
│  Presets (presets.py)     │ Config (config.py)     │
│  10 curated puzzles        │ JSON/YAML/TOML config   │
└───────────────────────────┴────────────────────────┘
```

## Core Algorithm

### 1. LineSolver — Per-Line Deduction

The `LineSolver` is the fundamental building block. Given a single row or
column (a "line") with some cells known and some unknown, plus the clue for
that line, it determines which additional cells can be definitively decided.

**Techniques used:**

1. **Overlap Method**: For each clue block, compute the leftmost and rightmost
   valid positions. If these placements overlap, the overlapping cells are
   guaranteed filled.
   ```
   Clue [3] on a 5-cell line:
   Leftmost:  ###..    (positions 0-2)
   Rightmost: ..###    (positions 2-4)
   Overlap:   ..#..    (position 2 → definitely filled)
   ```

2. **Constraint Propagation**: Iterate to a fixpoint, repeatedly applying
   the overlap method. Each pass may reveal new filled or empty cells which
   further constrain the next pass.

3. **Feasibility Check**: A backtracking verifier confirms that at least one
   valid arrangement exists consistent with the known cells.

4. **Result Caching**: Results are cached by (line_state, clue, length) key
   to avoid redundant computation across propagation rounds.

### 2. Solver — Full-Board Solving

The `Solver` combines line-level deduction with backtracking:

1. **Constraint Propagation**: Apply `LineSolver` to every row and column
   iteratively until no more progress is made (fixpoint).

2. **MRV Backtracking**: When propagation stalls, use the Minimum Remaining
   Values heuristic to pick the most constrained line (fewest unknowns),
   try both values for an unknown cell in that line, and recurse.

3. **Solution Counting**: `count_solutions()` uses the same backtracking
   framework but counts all solutions up to a limit (for uniqueness checking).

### 3. Generator — Puzzle Creation

The `Generator` creates random grids at a given density, derives clues from
the grid, and verifies (via the solver) that the clues produce a unique
solution. It retries up to `max_attempts` times if uniqueness is required.

### 4. Difficulty Analyzer

The `DifficultyAnalyzer` estimates puzzle difficulty based on:
- Grid size and total cells
- Clue complexity (number of blocks, average block size)
- Filled-cell ratio
- Whether constraint propagation alone solves the puzzle
- Backtracking effort (number of backtracks, backtrack ratio)

Produces a score and classifies as: trivial / easy / medium / hard / expert.

## Data Flow

```
Puzzle File (JSON/NON)
       │
       ▼
   Board (clues + grid state)
       │
       ▼
   Solver
   ├── LineSolver (per line)
   │   ├── Overlap computation
   │   ├── Leftmost/rightmost placement
   │   └── Feasibility check
   ├── Constraint propagation (iterate lines → fixpoint)
   └── MRV backtracking (if propagation stalls)
       │
       ▼
   Solved Board (all cells decided)
       │
       ├── Render (ANSI/HTML/SVG/PNG)
       ├── Export (JSON/NON)
       ├── Analyze (difficulty score)
       ├── Validate (uniqueness check)
       └── Count solutions
```

## Configuration

Configuration is managed by `config.py` and supports JSON, YAML, and TOML
formats. The `AppConfig` dataclass provides typed, validated configuration
for solver, generator, rendering, and logging settings.

## Web Server

The `web.py` module provides an interactive web-based solver using only
`http.server` from the standard library. It serves a self-contained HTML/JS/CSS
page that supports cell clicking, hints, checking, solving, and reset.