# Parity Game Solver

A dependency-free solver for finite two-player parity games. Vertices carry an owner and a non-negative priority; players move a token along directed edges forever. The player whose parity occurs infinitely often at the highest recurring priority wins.

## How it works

Zielonka's recursive algorithm finds the highest priority, computes the owning player's attractor, solves the remaining subgame, and recursively removes the opponent's counter-attractor when needed. The attractor is a least fixed point: a player's vertices need one route into the target, while opponent vertices need every available route there.

## Usage

Create a JSON file with parallel maps for vertex owners, priorities, and outgoing edges:

```json
{"owners":{"0":0},"priorities":{"0":2},"edges":{"0":[0]}}
```

Run `python3 solver.py game.json`. Output is JSON containing each player's winning region and a positional strategy where constructed. Malformed games (including dead ends and dangling edges) return exit code 2 with a diagnostic. No network or third-party packages required.

Run tests with `python3 -m unittest discover -s tests -v`.
