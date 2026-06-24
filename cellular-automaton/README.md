# Cellular Automaton Simulator

A from-scratch 1D & 2D cellular automaton (CA) engine in pure Python (NumPy-backed), supporting all 256 of Wolfram's elementary rules, 15 Life-like rule variants, custom user-defined rules, 19 classic patterns, RLE pattern loading, spacetime diagrams, animation frame export, serialization, statistics with cycle detection, and multi-format rendering (ASCII / ANSI / SVG / PPM / PNG).

## Features

### Rules
- **256 Elementary 1D rules** — Wolfram's radius-1 rules (Rule 0–255), including the famous Rule 30 (chaotic), Rule 90 (Sierpinski), Rule 110 (Turing-complete), and Rule 184 (traffic flow).
- **15 Life-like 2D rules** — Conway's Game of Life (B3/S23), HighLife (B36/S23), Seeds (B2/S), Day & Night (B3678/S34678), Replicator, Maze, Mazectric, Anneal, Coral, Diamoeba, Majority, WalledCities, Gnarl, LifeWithoutDeath, TwoByTwo.
- **Custom rules** — supply any Python callable that maps a neighbourhood to a new cell state; configurable radius and dimensions.
- **Bxx/Sxx notation** — any outer-totalistic 2D rule can be specified inline, e.g. `B36/S23`.

### Patterns (19 built-in)
- **Still lifes:** block, beehive, loaf, ship, boat, tub
- **Oscillators:** blinker, toad, beacon, pulsar, pentadecathlon
- **Spaceships:** glider, LWSS, MWSS, HWSS
- **Guns:** Gosper glider gun
- **Methuselahs:** R-pentomino, diehard, acorn
- **RLE parser** — load any pattern from Run Length Encoded strings.

### Boundary conditions
`periodic` (toroidal wrap), `fixed` (constant value), `reflect` (mirror), `zero`.

### Rendering
- **ASCII** — compact text output.
- **ANSI** — colour-coded terminal display.
- **SVG** — vector graphics (2D grids and 1D spacetime).
- **PPM / PNG** — raster image output (PNG requires Pillow).
- **Spacetime diagrams** — 1D CA history stacked vertically (time flows downward).
- **Animation frames** — export a numbered sequence of PPM/PNG frames for 2D CAs.

### Engine
- **Vectorised stepping** — NumPy-accelerated fast paths for elementary 1D rules and Life-like 2D rules (orders of magnitude faster than per-cell Python loops).
- Step history (undo support via history stack).
- 1D spacetime accumulation.
- Cycle/stability detection.
- State hashing for cycle detection.
- **Run statistics** — births, deaths, max/min alive, cycle length.
- **JSON serialization** — save/load complete CA state.
- Deep-copy support.

## How it works

### 1D Elementary Rules
Each cell looks at itself and its two immediate neighbours (radius 1), forming a 3-bit pattern (000–111, 8 combinations). The rule number's 8-bit binary representation specifies the output for each pattern. For example, Rule 30 = `00011110` in binary, so pattern `111→0, 110→0, 101→0, 100→1, 011→1, 010→1, 001→1, 000→0`. The engine uses a vectorised NumPy lookup-table approach: the entire row is shifted left/right and combined into index arrays, then a single `table[idx]` gather computes the next generation.

### 2D Life-like Rules
Each cell examines its 8 Moore neighbours. The `birth` set specifies neighbour counts that spawn a dead cell to life; the `survive` set specifies counts that keep a live cell alive. All other cells die or stay dead. The engine computes neighbour counts via a vectorised 3×3 sliding-window sum (eight shifted-array additions) and applies birth/survive masks across the whole grid at once.

### Cycle detection
During `run()`, each step's grid is hashed (`hash(grid.tobytes())`) and stored in a dictionary. If a hash repeats, a cycle has been found and its length is reported. A stable state (no cells change) is detected via `changed == 0`.

## Installation

```bash
cd cellular-automaton
pip install -e .          # installs numpy + CLI entry point
# Optional PNG support:
pip install -e ".[png]"
# Optional dev/test:
pip install -e ".[dev]"
```

## Usage

### Python API

```python
from cellular_automaton import (
    CellularAutomaton, ElementaryRule, GameOfLifeRule,
    get_pattern, place_pattern, render_ascii, render_spacetime_ascii,
)

# 1D — Wolfram's Rule 30 from a single centre cell
ca = CellularAutomaton(ElementaryRule(30), width=80)
ca.center_seed()
ca.step(40)
# Spacetime diagram (each row is one timestep)
print(render_spacetime_ascii(ca.get_spacetime_array(), on_char="█", off_char=" "))

# 2D — Conway's Game of Life with a glider
ca = CellularAutomaton(GameOfLifeRule(), width=40, height=20)
place_pattern(ca, get_pattern('glider'), x=5, y=5)
ca.step(100)
print(render_ascii(ca.grid))

# Run with statistics and cycle detection
ca = CellularAutomaton(GameOfLifeRule(), width=30, height=30)
place_pattern(ca, get_pattern('blinker'), x=10, y=10)
stats = ca.run(50)
print(f"Stable: {stats.stable}, cycle: {stats.cycle_detected} (len {stats.cycle_length})")

# Serialize / deserialize
ca.save('state.json')
ca2 = CellularAutomaton.load('state.json')

# Custom rule via Bxx/Sxx notation
from cellular_automaton.rules import get_rule
rule = get_rule('B36/S23')  # HighLife
ca = CellularAutomaton(rule, width=50, height=30)
ca.randomize(0.3, seed=42)

# Custom Python callable rule
from cellular_automaton.rules import CustomRule
def majority(nb):
    return 1 if nb.sum() >= 5 else 0
ca = CellularAutomaton(CustomRule(majority, radius=1, dimensions=2),
                       width=40, height=40)
ca.randomize(0.5)
```

### CLI

```bash
# Run Rule 30 for 30 steps from a centre seed
cellular-automaton run --rule Rule30 --width 80 --steps 30

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

# Save / load state
cellular-automaton save --rule Rule30 --width 50 --steps 10 -o state.json
cellular-automaton load state.json

# Load a pattern from RLE
cellular-automaton run --rule GameOfLife --width 20 --height 20 \
    --rle "bo$2bo$3o!" --px 5 --py 5 --steps 20

# List rules / patterns
cellular-automaton rules
cellular-automaton patterns

# Rule info
cellular-automaton info --rule Rule30
cellular-automaton info --rule GameOfLife
```

## Project structure

```
cellular-automaton/
├── cellular_automaton/
│   ├── __init__.py      # Public API
│   ├── engine.py        # CellularAutomaton core: stepping, stats, serialization
│   ├── rules.py         # Rule classes + registry (271 rules)
│   ├── patterns.py      # 19 builtin patterns + RLE parser
│   ├── vectorized.py    # NumPy-accelerated stepping functions
│   ├── visualizer.py    # ASCII / ANSI / SVG / PPM / PNG / spacetime renderers
│   └── cli.py           # argparse CLI (10 subcommands)
├── examples/
│   ├── 01_rule30.py
│   ├── 02_gosper_gun.py
│   └── 03_highlife.py
├── tests/
├── pyproject.toml
└── README.md
```

## License

MIT
## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **Beacon pattern missing 2 cells** — The `BEACON` pattern had only 6 cells instead of 8 (missing the inner cells at (1,1) and (2,2)). This prevented the beacon from oscillating correctly. **Fix:** Added the missing cells; verified period-2 oscillation with zero boundary.

2. **Pentadecathlon pattern incorrect** — The `PENTADECATHLON` pattern was a plain row of 10 cells (not a period-15 oscillator). The canonical RLE is `2bo4bo$2ob4ob2o$2bo4bo!` (12 cells in 3 rows). **Fix:** Replaced with the correct 12-cell pattern from LifeWiki; verified period-15 oscillation.

3. **`reflect` boundary inconsistency** — The 1D vectorized path used edge/clamp (Neumann zero-gradient) while the 2D vectorized and generic paths used NumPy's `reflect` mode (which mirrors the *second-from-edge* cell). These are different boundary conditions. **Fix:** Changed all paths to use `edge` (clamp/Neumann) for `reflect` boundary, ensuring consistent behaviour across 1D and 2D.

4. **Incorrect births/deaths statistics** — `CAStats.total_births` and `total_deaths` used a heuristic formula `(alive_diff + changed/2)` that produced wrong results. **Fix:** Replaced with exact per-cell comparison: births = `count(dead→alive)`, deaths = `count(alive→dead)`.

5. **`render_png` fallback writes wrong filename** — When PIL is unavailable, `render_png` wrote to `path + ".ppm"` instead of the requested path, causing animation frames to be named `frame_00000.png.ppm`. **Fix:** Writes PPM data to the exact requested path.

6. **`fixed_value > 1` causes `IndexError`** — In the elementary 1D vectorized path, a `fixed_value` greater than 1 produced a 3-bit neighbourhood index exceeding 7, crashing the 8-element lookup table. The 2D vectorized path had a similar issue with non-binary values corrupting neighbour counts. **Fix:** Clamp `fixed_value` to binary (1 if non-zero, else 0) before use.

7. **`from_dict` deserialization fails for custom-named rules** — `get_rule()` raises `KeyError` (not `None`) when a rule isn't found, but `from_dict` checked for `None`, so custom Bxx/Sxx rules stored by name couldn't be deserialized. **Fix:** Use `try/except KeyError` and fall back to `parse_bx_sx_notation()`.