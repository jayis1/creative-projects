# MCTS Engine — Monte Carlo Tree Search for Game AI

A from-scratch implementation of Monte Carlo Tree Search (MCTS) supporting multiple games with UCT, RAVE/AMAF, transposition tables, and parallel search.

## Overview

MCTS is a heuristic search algorithm for decision processes, most notably used in game AI (e.g., AlphaGo). It builds a partial game tree through four phases:

1. **Selection** — Traverse the tree from root to leaf using a selection policy (UCT or RAVE)
2. **Expansion** — Add a new child node for an untried move
3. **Simulation** — Roll out a random playout to a terminal state
4. **Backpropagation** — Update visit counts and rewards up the path to the root

## Features

- **5 games**: Tic-Tac-Toe, Connect Four, Gomoku (Five-in-a-Row), Reversi/Othello, Hex
- **2 selection policies**:
  - **UCT** (Upper Confidence bounds applied to Trees) — classic UCB1 formula
  - **RAVE** (Rapid Action Value Estimation) — blends MCTS values with AMAF estimates for faster convergence
- **Parallel search** — root parallelization with tree merging across threads
- **Transposition tables** — share statistics across identical states reachable by different move orders
- **Configurable** — simulation limits, time limits, max depth, exploration constants
- **Interactive play** — human vs. AI, self-play, and benchmarking modes
- **Pure Python** — no external dependencies

## Installation

```bash
cd mcts-engine
pip install -e .
```

Or simply run from the directory (Python 3.10+).

## Usage

### Play against the AI

```bash
python -m mcts play --game tictactoe --sims 5000
python -m mcts play --game connect4 --sims 10000 --rave
python -m mcts play --game hex --size 7 --sims 20000 --time-limit 5
```

### Self-play (engine vs. engine)

```bash
python -m mcts selfplay --game tictactoe --sims 2000 --verbose
```

### Benchmark different configurations

```bash
python -m mcts benchmark --game tictactoe --sims 5000 --rounds 10 --rave
```

### List available games

```bash
python -m mcts list
```

### Parallel search

```bash
python -m mcts play --game connect4 --sims 20000 --parallel 4
```

## Python API

```python
from mcts import MCTSEngine, TicTacToe, UCTPolicy

# Create a game
game = TicTacToe()

# Create engine with UCT
engine = MCTSEngine(
    selection_policy=UCTPolicy(exploration=1.4142),
    simulation_limit=10000,
    seed=42,
)

# Search for best move
result = engine.search(game)
print(f"Best move: {result.best_move}")
print(f"Win rate: {result.win_rate:.1%}")
print(f"Simulations: {result.simulations}")
print(f"Principal variation: {result.principal_variation}")

# Use RAVE
from mcts import RAVEPolicy
engine_rave = MCTSEngine(
    selection_policy=RAVEPolicy(exploration=1.4142, rave_k=300),
    simulation_limit=10000,
    rave=True,
    seed=42,
)
result = engine_rave.search(game)

# Parallel search
result = engine.search_parallel(game, num_threads=4)
```

## How It Works

### UCT Selection

The UCB1 formula balances exploitation and exploration:

```
UCB1 = (total_reward / visits) + c * sqrt(ln(parent_visits) / visits)
```

- `c` = exploration constant (default √2 ≈ 1.4142)
- Unvisited nodes return +∞, ensuring all children are tried at least once

### RAVE / AMAF

RAVE (Rapid Action Value Estimation) uses the AMAF (All Moves As First) heuristic: if a move `m` was played during a rollout and led to a win, we update not just the node for `m` in the tree, but also the AMAF statistics for any child with move `m` along the backpropagation path. This provides faster value estimates early in the search when visit counts are low.

The blended value is:

```
β = N_amaf / (N_visits + N_amaf + 4·k·N_visits·N_amaf / (N_visits + N_amaf + 4·k))
value = (1 - β) · MCTS_avg + β · AMAF_avg + exploration
```

### Parallel Search

Root parallelization runs independent MCTS searches in separate threads, each with its own RNG seed, then merges the resulting trees by summing visit counts and rewards. This provides near-linear speedup with thread count.

## Games

| Game | Board | Win Condition |
|------|-------|---------------|
| Tic-Tac-Toe | 3×3 | 3 in a row |
| Connect Four | 6×7 | 4 in a row (gravity) |
| Gomoku | 15×15 | 5 in a row |
| Reversi/Othello | 8×8 | Most pieces at end |
| Hex | 11×11 | Connect your two sides |

## Project Structure

```
mcts-engine/
├── mcts/
│   ├── __init__.py      # Package exports
│   ├── __main__.py      # CLI entry point
│   ├── core.py          # GameState, MCTSNode, MCTSResult
│   ├── engine.py        # MCTSEngine, TranspositionTable
│   ├── games.py         # 5 game implementations
│   ├── uct.py           # UCTPolicy, RAVEPolicy, SelectionPolicy
│   ├── rave.py          # RAVE re-export
│   └── cli.py           # Command-line interface
├── README.md
└── pyproject.toml
```

## License

MIT