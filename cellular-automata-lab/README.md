# CellLab — Interactive Cellular Automata Laboratory

Explore the emergent beauty of cellular automata right in your terminal. CellLab supports both **1D elementary automata** (Wolfram rules 0–255) and **2D Life-like automata** (10 presets + custom rules) with an interactive curses UI or a non-interactive render mode for scripting and screenshots.

## Features

- **1D Elementary Cellular Automata** — Browse all 256 Wolfram rules interactively, with instant switching
- **2D Life-like Automata** — 10 curated presets including Conway's Game of Life, HighLife, Seeds, Diamoeba, Coral, Maze, and more
- **Interactive curses UI** — Real-time simulation with play/pause, speed control, cell drawing, and cursor navigation
- **Age-based coloring** — Cells change color based on how long they've been alive (new → old: green → yellow → red → magenta → white)
- **Preset patterns** — Gosper glider gun, pulsar, lightweight spaceship, and random fills
- **Non-interactive mode** — Render automata directly to the terminal for piping, screenshots, or scripting
- **Drawing mode** — Toggle individual cells on/off with the cursor to create your own starting states

## Installation

No external dependencies required — CellLab uses only the Python standard library.

```bash
# Clone and run
git clone https://github.com/your-username/daily-ideas.git
cd daily-ideas/2026-06-13-cellular-automata-lab

# Make executable (optional)
chmod +x cellab.py
```

Requires Python 3.7+ with `curses` (included on macOS/Linux by default).

## How to Run

### Interactive Mode (default)

```bash
# Start with 2D Game of Life (default)
python3 cellab.py

# Start in 1D mode
python3 cellab.py --one-d

# Start 1D mode with specific rule
python3 cellab.py --one-d --rule 30

# Start with a specific 2D preset
python3 cellab.py --preset highlife
```

### Non-interactive Rendering

```bash
# Render 1D Rule 90 (Sierpinski triangle)
python3 cellab.py --render-1d 90 --width 80 --height 30

# Render 2D Game of Life
python3 cellab.py --render-2d life --width 60 --height 25 --steps 50

# Render with custom speed
python3 cellab.py --render-2d seeds --steps 100 --delay 0.03

# Static snapshot (no animation)
python3 cellab.py --render-2d maze --steps 30 --no-animate
```

### Information

```bash
# List all 2D presets
python3 cellab.py --list-presets

# List notable 1D rules
python3 cellab.py --list-rules
```

## Interactive Controls

### Global Controls

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `.` | Step forward one generation (auto-pauses) |
| `+` / `-` | Increase / decrease simulation speed |
| `Tab` | Switch between 1D and 2D mode |
| `r` | Reset (1D: center seed, 2D: current pattern) |
| `R` | Reset with random seed |
| `q` / `Esc` | Quit |

### 1D Mode Controls

| Key | Action |
|-----|--------|
| `n` | Next rule (increment by 1) |
| `p` | Previous rule (decrement by 1) |
| `0` | Jump to Rule 0 |
| `3` | Jump to Rule 30 |
| `9` | Jump to Rule 90 |
| `1` | Jump to Rule 110 |

### 2D Mode Controls

| Key | Action |
|-----|--------|
| `n` | Next preset |
| `p` | Previous preset |
| `g` | Load Gosper glider gun pattern |
| `u` | Load pulsar pattern |
| `l` | Load lightweight spaceship (LWSS) |
| `d` | Toggle drawing mode |
| `e` | Toggle cell under cursor |
| Arrow keys / WASD | Move cursor (in drawing mode) |

## 2D Presets

| Name | Rule | Description |
|------|------|-------------|
| life | B3/S23 | Conway's Game of Life — the classic |
| highlife | B36/S23 | HighLife — features replicators |
| seeds | B2/S | Seeds — explosive, chaotic growth |
| daynight | B3678/S34678 | Day & Night — symmetric patterns |
| diamoeba | B35678/S5678 | Diamoeba — blobby growth |
| maze | B3/S12345 | Maze — generates maze-like structures |
| coral | B3/S45678 | Coral — slow, organic growth |
| anneal | B4678/S35678 | Anneal — smooths initial noise |
| 2x2 | B36/S125 | 2x2 — creates blocky patterns |
| replicator | B1357/S1357 | Replicator — every pattern copies itself |

## What It Does

CellLab is a cellular automata sandbox that lets you watch complexity emerge from simple rules. In **1D mode**, each row is a generation of a Wolfram elementary automaton — you can scroll through all 256 rules and watch patterns like the Sierpinski triangle (Rule 90) and chaotic randomness (Rule 30) unfold. In **2D mode**, you can explore the entire family of "Life-like" rules — each defined by which neighbor counts cause a dead cell to be born (B) or a live cell to survive (S). The age-based coloring reveals the dynamics of growth and decay at a glance.

The project demonstrates how simple local rules produce global emergent behavior, a core concept in complexity science, artificial life, and theoretical computer science (Rule 110 is Turing-complete!).