# 🐠 Terminal Aquarium

A beautiful animated aquarium that lives in your terminal. Watch procedurally generated fish swim, plants sway, and bubbles rise — all rendered in glorious curses-based ASCII art with color.

![Terminal Aquarium](https://img.shields.io/badge/type-visualization-blue) ![Python](https://img.shields.io/badge/python-3.8+-green) ![Curses](https://img.shields.io/badge/ui-curses-orange)

## Features

- **10 fish species** — Neon Tetra, Guppy, Angelfish, Clownfish, Betta, Goldfish, Discus, Danio, Pufferfish, and Swordtail, each with unique colors, sizes, and swimming behaviors
- **Procedural animation** — Fish swim with natural wobble, vertical drift, and random direction changes
- **5 plant species** — Anubias, Java Fern, Hornwort, Vallisneria, and Cryptocoryne that sway with simulated current
- **Dynamic bubbles** — Rise from the bottom and from fish mouths, with wobble physics
- **Interactive feeding** — Drop food that sinks slowly; fish detect and swim toward it
- **Light rays** — Animated light shafts penetrate the water from above
- **Depth gradient** — Water color darkens with depth for a realistic look
- **Named fish** — Each fish gets a randomly chosen name (Bubbles, Nemo, Dory, etc.)
- **Interactive controls** — Feed, spawn fish, burst bubbles, scare fish, pause, and view the resident list

## How to Install

```bash
# No external dependencies needed — uses only Python standard library
# Just clone and run!

git clone <repo-url>
cd 2026-06-13-terminal-aquarium
```

Requirements:
- Python 3.8+
- A terminal that supports curses (most Linux/macOS terminals do)
- Terminal with color support recommended (256-color for best experience)

## How to Run

```bash
python3 aquarium.py
```

## Controls

| Key | Action |
|-----|--------|
| `F` | Drop food into the aquarium |
| `S` | Spawn a new fish |
| `B` | Burst of bubbles |
| `R` | Scare all fish (they scatter!) |
| `I` | Toggle resident info display |
| `P` | Pause/resume the aquarium |
| `Q` | Quit |

## What It Does

Terminal Aquarium creates a self-contained animated aquatic ecosystem in your terminal:

1. **On startup**, the aquarium populates with 8–14 randomly chosen fish, 4–8 plants, 2–4 rocks, and a sand floor. The water is rendered with a depth gradient and animated surface ripples.

2. **Fish AI** — Each fish swims with sinusoidal vertical wobble, random direction changes, and vertical drift. When food is present, fish detect nearby food particles and swim toward them to eat. Fish bounce off the aquarium walls.

3. **Plants** — Each plant is rendered as a vertical column of characters that sway sinusoidally based on time, with leaf segments branching off periodically.

4. **Bubbles** — Spawn randomly from the bottom and from fish mouths. Each bubble has its own wobble frequency and rise speed.

5. **Light rays** — Animated diagonal light shafts move across the aquarium, fading with depth.

6. **Food** — When you press `F`, 3–7 food particles drop from the surface. They sink slowly with horizontal drift. Fish within 20 units will target and eat them. Uneaten food expires after 15 seconds.

## Usage Examples

```
# Run with default settings
python3 aquarium.py

# The aquarium will show:
# - A header bar with fish count, bubble count, food count, and elapsed time
# - An animated water surface with wave characters
# - Fish swimming around with unique colors and patterns
# - Plants swaying at the bottom
# - Bubbles rising

# Press F to feed — watch fish swarm toward food
# Press S to add more fish — up to dozens
# Press B for a satisfying bubble burst
# Press R to scare them — they scatter to the sides!
```

## Technical Details

- **Rendering**: Uses `curses` for terminal rendering at ~15 FPS
- **Color system**: Dynamic RGB color registration with curses `init_color`/`init_pair`, falling back to basic colors when custom colors aren't supported
- **Fish data**: Each fish is a `@dataclass` with species, size, speed, direction, wobble parameters, and color attributes
- **Physics**: Simple Euler integration for fish movement with sinusoidal wobble, random impulses, and boundary reflection
- **No external dependencies** — pure Python standard library

## License

MIT