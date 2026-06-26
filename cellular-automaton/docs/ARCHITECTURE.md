# Architecture

This document describes the internal architecture of the cellular automaton
simulator.

## Overview

The simulator is organized into a modular Python package with clear
separation of concerns:

```
┌──────────────────────────────────────────────────────────┐
│                      CLI (cli.py)                          │
│         19 subcommands, argparse-based                    │
├──────────────┬───────────────┬──────────────┬────────────┤
│   Config      │   Analysis    │  Visualizer  │ Continuous │
│  (config.py)  │ (analysis.py) │(visualizer.py)│(continuous)│
├──────────────┴───────────────┼──────────────┼────────────┤
│                    Engine (engine.py)                      │
│       CellularAutomaton — stepping, stats, serial.        │
├──────────┬──────────────┬───────────────┬────────────────┤
│  Rules    │  MultiState   │  Vectorized   │     LtL        │
│(rules.py) │(multistate.py)│ (vectorized)  │   (ltl.py)     │
├──────────┼──────────────┼───────────────┼────────────────┤
│ Patterns  │    NumPy     │   RLE Files   │    GIF          │
│(patterns) │  (external)  │  (patterns)   │ (visualizer)    │
└──────────┴──────────────┴───────────────┴────────────────┘
```

## Core Components

### Engine (`engine.py`)

The `CellularAutomaton` class is the central orchestrator. It:
- Holds the grid state (`np.ndarray`), step count, history, and spacetime.
- Dispatches stepping to the appropriate fast path (vectorized or multi-state).
- Collects run statistics with cycle detection via state hashing.
- Provides serialization (JSON save/load) and deep copy.

**Key design decision:** The engine uses a dispatch pattern in
`_compute_next()`. It checks the rule type and selects the fastest available
stepping method:
1. Multi-state rules → `rule.step()` (grid-level NumPy operations)
2. ElementaryRule → `step_elementary_vectorized()` (lookup-table gather)
3. GameOfLifeRule (radius 1) → `step_life_vectorized()` (sliding-window sum)
4. LargerThanLifeRule → `rule.step_vectorized()` (arbitrary-radius convolution)
5. Everything else → `_compute_next_generic()` (per-cell Python loop)

### Rules (`rules.py`)

Defines the abstract `Rule` base class and three concrete implementations:
- `ElementaryRule` — 1D Wolfram rules with a pre-computed 8-bit lookup table.
- `GameOfLifeRule` — 2D outer-totalistic rules with birth/survive sets.
- `CustomRule` — user-supplied Python callable.

The `RULES` registry maps names to instances, covering all 256 elementary
rules and 15 Life-like variants.

### Multi-State Rules (`multistate.py`)

Multi-state CAs need more than binary 0/1 states. Each rule implements a
grid-level `step()` method using NumPy vectorised operations:

- **Wireworld** — electronic circuit simulation (4 states).
- **Brian's Brain** — wave-like patterns (3 states).
- **Forest Fire** — ecological model with stochastic ignition/growth (3 states).
- **Cyclic** — spiral wave patterns (configurable states).
- **Immigration** — two-species Game of Life (3 states).

### Continuous CAs (`continuous.py`) [v4.0]

Continuous cellular automata use floating-point cell values instead of discrete
states. Two reaction-diffusion models are provided:

- **Gray-Scott** — two species (u, v) with feed/kill/diffusion parameters.
  Uses a 9-point Laplacian stencil (edges 0.20, corners 0.05, centre −1.00,
  weights sum to zero). 10 parameter presets produce distinct pattern regimes
  (spots, stripes, maze, worms, solitons, gliders, coral, chaos, holes, pulsating).
- **FitzHugh-Nagumo** — excitable medium with voltage (v) and recovery (w)
  variables. Produces spiral wave patterns.

Both models use NumPy vectorised operations for speed. The `ContinuousCA` base
class provides the Laplacian, serialization, and step-counting infrastructure.

### Larger than Life (`ltl.py`) [v4.0]

Larger-than-Life rules extend Life-like rules to neighbourhoods bigger than 3×3.
The `LargerThanLifeRule` class supports arbitrary radius and uses
`neighbour_sum_2d()` from `vectorized.py` for efficient convolution. The
`parse_ltl_notation()` function parses `Bxx/Sxx/Rn` notation strings.

### Vectorized Stepping (`vectorized.py`)

The performance-critical module. Two key functions:

- `step_elementary_vectorized()` — shifts the row left/right, combines into
  a 3-bit index array, and does a single `table[idx]` gather. O(n) per step.
- `step_life_vectorized()` — pads the grid, computes 8 shifted arrays, sums
  them for neighbour counts, then applies birth/survive masks. O(n) per step.
- `neighbour_sum_2d()` — supports arbitrary radius for Larger-than-Life rules.

### Patterns (`patterns.py`)

Patterns are stored as lists of `(x, y)` coordinates, making them
resolution-independent. The RLE parser supports the standard Game of Life
Run Length Encoded format for loading external patterns.

### RLE File I/O [v4.0]

`load_rle_file()` reads standard RLE files (with header `x = ..., y = ...` and
comment lines starting with `#`). `save_rle_file()` writes patterns back to RLE
with run-length encoding and 70-column line wrapping.

### Visualizer (`visualizer.py`)

Multiple output formats:
- **ASCII** — compact text using configurable on/off characters.
- **ANSI** — terminal colour codes (white-on-black blocks).
- **SVG** — vector graphics, one `<rect>` per live cell.
- **PPM** — binary P6 raster image (no dependencies).
- **PNG** — uses Pillow if available, falls back to PPM with `.png` extension.
- **GIF** — animated GIF via Pillow (binary and multi-state with state colours).
- **Spacetime** — stacks 1D CA rows vertically (time flows downward).
- **Animation** — numbered frame sequences for 2D CAs.
- **Continuous ASCII** — character-ramp rendering for float fields.

### Analysis (`analysis.py`)

Tools for understanding CA behaviour:
- **Wolfram classification** — heuristic classification of 1D rules into
  classes I–IV based on entropy, density, and stability.
- **Shannon entropy** — per-cell or block entropy of grids.
- **Density tracking** — live-cell density over time with trend detection.
- **Parameter sweeps** — run a CA across a grid of parameters.
- **Lyapunov proxy** — perturbation-based chaos detection.
- **Local diversity** — count of distinct neighbourhoods.

### Config (`config.py`)

Supports JSON, YAML, and TOML configuration files. YAML requires PyYAML
(optional dependency); TOML uses `tomllib` (Python 3.11+) or `tomli`.

## Data Flow

1. User provides rule + initial state (via Python API, CLI, or config file).
2. Engine initialises the grid (zeros, random, center seed, or pattern).
3. Each `step()` call:
   a. Save current grid to history (for undo).
   b. For 1D rules, save current row to spacetime.
   c. Dispatch to the appropriate `_compute_next()` path.
   d. Update grid and step_count.
4. `run()` wraps step() with statistics collection and cycle detection.
5. Visualizer renders the grid to the desired output format.

For continuous CAs, the flow is simpler: `ContinuousCA.step()` calls
`_single_step()` which applies the reaction-diffusion equations directly
using NumPy array operations (no dispatch needed).