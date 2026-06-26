# Cellular Automaton Simulator

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/cellular-automaton-ci.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions/workflows/cellular-automaton-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 150](https://img.shields.io/badge/tests-150%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-4.0.0-blue)]()

A comprehensive cellular automaton engine in pure Python with NumPy-accelerated
stepping. Supports **discrete** (binary, multi-state) and **continuous**
(reaction-diffusion) cellular automata across **1D**, **2D**, and
**larger-neighbourhood** (Larger than Life) regimes.

## What's New in v4.0

| Feature | Description |
|---------|-------------|
| 🧪 **Continuous CAs** | Gray-Scott reaction-diffusion (10 presets) + FitzHugh-Nagumo excitable medium |
| 🌐 **Larger than Life** | Arbitrary-radius Life-like rules with `Bxx/Sxx/Rn` notation (5 presets) |
| 🎞️ **GIF export** | Animated GIF output for binary and multi-state CAs (via Pillow) |
| 📂 **RLE file I/O** | Load patterns from `.rle` files (LifeWiki/Golly format) + save patterns |
| 🔧 **4 new CLI commands** | `gif`, `rle-file`, `ltl`, `continuous` (19 subcommands total) |
| 📊 **45 new tests** | 150 tests total (was 105), covering all new features |
| 📝 **5 new examples** | Gray-Scott, LtL, FitzHugh-Nagumo, GIF, RLE files |

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Config Files](#config-files)
  - [Multi-State CAs](#multi-state-cas)
  - [Continuous CAs](#continuous-cas)
  - [Larger than Life](#larger-than-life)
  - [Analysis Tools](#analysis-tools)
  - [RLE Files](#rle-files)
  - [GIF Export](#gif-export)
- [Architecture](#architecture)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

## Features

### Rules

| Category | Count | Examples |
|----------|-------|----------|
| Elementary 1D (Wolfram) | 256 | Rule 30 (chaotic), Rule 90 (Sierpinski), Rule 110 (Turing-complete), Rule 184 (traffic) |
| Life-like 2D | 15 | Game of Life, HighLife, Seeds, Day & Night, Replicator, Maze, Mazectric, Anneal, Coral, Diamoeba, Majority, WalledCities, Gnarl, LifeWithoutDeath, TwoByTwo |
| Multi-state | 5 | Wireworld (4 states), Brian's Brain (3), Forest Fire (3), Cyclic (configurable), Immigration (3) |
| Larger than Life | 5+ | Boon (R5), Grenville (R3), Bugs (R4), + arbitrary `Bxx/Sxx/Rn` |
| Continuous | 2 | Gray-Scott (reaction-diffusion, 10 presets), FitzHugh-Nagumo (excitable medium) |
| Custom | ∞ | Any Python callable with configurable radius/dimensions |
| Bxx/Sxx notation | ∞ | Any outer-totalistic rule, e.g. `B36/S23` |

### Patterns (19 built-in)

- **Still lifes:** block, beehive, loaf, ship, boat, tub
- **Oscillators:** blinker, toad, beacon, pulsar, pentadecathlon
- **Spaceships:** glider, LWSS, MWSS, HWSS
- **Guns:** Gosper glider gun
- **Methuselahs:** R-pentomino, diehard, acorn
- **RLE parser** — load any pattern from Run Length Encoded strings or `.rle` files

### Boundary Conditions

`periodic` (toroidal wrap), `fixed` (constant value), `reflect` (mirror/Neumann), `zero`

### Rendering

- **ASCII** — compact text output with configurable characters
- **ANSI** — colour-coded terminal display
- **SVG** — vector graphics (2D grids and 1D spacetime)
- **PPM / PNG** — raster image output (PNG requires Pillow)
- **GIF** — animated GIF export (requires Pillow)
- **Spacetime diagrams** — 1D CA history stacked vertically (time ↓)
- **Animation frames** — numbered PPM/PNG frame sequences for 2D CAs
- **Continuous ASCII** — character-ramp rendering for float fields

### Analysis Tools

- **Wolfram classification** — classify 1D rules into classes I–IV
- **Shannon entropy** — per-cell or block entropy of grids
- **Spacetime entropy** — average per-row entropy over a CA evolution
- **Density tracking** — live-cell density over time with trend detection
- **Parameter sweeps** — run CAs across parameter grids
- **Lyapunov proxy** — perturbation-based chaos detection
- **Local diversity** — count of distinct neighbourhood patterns
- **Hamming distance** — grid-to-grid comparison

### Engine

- **NumPy-vectorized stepping** — orders of magnitude faster than Python loops
- Step history (undo support via history stack)
- 1D spacetime accumulation
- Cycle/stability detection via state hashing
- **Run statistics** — births, deaths, max/min alive, cycle length
- **JSON serialization** — save/load complete CA state
- Deep-copy support

## Installation

```bash
cd cellular-automaton
pip install -e .              # installs numpy + CLI entry point

# Optional extras:
pip install -e ".[png]\"       # PNG rendering (Pillow)
pip install -e ".[yaml]\"      # YAML config support (PyYAML)
pip install -e ".[dev]\"       # dev dependencies (pytest, pytest-cov, Pillow, PyYAML)
pip install -e ".[all]\"       # all optional dependencies
```

Requires **Python 3.8+** and **NumPy ≥ 1.20**. GIF/PNG export requires Pillow.

## Quick Start

```python
from cellular_automaton import (
    CellularAutomaton, ElementaryRule, GameOfLifeRule,
    get_pattern, place_pattern, render_ascii, render_spacetime_ascii,
)

# 1D — Wolfram's Rule 30 from a single centre cell
ca = CellularAutomaton(ElementaryRule(30), width=80)
ca.center_seed()
ca.step(40)
print(render_spacetime_ascii(ca.get_spacetime_array(), on_char="█", off_char=" "))

# 2D — Conway's Game of Life with a glider
ca = CellularAutomaton(GameOfLifeRule(), width=40, height=20)
place_pattern(ca, get_pattern('glider'), x=5, y=5)
ca.step(100)
print(render_ascii(ca.grid))

# Continuous — Gray-Scott reaction-diffusion spots
from cellular_automaton import GrayScott, render_continuous_ascii
gs = GrayScott.from_preset("spots", width=50, height=25)
gs.seed_square(25, 12, radius=6)
gs.step(500)
print(render_continuous_ascii(gs.states[1], chars=" .:-=+*#%@"))
```

## Usage

### Python API

#### 1D Elementary Rules

```python
from cellular_automaton import CellularAutomaton, ElementaryRule, render_spacetime_ascii

# Rule 30 — Wolfram's chaotic rule
ca = CellularAutomaton(ElementaryRule(30), width=80, boundary="zero")
ca.center_seed()
ca.step(40)
print(render_spacetime_ascii(ca.get_spacetime_array(), on_char="█", off_char=" "))

# Rule 90 — Sierpinski triangle
ca = CellularAutomaton(ElementaryRule(90), width=63, boundary="zero")
ca.center_seed()
ca.step(31)
print(render_spacetime_ascii(ca.get_spacetime_array()))

# Rule 184 — Traffic flow model
ca = CellularAutomaton(ElementaryRule(184), width=20, boundary="periodic")
ca.set_grid([0,0,1,1,1,1,0,0,0,0, 0,0,1,1,1,1,0,0,0,0])
ca.step(1)
print(ca.grid[0])
```

#### 2D Life-like Rules

```python
from cellular_automaton import (
    CellularAutomaton, GameOfLifeRule, get_pattern, place_pattern, render_ascii,
)

# Conway's Game of Life with a Gosper glider gun
ca = CellularAutomaton(GameOfLifeRule(), width=60, height=40)
place_pattern(ca, get_pattern('gosper_gun'), x=5, y=10)
ca.step(200)
print(f"Alive cells: {ca.alive_count()}")
print(render_ascii(ca.grid))

# Run with statistics and cycle detection
ca = CellularAutomaton(GameOfLifeRule(), width=30, height=30)
place_pattern(ca, get_pattern('blinker'), x=10, y=10)
stats = ca.run(50)
print(f"Stable: {stats.stable}, cycle: {stats.cycle_detected} (len {stats.cycle_length})")

# HighLife (B36/S23) with random init
from cellular_automaton import get_rule
ca = CellularAutomaton(get_rule('HighLife'), width=50, height=30)
ca.randomize(0.3, seed=42)
ca.step(100)
```

#### Custom Rules

```python
from cellular_automaton import CellularAutomaton, CustomRule

# Custom Python callable rule (majority rule)
def majority(neighbourhood):
    return 1 if neighbourhood.sum() >= 5 else 0

ca = CellularAutomaton(CustomRule(majority, radius=1, dimensions=2),
                       width=40, height=40)
ca.randomize(0.5, seed=42)

# Bxx/Sxx notation
from cellular_automaton import get_rule
rule = get_rule('B36/S23')  # HighLife
```

#### Serialization

```python
# Save / load
ca = CellularAutomaton(GameOfLifeRule(), width=20, height=20)
ca.randomize(0.3, seed=42)
ca.step(10)
ca.save('state.json')

ca2 = CellularAutomaton.load('state.json')
assert ca2.step_count == 10
```

### CLI

The CLI has **19 subcommands**:

```bash
# Run Rule 30 for 30 steps from a centre seed
cellular-automaton run --rule Rule30 --width 80 --steps 30 --boundary zero

# Game of Life with a Gosper glider gun
cellular-automaton run --rule GameOfLife --width 60 --height 40 \
    --pattern gosper_gun --steps 200 --format ansi

# Random initial state
cellular-automaton run --rule GameOfLife --width 60 --height 30 \
    --random 0.3 --seed 42 --steps 100

# Render to SVG
cellular-automaton render --rule Rule110 --width 100 --steps 50 \
    --format svg --output rule110.svg

# 1D spacetime diagram
cellular-automaton spacetime --rule Rule90 --width 80 --steps 40 --format ascii
cellular-automaton spacetime --rule Rule30 --width 100 --steps 60 \
    --format svg --output rule30.svg

# Simulate with statistics & cycle detection
cellular-automaton simulate --rule GameOfLife --width 20 --height 20 \
    --pattern blinker --px 8 --py 8 --steps 50 --json

# Export animation frames
cellular-automaton animate --rule GameOfLife --width 40 --height 30 \
    --random 0.3 --seed 7 --steps 50 --format ppm --output frames/

# Export animated GIF (new in v4.0)
cellular-automaton gif --rule GameOfLife --width 60 --height 40 \
    --random 0.3 --seed 42 --steps 100 --output evolution.gif

# Save / load state
cellular-automaton save --rule Rule30 --width 50 --steps 10 -o state.json
cellular-automaton load state.json

# Load a pattern from RLE
cellular-automaton run --rule GameOfLife --width 20 --height 20 \
    --rle "bo$2bo$3o!" --px 5 --py 5 --steps 20

# Load a pattern from an RLE file (new in v4.0)
cellular-automaton rle-file glider.rle --rule GameOfLife --width 40 --height 20 --steps 50

# List rules / patterns
cellular-automaton rules
cellular-automaton patterns

# Rule info
cellular-automaton info --rule Rule30
cellular-automaton info --rule GameOfLife
cellular-automaton info --rule Wireworld

# Classify elementary rules
cellular-automaton classify --rule 30
cellular-automaton classify --all

# Compute entropy
cellular-automaton entropy --rule GameOfLife --width 50 --height 50 \
    --random 0.3 --steps 50 --block-size 2

# Parameter sweep
cellular-automaton sweep --rule ForestFire \
    --params '{"p":[0.001,0.01,0.05],"g":[0.01,0.05,0.1]}'

# Run from config file
cellular-automaton config examples/configs/gosper_gun.json

# Multi-state CA
cellular-automaton multistate --rule Wireworld --width 40 --height 10 \
    --random 0.3 --seed 42 --steps 20
cellular-automaton multistate --rule ForestFire --width 50 --height 25 \
    --random 0.3 --seed 42 --steps 30 --params p=0.001,g=0.05

# Larger than Life (new in v4.0)
cellular-automaton ltl --rule Boon --width 30 --height 20 --steps 10 --seed 42
cellular-automaton ltl --rule B5678/S45678/R5 --width 30 --height 20 --steps 10

# Continuous CA — reaction-diffusion (new in v4.0)
cellular-automaton continuous --model GrayScott --preset spots --width 50 --steps 500
cellular-automaton continuous --model FitzHughNagumo --width 50 --steps 300
cellular-automaton continuous --model GrayScott --preset stripes --width 80 --steps 1000 --format png -o spots.png
```

### Config Files

Run CAs from JSON, YAML, or TOML config files:

**JSON example:**
```json
{
  "rule": "GameOfLife",
  "width": 60,
  "height": 40,
  "boundary": "periodic",
  "initial": {"pattern": "gosper_gun", "x": 5, "y": 10},
  "steps": 200,
  "output": {"format": "ascii"},
  "logging": {"level": "INFO"}
}
```

**YAML example:**
```yaml
rule: Rule30
width: 80
boundary: zero
initial:
  center: true
steps: 40
output:
  format: ascii
```

```bash
# Run from config
cellular-automaton config simulation.json
cellular-automaton config simulation.yaml --steps 100
```

See `examples/configs/` for ready-to-use config files.

### Multi-State CAs

Multi-state CAs have cells with more than two states:

```python
from cellular_automaton import CellularAutomaton, WireworldRule, ForestFireRule

# Wireworld — electronic circuit simulation
# States: 0=empty, 1=electron head, 2=electron tail, 3=conductor
ca = CellularAutomaton(WireworldRule(), width=40, height=10, boundary="zero")
for x in range(5, 35):
    ca.set_cell(x, 5, 3)  # conductor wire
ca.set_cell(8, 5, 1)      # electron head
ca.set_cell(7, 5, 2)      # electron tail
ca.step(20)  # electron flows along the wire

# Forest Fire — ecological model
ca = CellularAutomaton(ForestFireRule(p=0.001, g=0.05), width=50, height=25)
ca.set_rng(42)
ca.randomize(0.3, seed=42)
ca.step(100)

# Brian's Brain — wave patterns
from cellular_automaton import BriansBrainRule
ca = CellularAutomaton(BriansBrainRule(), width=50, height=50)
ca.randomize(0.3, seed=42)
ca.step(50)

# Cyclic — spiral waves
from cellular_automaton import CyclicRule
ca = CellularAutomaton(CyclicRule(n_states=14, threshold=3), width=50, height=50)
ca.randomize(0.5, seed=42)

# Immigration — two-species Game of Life
from cellular_automaton import ImmigrationRule
ca = CellularAutomaton(ImmigrationRule(), width=50, height=50)
ca.randomize(0.3, seed=42)
```

### Continuous CAs

Continuous CAs use floating-point cell values instead of discrete states.
The engine supports two reaction-diffusion models:

#### Gray-Scott

Produces self-organising patterns (spots, stripes, mazes, solitons, gliders):

```python
from cellular_automaton import GrayScott, render_continuous_ascii

# Use a preset
gs = GrayScott.from_preset("spots", width=80, height=40)
gs.seed_square(40, 20, radius=8)
gs.step(1000)
print(render_continuous_ascii(gs.states[1], chars=" .:-=+*#%@"))

# Custom parameters
gs = GrayScott(80, 40, F=0.022, k=0.059)  # stripes pattern
gs.seed_random(n_seeds=10, seed=42)
gs.step(500)
```

**Gray-Scott presets:** `spots`, `stripes`, `maze`, `worms`, `solitons`,
`gliders`, `coral`, `chaos`, `holes`, `pulsating`

#### FitzHugh-Nagumo

An excitable-medium model producing spiral waves:

```python
from cellular_automaton import FitzHughNagumo, render_continuous_ascii

fhn = FitzHughNagumo(60, 30)
fhn.seed_spiral(30, 15)
fhn.step(400)
print(render_continuous_ascii(fhn.states[0], chars=" .:-=+*#%@"))
```

### Larger than Life

Larger than Life (LtL) rules use neighbourhoods bigger than the standard 3×3:

```python
from cellular_automaton import CellularAutomaton, LargerThanLifeRule, render_ascii

# Boon — 5×5 neighbourhood
rule = LargerThanLifeRule((5678,), (45678,), radius=5, name="Boon")
ca = CellularAutomaton(rule, width=30, height=20)
ca.randomize(0.3, seed=42)
ca.step(10)
print(render_ascii(ca.grid))

# Parse Bxx/Sxx/Rn notation
from cellular_automaton import parse_ltl_notation
rule = parse_ltl_notation("B3/S23/R2")  # Life with radius 2
```

**LtL presets:** `Boon` (R5), `Grenville` (R3), `Bugs` (R4), plus any `Bxx/Sxx/Rn` string.

### Analysis Tools

```python
from cellular_automaton import (
    classify_elementary_rule, shannon_entropy, density_over_time,
    parameter_sweep, lyapunov_proxy, local_diversity,
)

# Wolfram classification
result = classify_elementary_rule(30)
print(f"Class {result.classification}: {result.description}")
print(f"Entropy: {result.entropy:.4f}, Density: {result.density:.4f}")

# Classify all 256 rules
for n in range(256):
    result = classify_elementary_rule(n)
    print(f"Rule {n:>3}: Class {result.classification}")

# Shannon entropy of a CA grid
entropy = shannon_entropy(ca.grid, block_size=4)

# Density over time
report = density_over_time(ca, steps=100)
print(f"Mean density: {report.mean:.4f}, Trend: {report.trend}")

# Parameter sweep
from cellular_automaton import ForestFireRule
results = parameter_sweep(
    lambda p, g: ForestFireRule(p=p, g=g),
    {"p": [0.001, 0.01, 0.05], "g": [0.01, 0.05, 0.1]},
    width=50, height=50, steps=100,
)
for r in results:
    print(f"  {r.params} → density={r.mean_density:.3f}")

# Lyapunov proxy — chaos detection
from cellular_automaton import ElementaryRule
distances = lyapunov_proxy(ElementaryRule(30), width=100, steps=50)
print(f"Divergence: {distances[0]} → {distances[-1]}")

# Local diversity
div = local_diversity(ca.grid, radius=1)
print(f"Distinct neighbourhoods: {div}")
```

### RLE Files

Load and save patterns in the standard RLE format (used by LifeWiki, Golly, etc.):

```python
from cellular_automaton import load_rle_file, save_rle_file, get_pattern

# Save the Gosper glider gun to an RLE file
gosper = get_pattern("gosper_gun")
save_rle_file(gosper, "gosper.rle")

# Load it back
pat = load_rle_file("gosper.rle")
print(f"Loaded {len(pat)} cells")
```

RLE file format:
```
#C Comment line
x = 36, y = 9, rule = B3/S23
24bo11b$22bobo11b$12b3o15b2o$11bo6b3o3b3o6b$...
```

### GIF Export

Export CA evolutions as animated GIFs (requires Pillow):

```python
from cellular_automaton import (
    CellularAutomaton, GameOfLifeRule, get_pattern, place_pattern, render_gif,
)

ca = CellularAutomaton(GameOfLifeRule(), width=60, height=40)
place_pattern(ca, get_pattern("gosper_gun"), x=5, y=10)
render_gif(ca, path="gosper.gif", steps=200, cell_size=4, duration=50)

# Multi-state CAs with state colours
from cellular_automaton import WireworldRule, render_multistate_gif
ca = CellularAutomaton(WireworldRule(), width=40, height=20)
# ... set up wireworld circuit ...
render_multistate_gif(ca, path="wireworld.gif", steps=50, cell_size=4, duration=100)
```

## Architecture

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

The engine uses a **dispatch pattern** in `_compute_next()`. It checks the rule
type and selects the fastest available stepping method:

1. **Multi-state rules** → `rule.step()` (grid-level NumPy operations)
2. **ElementaryRule** → `step_elementary_vectorized()` (lookup-table gather)
3. **GameOfLifeRule** (radius 1) → `step_life_vectorized()` (sliding-window sum)
4. **LargerThanLifeRule** → `rule.step_vectorized()` (arbitrary-radius convolution)
5. **Everything else** → `_compute_next_generic()` (per-cell Python loop)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a detailed description.

### Project Structure

```
cellular-automaton/
├── cellular_automaton/           # Main package
│   ├── __init__.py               # Public API (all exports)
│   ├── engine.py                 # Core CA engine
│   ├── rules.py                  # Binary rule classes + registry
│   ├── multistate.py             # Multi-state CAs (5 types)
│   ├── continuous.py             # Continuous CAs (Gray-Scott, FHN) [NEW]
│   ├── ltl.py                    # Larger than Life rules [NEW]
│   ├── patterns.py               # 19 builtin patterns + RLE parser + file I/O
│   ├── vectorized.py             # NumPy-accelerated stepping
│   ├── visualizer.py             # ASCII/ANSI/SVG/PPM/PNG/GIF renderers
│   ├── analysis.py               # Wolfram classification, entropy, sweeps
│   ├── config.py                 # Config system (JSON/YAML/TOML)
│   └── cli.py                    # argparse CLI (19 subcommands)
├── examples/
│   ├── 01_rule30.py              # Rule 30 chaotic pattern
│   ├── 02_gosper_gun.py          # Gosper glider gun
│   ├── 03_highlife.py            # HighLife replicator
│   ├── 04_wireworld.py           # Wireworld electron flow
│   ├── 05_classification.py      # Classify all 256 rules
│   ├── 06_forest_fire.py         # Forest fire simulation
│   ├── 07_config.py              # Config file usage
│   ├── 08_lyapunov.py            # Lyapunov exponent proxy
│   ├── 09_gray_scott.py          # Gray-Scott spots [NEW]
│   ├── 10_ltl_boon.py            # Larger than Life [NEW]
│   ├── 11_fitzhugh_nagumo.py     # Spiral waves [NEW]
│   ├── 12_gif_export.py          # Animated GIF [NEW]
│   ├── 13_rle_file.py            # RLE file I/O [NEW]
│   └── configs/                  # Ready-to-use config files
├── tests/                        # 150 tests (7 test files)
├── docs/
│   └── ARCHITECTURE.md           # Architecture documentation
├── pyproject.toml                # Package metadata + dependencies
├── LICENSE                       # MIT license
├── CONTRIBUTING.md               # Contributing guide
└── README.md                     # This file
```

## Examples

### Rule 30 — Chaotic Pattern

```
                                █
                               ███
                              ██ ███
                             ███ █ ███
                            ██   ███ ███
                           ████ ██   █ ███
                          ██  ██████ ██ ███
                         ███████  ███████ ███
                        ██     █████  ██████ ███
                       ██████ ██    █████ ██  █ ███
```

### Wireworld — Electron Flow

```
Step  0: .....##TH##########################.....
Step  1: .....###TH#########################.....
Step  2: .....####TH########################.....
Step  3: .....#####TH#######################.....
```

### Rule 90 — Sierpinski Triangle

```
                               █
                              █ █
                             █   █
                            █ █ █ █
                           █       █
                          █ █     █ █
                         █   █   █   █
                        █ █ █ █ █ █ █ █
```

### Gray-Scott — Spots Pattern

```
              .:-:.      :-=+.
             .=#@@*:    :+@@#-.
             -#@@@#.    .+@@@#:
             :#@@@+.    .+@@@#:
             .-##=:      :+##-.
              ...        ...
```

### Larger than Life — Boon (R5)

Produces organic blob patterns from random noise using a 5×5 neighbourhood:

```
    █   █      █ █
     ██ █        █ ███
        █ █  ████      ███  █
█      ██   █    ██  █  █
  █ █  ██ █    █   █     █   █
```

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **Beacon pattern missing 2 cells** — Had 6 cells instead of 8. **Fix:** Added missing inner cells at (1,1) and (2,2).
2. **Pentadecathlon pattern incorrect** — Was a plain row of 10. **Fix:** Replaced with correct 12-cell pattern from LifeWiki (`2bo4bo$2ob4ob2o$2bo4bo!`).
3. **`reflect` boundary inconsistency** — 1D used edge/clamp while 2D used NumPy's `reflect`. **Fix:** Unified to edge/clamp everywhere.
4. **Incorrect births/deaths statistics** — Heuristic formula was wrong. **Fix:** Exact per-cell comparison.
5. **`render_png` fallback wrong filename** — Wrote `.png.ppm` instead of the requested path. **Fix:** Writes to exact path.
6. **`fixed_value > 1` causes `IndexError`** — Non-binary values overflowed lookup table. **Fix:** Binary clamping.
7. **`from_dict` deserialization crash** — `get_rule()` raises `KeyError` not `None`. **Fix:** try/except with Bxx/Sxx fallback.

### v4.0 Bug Fixes

8. **Gray-Scott Laplacian stencil weights** — All 8 neighbours were weighted 0.05, causing a non-zero Laplacian for constant fields (weights summed to −0.60 instead of 0). **Fix:** Corrected to 0.20 for edge neighbours and 0.05 for corner neighbours (weights now sum to 0).

## Roadmap

- [x] ~~**Continuous CA** — Reaction-diffusion models (Gray-Scott, FitzHugh-Nagumo)~~ ✅ v4.0
- [x] ~~**Larger than Life** — Larger neighbourhood Life-like rules~~ ✅ v4.0
- [x] ~~**GIF export** — Direct animated output~~ ✅ v4.0
- [x] ~~**Pattern file loader** — Load patterns from .rle files~~ ✅ v4.0
- [ ] **3D CAs** — 3D Life-like rules and visualizers
- [ ] **Interactive mode** — Live terminal display with keyboard controls
- [ ] **More multi-state CAs** — Vote, Belousov-Zhabotinsky, Wireworld computer
- [ ] **Pattern library** — Expand builtin patterns (oscillators, spaceships)
- [ ] **Performance** — Numba/Cython JIT for the generic stepping path
- [ ] **Web playground** — Browser-based interactive CA explorer
- [ ] **Audio synthesis** — Convert CA patterns to MIDI/OSC

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding conventions,
and how to add new rules, patterns, and renderers.

## Changelog

### v4.0.0 (2026-06-26) — Continuous CAs, Larger than Life, GIF, RLE Files

**New Features:**
- **Gray-Scott reaction-diffusion model** — 10 parameter presets (spots, stripes,
  maze, worms, solitons, gliders, coral, chaos, holes, pulsating), seed methods
  (square, random), continuous-state floating-point grids, ASCII rendering with
  character ramps, PNG/GIF export with colormap
- **FitzHugh-Nagumo excitable medium** — spiral wave seed, voltage/recovery
  variables, produces spiral wave patterns
- **Larger than Life (LtL) rules** — `LargerThanLifeRule` class with arbitrary
  radius, `Bxx/Sxx/Rn` notation parser, 5 presets (Boon, Grenville, Bugs),
  vectorised stepping for any radius, engine integration with dispatch path
- **GIF export** — `render_gif()` and `render_multistate_gif()` via Pillow,
  CLI `gif` subcommand
- **RLE file I/O** — `load_rle_file()` and `save_rle_file()` for standard RLE
  format (with header/comments), CLI `rle-file` subcommand
- **4 new CLI subcommands** — `gif`, `rle-file`, `ltl`, `continuous` (19 total)
- **5 new example scripts** (13 total) + 2 new config files (6 total)
- **45 new tests** (150 total, up from 105) — test_ltl.py, test_continuous.py,
  test_new_features.py
- **Laplaician stencil fix** — corrected weights so constant fields have zero
  Laplacian (was producing spurious diffusion in quiescent Gray-Scott grids)

**Improvements:**
- Updated `pyproject.toml` description, keywords, and version
- `from_dict` now supports LtL `Bxx/Sxx/Rn` notation
- `cmd_rules` now lists LtL rules, continuous models, and Gray-Scott presets
- CLI version bumped to 4.0.0

### v3.0.0 (2026-06-24) — Comprehensive Improvement

**New Features:**
- **5 multi-state CAs** — Wireworld, Brian's Brain, Forest Fire, Cyclic, Immigration
- **Analysis tools** — Wolfram classification (I–IV), Shannon entropy, block entropy,
  spacetime entropy, density tracking with trend detection, parameter sweeps,
  Lyapunov exponent proxy, local diversity, Hamming distance
- **Config system** — JSON/YAML/TOML config files with `CAConfig` class
- **5 new CLI subcommands** — classify, entropy, sweep, config, multistate (15 total)
- **Logging** — structured logging via Python `logging` module
- **Multi-state rendering** — state-aware ASCII/ANSI rendering with colour maps
- **8 example scripts** (was 3) + 4 config files
- **Architecture documentation** — `docs/ARCHITECTURE.md`
- **CONTRIBUTING.md** and **LICENSE** files
- **GitHub Actions CI** — tests on Python 3.8–3.12

**Improvements:**
- Enhanced `pyproject.toml` with classifiers, keywords, optional dependencies, URLs
- pytest configuration with coverage settings
- Type hints throughout new modules
- Comprehensive docstrings (Google style) on all new code
- 88 new tests (105 total, up from 17)
- All tests pass in ~0.5s

### v2.0.0 — Enhanced + Bug Hunt

- Vectorized NumPy stepping for 1D and 2D rules
- 1D spacetime diagrams, animation frame export
- JSON serialization, run statistics with cycle detection
- 5 new CLI subcommands (10 total)
- 7 bugs fixed, 17 tests

### v1.0.0 — Initial Release

- 256 Wolfram elementary rules, 15 Life-like variants
- Custom callable rules, Bxx/Sxx notation parser
- 19 builtin patterns, RLE parser
- 4 boundary conditions
- ASCII/ANSI/SVG/PPM/PNG renderers
- 5 CLI subcommands

## License

MIT — see [LICENSE](LICENSE).