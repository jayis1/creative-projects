# Cellular Automaton Simulator

A from-scratch 1D & 2D cellular automaton (CA) engine in pure Python (NumPy-backed), supporting all 256 of Wolfram's elementary rules, 15 Life-like rule variants, custom user-defined rules, 19 classic patterns, and multi-format rendering (ASCII / ANSI / SVG / PPM / PNG).

## Features

### Rules
- **256 Elementary 1D rules** — Wolfram's radius-1 rules (Rule 0–255), including the famous Rule 30 (chaotic), Rule 90 (Sierpinski), Rule 110 (Turing-complete), and Rule 184 (traffic flow).
- **15 Life-like 2D rules** — Conway's Game of Life (B3/S23), HighLife (B36/S23), Seeds (B2/S), Day & Night (B3678/S34678), Replicator, Maze, Mazectric, Anneal, Coral, Diamoeba, Majority, WalledCities, Gnarl, and more.
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
- **SVG** — vector graphics.
- **PPM / PNG** — raster image output (PNG requires Pillow).

### Engine
- Efficient NumPy-backed grids.
- Step history (undo support via history stack).
- Cycle/stability detection.
- State hashing for cycle detection.
- Deep-copy support.

## How it works

### 1D Elementary Rules
Each cell looks at itself and its two immediate neighbours (radius 1), forming a 3-bit pattern (000–111, 8 combinations). The rule number's 8-bit binary representation specifies the output for each pattern. For example, Rule 30 = `00011110` in binary, so pattern `111→0, 110→0, 101→0, 100→1, 011→1, 010→1, 001→1, 000→0`.

### 2D Life-like Rules
Each cell examines its 8 Moore neighbours. The `birth` set specifies neighbour counts that spawn a dead cell to life; the `survive` set specifies counts that keep a live cell alive. All other cells die or stay dead.

## Installation

```bash
cd cellular-automaton
pip install -e .          # installs numpy + CLI entry point
# Optional PNG support:
pip install -e ".[png]"
```

## Usage

### Python API

```python
from cellular_automaton import (
    CellularAutomaton, ElementaryRule, GameOfLifeRule,
    get_pattern, place_pattern, render_ascii,
)

# 1D — Wolfram's Rule 30 from a single centre cell
ca = CellularAutomaton(ElementaryRule(30), width=80)
ca.center_seed()
for _ in range(40):
    print(render_ascii(ca.grid).replace(' ', '.').replace('#', '█'))
    ca.step()

# 2D — Conway's Game of Life with a glider
ca = CellularAutomaton(GameOfLifeRule(), width=40, height=20)
place_pattern(ca, get_pattern('glider'), x=5, y=5)
ca.step(100)
print(render_ascii(ca.grid))

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
│   ├── engine.py        # CellularAutomaton core engine
│   ├── rules.py         # Rule classes + registry (271 rules)
│   ├── patterns.py      # 19 builtin patterns + RLE parser
│   ├── visualizer.py    # ASCII / ANSI / SVG / PPM / PNG renderers
│   └── cli.py           # argparse CLI (5 subcommands)
├── tests/
├── examples/
├── pyproject.toml
└── README.md
```

## License

MIT