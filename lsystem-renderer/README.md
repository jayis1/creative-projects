# L-System Renderer — `lsystem-renderer-q4m7`

A **Lindenmayer System (L-System) renderer** — a formal grammar-based generative art engine that produces fractals, plant-like structures, and complex geometric patterns through string rewriting and turtle graphics interpretation.

## How It Works

L-systems work through **parallel string rewriting**: starting from an initial string (axiom), production rules are simultaneously applied to each symbol across multiple iterations. The resulting string is then interpreted as turtle graphics commands to produce 2D line art.

### Supported Features

| Feature | Description |
|---------|-------------|
| **Deterministic L-systems** | Standard one-symbol → one-replacement rules |
| **Stochastic L-systems** | Rules with probability weights for organic variation |
| **Context-sensitive L-systems** | Rules that consider neighboring symbols (ignoring brackets) |
| **Parametric L-systems** | Rules with Python-evaluated conditions |
| **SVG rendering** | High-quality vector output with auto-scaling, centering, and grouped paths |
| **SVG animation** | Progressive draw animation with opacity transitions |
| **ASCII rendering** | Terminal-friendly character-based output with directional chars |
| **Depth-based coloring** | Branches colored by recursion depth for plant-like visuals |
| **Gradient coloring** | Linear color interpolation across position or segment order |
| **Rainbow coloring** | HSL rainbow mapped to segment order for curves |
| **Perturbation/noise** | Random angle and step-size perturbation for organic variation |
| **JSON import/export** | Save and load L-system definitions as JSON files |
| **Batch rendering** | Render all presets at once with `--render-all` |
| **Growth animation** | Render each iteration step as a separate SVG for growth visualization |
| **String statistics** | Analyze L-system strings: length, symbol counts, drawing symbols |
| **14 built-in presets** | Classic fractals, plants, curves, and more |

### Turtle Command Reference

| Symbol | Action |
|--------|--------|
| `F`, `G` | Move forward and draw a line |
| `f` | Move forward without drawing |
| `+` | Turn left by the angle increment |
| `-` | Turn right by the angle increment |
| `[` | Push turtle state (start branch) |
| `]` | Pop turtle state (end branch) |
| `\|` | Reverse direction (turn 180°) |
| `#` | Increase line width |
| `!` | Decrease line width |
| `<` | Halve step size |
| `>` | Double step size |
| `(` | Decrease step size by factor |
| `)` | Increase step size by factor |

## Built-in Presets

| Preset Name | Description | Color Mode |
|------------|-------------|------------|
| `koch_curve` | Classic Koch curve fractal | depth |
| `koch_snowflake` | Koch snowflake (three Koch curves) | depth |
| `sierpinski_triangle` | Sierpiński triangle | depth |
| `dragon_curve` | Dragon curve (Heighway dragon) | rainbow |
| `hilbert_curve` | Hilbert space-filling curve | rainbow |
| `plant_simple` | Simple branching plant | depth |
| `plant_stochastic` | Stochastic plant (varies each run) | depth |
| `tree_bushy` | Bushy fractal tree | depth |
| `penrose_tiles` | Penrose tiling pattern | depth |
| `levy_c_curve` | Lévy C curve | rainbow |
| `gosper_curve` | Gosper/flowsnake curve | rainbow |
| `fractal_tree` | Fractal tree (branching) | depth |
| `barnsley_fern` | Barnsley fern (approximation) | depth |
| `cantor_dust` | Cantor dust fractal | single |

## Usage

### Command Line

```bash
# Render a Koch snowflake to SVG
python3 lsystem.py --preset koch_snowflake -i 4 -o koch.svg

# Render a stochastic plant with seed for reproducibility
python3 lsystem.py --preset plant_stochastic -i 5 --seed 42 -o plant.svg

# Render dragon curve as ASCII art
python3 lsystem.py --preset dragon_curve -i 10 --backend ascii -o dragon.txt

# Render with rainbow color mode
python3 lsystem.py --preset hilbert_curve -i 5 --color-mode segment_index -o hilbert.svg

# Render with gradient (bottom=red, top=blue)
python3 lsystem.py --preset plant_simple -i 5 --color-mode position --gradient "#ff0000,#0000ff" -o gradient.svg

# Add organic perturbation (angle noise ±3°)
python3 lsystem.py --preset tree_bushy -i 4 --perturbation 3.0 -o organic.svg

# Render all presets at once
python3 lsystem.py --render-all -d ./output

# Animate growth steps (step_0.svg, step_1.svg, ...)
python3 lsystem.py --preset koch_snowflake --animate-steps -d ./growth

# Generate animated SVG (progressive draw)
python3 lsystem.py --preset plant_simple -i 5 --animate -o growing.svg

# Print string statistics
python3 lsystem.py --preset dragon_curve -i 12 --stats

# List all presets
python3 lsystem.py --list-presets

# Custom L-system (Sierpinski arrowhead)
python3 lsystem.py --axiom "A" --rule "A->B-A-B" --rule "B->A+B+A" --angle 60 -i 7 -o custom.svg

# Load from JSON definition
python3 lsystem.py --load my_definition.json -o output.svg

# Save definition to JSON (no rendering)
python3 lsystem.py --preset koch_snowflake --save koch.json
```

### Python API

```python
from lsystem import (
    LSystemRenderer, LSystemDefinition, LSystemRule,
    LSystemEngine, SVGRenderer, ASCIIRenderer,
    ColorPostProcessor, hex_to_rgb, lerp_color
)

renderer = LSystemRenderer(seed=42)

# Use a preset
renderer.render("koch_snowflake", iterations=4, output="koch.svg")

# Define a custom L-system
custom = LSystemDefinition(
    name="My Fractal",
    axiom="F",
    rules=[LSystemRule("F", "F+F-F-F+F")],
    angle=90.0,
    step_size=5.0,
    iterations=4,
    colors={0: "#ff6600", 1: "#ff3300"},
)
renderer.render(custom, output="custom.svg")

# Rainbow color mode
rainbow_def = LSystemDefinition(
    name="Rainbow Dragon",
    axiom="F",
    rules=[LSystemRule("F", "F+G"), LSystemRule("G", "F-G")],
    angle=90.0,
    step_size=5.0,
    iterations=12,
    color_mode="segment_index",
)
renderer.render(rainbow_def, output="rainbow_dragon.svg")

# Gradient coloring (position-based)
gradient_def = LSystemDefinition(
    name="Gradient Plant",
    axiom="F",
    rules=[LSystemRule("F", "F[+F]F[-F]F")],
    angle=25.7,
    step_size=4.0,
    iterations=5,
    color_mode="position",
    gradient=("#1a5c1a", "#adff2f"),
)
renderer.render(gradient_def, output="gradient_plant.svg")

# Organic perturbation
organic_def = LSystemDefinition(
    name="Organic Tree",
    axiom="F",
    rules=[LSystemRule("F", "FF+[+F-F-F]-[-F+F+F]")],
    angle=22.5,
    step_size=4.0,
    iterations=4,
    perturbation=3.0,      # ±3° angle noise
    step_perturbation=0.1,  # ±10% step noise
)
renderer.render(organic_def, seed=42, output="organic.svg")

# Save/load definitions as JSON
custom.to_json("my_fractal.json")
loaded = LSystemDefinition.from_json("my_fractal.json")

# Analyze string statistics
engine = LSystemEngine(custom)
lstring = engine.iterate(4)
stats = LSystemEngine.analyze(lstring)
print(f"Length: {stats['length']}, Drawing symbols: {stats['draw_symbols']}")

# Render all presets at once
results = renderer.render_all_presets(output_dir="./gallery")
for name, path in results.items():
    print(f"{name}: {path}")

# Render growth steps
steps = renderer.animate_growth("koch_snowflake", output_dir="./growth", iterations=4)
print(f"Generated {len(steps)} step files")
```

## Architecture

```
lsystem.py
├── LSystemDefinition   — Data class: axiom, rules, angle, colors, perturbation
├── LSystemRule          — Single production rule with optional probability/context
├── LSystemEngine        — Core string rewriting (iterate, iterate_steps, analyze)
├── TurtleInterpreter    — Converts L-system string → Segments (with perturbation)
├── ColorPostProcessor   — Applies depth/gradient/rainbow coloring to segments
├── SVGRenderer          — Segments → SVG (grouped paths, animation support)
├── ASCIIRenderer        — Segments → ASCII art with directional characters
├── LSystemRenderer      — High-level API (render, render_all, animate_growth)
├── Color utilities      — hex_to_rgb, rgb_to_hex, lerp_color, hsl_to_rgb, rainbow_color
├── PRESETS dict          — 14 built-in L-system definitions
└── CLI (main)           — Full-featured argparse CLI
```

## Requirements

- Python 3.7+ (no external dependencies — uses only stdlib)

## Known Issues (Resolved)

The following bugs were identified during Phase 3 bug hunting and have been fixed:

1. **`lerp_color` rounding error** — Used `int()` (truncation) instead of `round()` for color interpolation, causing `lerp_color("#000000", "#ffffff", 0.5)` to return `#7f7f7f` instead of `#808080`. Fixed by switching to `round()`.

2. **SVG title XSS/malformed XML** — SVG `<title>` and `<desc>` elements contained unescaped XML special characters (`<`, `>`, `&`), which could produce malformed SVG or allow XSS in browser contexts. Fixed by adding `_escape_xml()` helper that escapes `&`, `<`, `>`, `"`, and `'`.

3. **SVG path grouping lost width variation** — When grouping segments by color for compact SVG output, all segments in a group were rendered with the first segment's `stroke-width`, losing width variation within same-colored segments. Fixed by grouping by `(color, rounded_width)` tuple instead of just `color`.

4. **`iterate_steps` missing validation** — The `iterate_steps()` method did not validate negative iterations, unlike `iterate()`. Fixed by adding the same `ValueError` check for `n < 0`.

5. **CLI `--render-all` required preset** — The `--render-all` flag required `--preset` or `--axiom` to be specified, defeating the purpose of rendering all presets. Fixed by moving the `--render-all` handler before the definition resolution logic.

6. **ASCII output path for extensionless filenames** — When the output filename had no extension (e.g., `output`), the ASCII backend would produce incorrect paths. Fixed by checking for dots in the basename before replacing extensions.

7. **Duplicate iteration validation** — `iterate_steps()` had a duplicated `if n < 0` check after the fix. Removed the duplicate.

## Testing

Run the test suite:

```bash
python3 -m pytest test_lsystem.py -v
```

71 tests covering:
- Color utilities (hex_to_rgb, lerp_color, hsl_to_rgb, rainbow_color)
- L-system rule serialization/deserialization
- L-system definition JSON round-trips
- String rewriting engine (deterministic, stochastic, context-sensitive)
- Turtle interpreter (drawing, turning, branching, perturbation)
- Color post-processing (depth, position gradient, rainbow, single)
- SVG and ASCII rendering
- High-level renderer API
- All 14 presets (SVG and ASCII)
- Edge cases (empty axiom, deep nesting, zero angle, extra pops)
- Bug verification tests for all fixed issues

## License

MIT