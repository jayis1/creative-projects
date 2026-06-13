# WFC Generator (wfc-generator-q4m7)

A **Wave Function Collapse** (WFC) procedural generation engine implemented in pure Python. WFC is an algorithm that generates random outputs that locally resemble an input or follow explicit adjacency constraints — think dungeon maps, terrain, circuit board patterns, mazes, and more.

## How It Works

The core algorithm is inspired by quantum mechanics:

1. **Superposition**: Start with a grid where every cell can be any possible tile (state)
2. **Observe (Collapse)**: Find the cell with lowest entropy (fewest possibilities) and randomly pick one state, weighted by tile frequency
3. **Propagate**: Remove impossible states from neighboring cells based on adjacency constraints (arc consistency)
4. **Repeat**: Until all cells are collapsed, or a contradiction forces a backtrack/restart

Key implementation features:
- **Shannon entropy** for cell selection with random noise for tie-breaking
- **Arc-consistency propagation** for constraint enforcement
- **Backtracking** on contradiction — restores previous state and tries alternate paths
- **Automatic restart** with fresh random seed when backtracking is exhausted
- **Pre-computed adjacency tables** for fast propagation
- **Generation statistics** tracking (time, collapses, propagations, backtracks)

## Generation Modes

| Mode | Description | Tiles |
|------|-------------|-------|
| `terrain` | Natural terrain with elevation transitions | deep_water, shallow_water, sand, grass, forest, hill, mountain, snow |
| `dungeon` | Dungeon maps with rooms and corridors | floor, wall, corridor, door, pillar, stairs, treasure |
| `city` | City layouts with roads and buildings | road_h, road_v, intersection, building, park, sidewalk, parking |
| `circuit` | Circuit board patterns with wires and components | empty, wire_h, wire_v, wire corners, junction, component, via |
| `maze` | Maze-like patterns | path, wall, dead_end |
| `overlap` | Learn constraints from a sample pattern | Auto-extracted from sample |
| `custom` | Load tile definitions from JSON | User-defined |

## Installation

No external dependencies required — pure Python 3.7+. Optional:

```bash
pip install Pillow  # For PNG rendering
```

## Usage

### Generate a Terrain Map

```bash
python3 wfc.py terrain --width 40 --height 25 --seed 42
```

### Generate a Dungeon with Statistics

```bash
python3 wfc.py dungeon --width 30 --height 20 --stats
```

### Generate a Maze

```bash
python3 wfc.py maze --width 40 --height 30 --seed 7
```

### Output to SVG (Scalable Vector Graphics)

```bash
python3 wfc.py terrain --width 50 --height 35 --output map.svg
```

### Output to PNG (requires Pillow)

```bash
python3 wfc.py circuit --width 25 --height 25 --output circuit.png --cell-size 24
```

### Output to HTML

```bash
python3 wfc.py city --width 25 --height 25 --output city.html
```

### Overlap Model (Learn from Sample)

Create a JSON sample file (`sample.json`):
```json
[
  ["~", "~", ".", "#", "#"],
  ["~", ".", "#", "#", "T"],
  [".", "#", "T", "T", "^"],
  ["#", "T", "^", "^", "^"]
]
```

Generate a new pattern:
```bash
python3 wfc.py overlap --sample sample.json --width 20 --height 20
```

### Custom Tile Set (JSON)

Create a tile set definition (`tiles.json`):
```json
{
  "tiles": [
    {
      "name": "sky",
      "weight": 10,
      "color": "#87ceeb",
      "symbol": " ",
      "constraints": {
        "top": ["sky", "cloud"],
        "right": ["sky", "cloud"],
        "bottom": ["sky", "cloud", "ground"],
        "left": ["sky", "cloud"]
      }
    },
    {
      "name": "cloud",
      "weight": 3,
      "color": "#ffffff",
      "symbol": "☁",
      "constraints": {
        "top": ["sky"],
        "right": ["sky", "cloud"],
        "bottom": ["sky", "ground"],
        "left": ["sky", "cloud"]
      }
    },
    {
      "name": "ground",
      "weight": 8,
      "color": "#8B4513",
      "symbol": "█",
      "constraints": {
        "top": ["sky", "cloud", "ground"],
        "right": ["ground", "sky"],
        "bottom": ["ground"],
        "left": ["ground", "sky"]
      }
    }
  ]
}
```

Generate:
```bash
python3 wfc.py custom --tileset tiles.json --width 20 --height 12 --symmetrize
```

Use `--symmetrize` to automatically make all constraints bidirectional (if A allows B on right, then B allows A on left).

### All Options

| Option | Description |
|--------|-------------|
| `--width` | Grid width (default: 30) |
| `--height` | Grid height (default: 20) |
| `--seed` | Random seed for reproducibility |
| `--periodic` | Use periodic (toroidal) boundary conditions |
| `--output` | Output file path (.html, .svg, .png, or .txt) |
| `--stats` | Print generation statistics |
| `--cell-size` | Cell size in pixels for visual output (default: 16) |

## API Usage

```python
from wfc import TileSet, Tile, WFCGrid, create_terrain_tileset, Renderer

# Use a preset tile set
tileset = create_terrain_tileset()

# Create and run WFC
grid = WFCGrid(tileset, width=30, height=20, seed=42)
success = grid.run()

if success:
    result = grid.get_result()
    print(Renderer.render_plain(result))
    print(f"Stats: {grid.stats}")

# Or define custom tiles
ts = TileSet()
sky = Tile("sky", weight=10, color="#87ceeb", data=" ")
cloud = Tile("cloud", weight=3, color="#ffffff", data="☁")
ground = Tile("ground", weight=8, color="#8B4513", data="█")

sky.add_constraint("bottom", ["sky", "cloud", "ground"])
sky.add_constraint("top", ["sky", "cloud"])
sky.add_constraint("left", ["sky", "cloud"])
sky.add_constraint("right", ["sky", "cloud"])

cloud.add_constraint("top", ["sky"])
cloud.add_constraint("bottom", ["sky", "ground"])
cloud.add_constraint("left", ["sky", "cloud"])
cloud.add_constraint("right", ["sky", "cloud"])

ground.add_constraint("top", ["sky", "cloud", "ground"])
ground.add_constraint("bottom", ["ground"])
ground.add_constraint("left", ["ground", "sky"])
ground.add_constraint("right", ["ground", "sky"])

for t in [sky, cloud, ground]:
    ts.add_tile(t)

ts.make_all_symmetric()  # Auto-symmetrize constraints

grid = WFCGrid(ts, 20, 10, seed=7)
grid.run()
result = grid.get_result()
print(Renderer.render_colored(result))
```

### Overlap Model API

```python
from wfc import OverlapModel

# Learn from a sample pattern
sample = [
    ["~", "~", ".", "#"],
    [".", "#", "#", "T"],
    ["#", "T", "T", "^"],
]

model = OverlapModel(sample, n=2)
result = model.generate(width=15, height=10, seed=42)
if result:
    for row in result:
        print("".join(row))
```

### Progress Callback

```python
from wfc import TileSet, WFCGrid, create_dungeon_tileset

def on_progress(fraction):
    print(f"\rProgress: {fraction:.1%}", end="", flush=True)

tileset = create_dungeon_tileset()
grid = WFCGrid(tileset, 50, 40, on_progress=on_progress)
grid.run()
print()  # newline after progress
```

## Architecture

```
wfc.py
├── Tile             - Tile definition with adjacency constraints, color, data
├── TileSet          - Collection of tiles with validation, JSON I/O, symmetrization
├── GenerationStats  - Statistics tracking (time, collapses, backtracks)
├── WFCGrid          - Core WFC algorithm (collapse, propagate, backtrack)
│   ├── entropy()      - Shannon entropy with noise for tie-breaking
│   ├── propagate()    - Arc-consistency constraint propagation
│   ├── _backtrack()   - State restoration on contradiction
│   └── run()          - Full generation with restart support
├── OverlapModel     - Learn constraints from sample patterns
│   ├── _extract_patterns()  - Extract NxN sub-patterns
│   └── _build_constraints() - Build adjacency from overlaps
├── Renderer         - Multi-format rendering (ANSI, plain, HTML, SVG, PNG)
│   ├── render_colored()  - ANSI-colored terminal output
│   ├── render_plain()    - Plain text output
│   ├── render_html()     - HTML table with colors
│   ├── render_svg()      - SVG image with colored cells
│   └── render_png()      - PNG image (requires Pillow)
├── create_*_tileset - Preset tile set generators
│   ├── create_terrain_tileset()
│   ├── create_dungeon_tileset()
│   ├── create_city_tileset()
│   ├── create_circuit_tileset()
│   └── create_maze_tileset()
└── main()           - CLI entry point with subcommands
```

## Rendering Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| ANSI | (terminal) | Colored output in terminal |
| Plain text | .txt | Simple character grid |
| HTML | .html | Colored HTML table |
| SVG | .svg | Scalable vector graphics |
| PNG | .png | Raster image (requires Pillow) |

## Known Issues (Resolved)

The following bugs were identified during code review and have been fixed:

1. **`add_rotated_variants` didn't remap tile name references** — When creating rotated tile variants, constraint side mappings were rotated correctly, but the tile names referenced *within* those constraints still pointed to the original tile instead of the corresponding rotated variant. For example, a 90°-rotated "path_h" tile would still reference "path_h" in its constraints instead of "path_h_r90". This caused incorrect adjacency in generated patterns. **Fix**: The method now remaps internal tile name references to their rotated counterparts using a name mapping table.

2. **OverlapModel didn't validate pattern size `n`** — The OverlapModel constructor accepted `n` values larger than the sample dimensions (non-periodic) or negative/zero values without raising an error, leading to cryptic failures during generation. **Fix**: Added validation that `n >= 1` and `n <= sample_width/sample_height` for non-periodic samples.

3. **Custom mode didn't check generation success** — The `custom` CLI subcommand retrieved the result via `get_result()` without first checking if `run()` succeeded, potentially attempting to render a `None` result. **Fix**: Added success check and error handling matching the other modes.

4. **Propagation treated empty constraint sets as "skip"** — When a tile had empty constraints on a side, the propagation code skipped restricting the neighbor entirely (effectively treating it as a wildcard). This was semantically ambiguous. **Fix**: Empty constraints now explicitly map to "allow all tiles" with a clear comment explaining the design choice, making the behavior documented and intentional rather than accidental.

5. **Negative tile weights accepted without validation** — Negative weights would cause issues with weighted random selection (cumulative distribution can go backwards). **Fix**: Added validation in both `WFCGrid.__init__` and `TileSet.from_json` to reject negative weights with a clear error message.

6. **JSON tileset loading lacked validation** — Missing `name` field in tile definitions would cause a `KeyError` rather than a helpful error message. **Fix**: `from_json` now validates that each tile has a `name` field and rejects negative weights from JSON input.

## License

MIT