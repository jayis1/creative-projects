# MCTS Engine — Monte Carlo Tree Search for Game AI

A from-scratch implementation of Monte Carlo Tree Search (MCTS) supporting multiple games with UCT, RAVE/AMAF, transposition tables, progressive bias, heuristic-guided rollouts, tree reuse, and parallel search.

## Overview

MCTS is a heuristic search algorithm for decision processes, most notably used in game AI (e.g., AlphaGo). It builds a partial game tree through four phases:

1. **Selection** — Traverse the tree from root to leaf using a selection policy (UCT or RAVE)
2. **Expansion** — Add a new child node for an untried move
3. **Simulation** — Roll out a playout to a terminal state (random or heuristic-guided)
4. **Backpropagation** — Update visit counts and rewards up the path to the root

## Features

- **5 games**: Tic-Tac-Toe, Connect Four, Gomoku (Five-in-a-Row), Reversi/Othello, Hex
- **2 selection policies**:
  - **UCT** (Upper Confidence bounds applied to Trees) — classic UCB1 formula
  - **RAVE** (Rapid Action Value Estimation) — blends MCTS values with AMAF estimates for faster convergence
- **5 game-specific heuristics**: threat counting (TicTacToe), window analysis (Connect4), corner/mobility (Reversi), shortest-path (Hex), pattern matching (Gomoku)
- **Progressive bias**: Inject heuristic priors into newly expanded nodes to guide early search
- **Heuristic-guided rollouts**: Epsilon-greedy rollout policy using game-specific heuristics
- **Tree reuse**: Reuse subtrees from previous searches between moves
- **Parallel search**: Root parallelization with tree merging across threads
- **Transposition tables**: Share statistics across identical states reachable by different move orders
- **Game records**: Full move history with search statistics, JSON serialization, text export
- **Search statistics**: Per-search and cumulative stats (simulations, time, tree size, win rates)
- **Configurable**: Simulation limits, time limits, max depth, exploration constants, rollout limit
- **Interactive play**: Human vs. AI, self-play with recording, benchmarking, position analysis, replay
- **Pure Python**: No external dependencies

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
python -m mcts play --game tictactoe --heuristic --sims 5000
python -m mcts play --game connect4 --sims 20000 --parallel 4 --tree-reuse
```

### Self-play (engine vs. engine)

```bash
python -m mcts selfplay --game tictactoe --sims 2000 --verbose
python -m mcts selfplay --game connect4 --sims 5000 --save game.json
```

### Benchmark different configurations

```bash
python -m mcts benchmark --game tictactoe --sims 5000 --rounds 10 --rave
python -m mcts benchmark --game connect4 --sims 5000 --rounds 10 --heuristic
```

### Analyze a position

```bash
python -m mcts analyze --game tictactoe --sims 5000 --verbose
python -m mcts analyze --game hex --size 7 --sims 10000 --heuristic
```

### Replay a saved game

```bash
python -m mcts replay game.json
```

### List available games

```bash
python -m mcts list
```

## Python API

```python
from mcts import MCTSEngine, TicTacToe, UCTPolicy, RAVEPolicy
from mcts import get_heuristic, make_rollout_policy, GameRecord, play_recorded_game

# Create a game
game = TicTacToe()

# Basic UCT search
engine = MCTSEngine(
    selection_policy=UCTPolicy(exploration=1.4142),
    simulation_limit=10000,
    seed=42,
)
result = engine.search(game)
print(f"Best move: {result.best_move}")
print(f"Win rate: {result.win_rate:.1%}")
print(f"Simulations: {result.simulations}")
print(f"Principal variation: {result.principal_variation}")

# RAVE search
engine_rave = MCTSEngine(
    selection_policy=RAVEPolicy(exploration=1.4142, rave_k=300),
    simulation_limit=10000,
    rave=True,
    seed=42,
)
result = engine_rave.search(game)

# Heuristic-guided search with progressive bias
heuristic = get_heuristic("tictactoe")
engine_heuristic = MCTSEngine(
    selection_policy=UCTPolicy(1.4142),
    simulation_limit=10000,
    progressive_bias=1.0,
    heuristic_fn=heuristic,
    seed=42,
)
result = engine_heuristic.search(game)

# Heuristic-guided rollouts (epsilon-greedy)
rollout = make_rollout_policy(heuristic, epsilon=0.2)
engine_rollout = MCTSEngine(
    simulation_limit=10000,
    rollout_policy=rollout,
    seed=42,
)
result = engine_rollout.search(game)

# Tree reuse between moves
engine_reuse = MCTSEngine(
    simulation_limit=5000,
    tree_reuse=True,
    seed=42,
)
result1 = engine_reuse.search(game)
game2 = game.apply(result1.best_move)
result2 = engine_reuse.search(game2)  # reuses subtree from first search

# Parallel search
result = engine.search_parallel(game, num_threads=4)

# Play and record a full game
final_state, record = play_recorded_game(game, engine, game_type="tictactoe")
print(record.to_text())
record.save("my_game.json")
loaded = GameRecord.load("my_game.json")

# Search statistics
print(engine.stats.summary())
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

### Progressive Bias

Progressive bias injects heuristic knowledge into the tree by adding virtual visits and rewards to newly created nodes. The heuristic evaluation provides a prior that guides UCB1 selection early in the search. As real visit counts grow, the virtual visits become statistically insignificant and the MCTS estimates dominate.

### Heuristic-Guided Rollouts

Instead of purely random rollouts, an epsilon-greedy policy uses game-specific heuristics to select moves during simulation. With probability `epsilon`, a random move is chosen; otherwise, the move with the best heuristic value is selected. This produces more realistic playouts and improves search quality.

### Tree Reuse

Between moves in a game, the subtree rooted at the previously chosen move can be reused for the next search. This preserves accumulated search statistics, effectively giving the engine a "head start" on subsequent moves. The engine performs a BFS over the previous tree to find the node matching the current state.

### Parallel Search

Root parallelization runs independent MCTS searches in separate threads, each with its own RNG seed, then merges the resulting trees by summing visit counts and rewards. This provides near-linear speedup with thread count.

## Games

| Game | Board | Win Condition | Heuristic |
|------|-------|---------------|-----------|
| Tic-Tac-Toe | 3×3 | 3 in a row | Threat counting + center bonus |
| Connect Four | 6×7 | 4 in a row (gravity) | Window analysis + center column |
| Gomoku | 15×15 | 5 in a row | Pattern matching (2/3/4-in-a-row) |
| Reversi/Othello | 8×8 | Most pieces at end | Corners + mobility + piece count |
| Hex | 11×11 | Connect your two sides | Shortest-path (Dijkstra) |

## Project Structure

```
mcts-engine/
├── mcts/
│   ├── __init__.py      # Package exports
│   ├── __main__.py      # CLI entry point
│   ├── core.py          # GameState, MCTSNode, MCTSResult
│   ├── engine.py        # MCTSEngine, TranspositionTable, SearchStats
│   ├── games.py         # 5 game implementations
│   ├── uct.py           # UCTPolicy, RAVEPolicy, SelectionPolicy
│   ├── rave.py          # RAVE re-export
│   ├── heuristics.py    # 5 game heuristics + rollout policy factory
│   ├── record.py        # GameRecord, play_recorded_game
│   └── cli.py           # Command-line interface (7 subcommands)
├── README.md
└── pyproject.toml
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `play` | Play a game (human vs AI) |
| `selfplay` | Engine plays both sides |
| `benchmark` | Compare MCTS configurations |
| `analyze` | Analyze a position with detailed move evaluation |
| `replay` | Replay a saved game from JSON |
| `list` | List available games |
| `version` | Show version info |

## Known Issues (Resolved)

### Bug 1: Gomoku `_win_length` not copied in `apply()` (fixed)
**Symptom**: `AttributeError: 'Gomoku' object has no attribute '_win_length'` when calling `apply()` on a Gomoku state.  
**Root cause**: `GridGame.apply()` uses `__class__.__new__()` to create the new state, bypassing `__init__()`. Subclass-specific attributes like `Gomoku._win_length` were never set on the copied state.  
**Fix**: Added `_copy_extra_attrs()` hook to `GridGame` that subclasses can override. `Gomoku` overrides it to copy `_win_length`. Called during `apply()` after `__new__`.

### Bug 2: `ucb_value()` crashes on `parent_visits=0` (fixed)
**Symptom**: `ValueError: math domain error` when calling `ucb_value()` or `rave_value()` with `parent_visits=0`.  
**Root cause**: `math.log(0)` raises a `ValueError` in Python. This can happen for children of the root node when the root has 0 visits (before the first backpropagation completes).  
**Fix**: Added a guard: if `parent_visits <= 0`, return just the exploitation term (average reward) without the exploration bonus.

### Bug 3: Reversi `legal_moves()` returns empty list when player must pass (fixed)
**Symptom**: When the current player in Reversi/Othello has no legal moves but the opponent does, `legal_moves()` returned `[]`, causing the MCTS engine to treat the position as a draw instead of a pass.  
**Root cause**: The pass logic (switching to the opponent when the current player can't move) was only in `_apply_move()`, not in `legal_moves()`. The engine checks `legal_moves()` first and never reaches `_apply_move()` if the list is empty.  
**Fix**: `legal_moves()` now checks if the current player has no moves. If so, it returns the opponent's legal moves (the pass case). Additionally, `_apply_move()` now handles the pass case by switching to the opponent before applying the move if the current player truly has no legal moves.

### Bug 4: Connect4 diagonal test was incorrectly constructed (test fix)
**Symptom**: `test_win_diagonal` failed with `ValueError: Illegal move at (2,2)`.  
**Root cause**: The test tried to place a piece at (2,2) without first filling the cells below it (violating Connect4's gravity rule). This was a test bug, not a code bug.  
**Fix**: Rewrote the test to directly construct a board with a diagonal and test `_check_winner()` directly, which correctly detects diagonal wins.

## License

MIT