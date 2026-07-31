# MCTS Engine — Monte Carlo Tree Search for Game AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 137](https://img.shields.io/badge/tests-137%20passing-brightgreen.svg)](#testing)
[![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-orange.svg)](#changelog)

> A from-scratch implementation of Monte Carlo Tree Search (MCTS) supporting
> multiple games with UCT, RAVE/AMAF, minimax with alpha-beta pruning,
> transposition tables, progressive bias, heuristic-guided rollouts, tree
> reuse, parallel search, opening books, tournament mode, and configuration
> file support.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Play Against the AI](#play-against-the-ai)
  - [Self-Play](#self-play)
  - [Benchmark](#benchmark)
  - [Analyze a Position](#analyze-a-position)
  - [Replay a Saved Game](#replay-a-saved-game)
  - [Tournament Mode](#tournament-mode)
  - [Minimax Analysis](#minimax-analysis)
  - [Configuration Files](#configuration-files)
  - [List Available Games](#list-available-games)
- [Python API](#python-api)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Games](#games)
- [Project Structure](#project-structure)
- [CLI Commands](#cli-commands)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

MCTS is a heuristic search algorithm for decision processes, most notably
used in game AI (e.g., AlphaGo). It builds a partial game tree through four
phases:

1. **Selection** — Traverse the tree from root to leaf using a selection
   policy (UCT or RAVE)
2. **Expansion** — Add a new child node for an untried move
3. **Simulation** — Roll out a playout to a terminal state (random or
   heuristic-guided)
4. **Backpropagation** — Update visit counts and rewards up the path to
   the root

This engine also includes a **minimax with alpha-beta pruning** engine for
exact search on small games, **opening books** for instant opening moves,
and a **tournament mode** for comparing engine configurations with Elo
ratings.

## Features

### MCTS Engine
- **5 games**: Tic-Tac-Toe, Connect Four, Gomoku (Five-in-a-Row),
  Reversi/Othello, Hex
- **2 MCTS selection policies**:
  - **UCT** (Upper Confidence bounds applied to Trees) — classic UCB1 formula
  - **RAVE** (Rapid Action Value Estimation) — blends MCTS values with AMAF
    estimates for faster convergence
- **5 game-specific heuristics**: threat counting (TicTacToe), window
  analysis (Connect4), corner/mobility (Reversi), shortest-path (Hex),
  pattern matching (Gomoku)
- **Progressive bias**: Inject heuristic priors into newly expanded nodes
- **Heuristic-guided rollouts**: Epsilon-greedy rollout policy
- **Tree reuse**: Reuse subtrees from previous searches between moves
- **Parallel search**: Root parallelization with tree merging across threads
- **Transposition tables**: Share statistics across identical states
- **Game records**: Full move history with search statistics, JSON
  serialization, text export
- **Search statistics**: Per-search and cumulative stats

### Minimax Engine
- **Alpha-beta pruning** with move ordering for efficient search
- **Transposition tables** to avoid redundant computation
- **Exact play** on small games (never loses at Tic-Tac-Toe)

### Tournament Mode
- **Round-robin** tournaments between engine configurations
- **Elo rating** computation
- **Standings table** with wins, losses, draws

### Opening Books
- **Build from self-play**: Automatically generate opening books
- **Weighted move selection**: Probabilistic openings from game outcomes
- **Save/load** as JSON

### Configuration & Tooling
- **YAML/JSON config files**: Full engine configuration from file
- **Logging**: Configurable logging with file output
- **CLI**: 10 subcommands including tournament, minimax, and config
- **Pure Python**: No external dependencies (PyYAML optional for YAML config)

## Installation

```bash
cd mcts-engine
pip install -e .
```

With development dependencies (pytest, coverage):

```bash
pip install -e ".[dev]"
```

With YAML configuration support:

```bash
pip install -e ".[yaml]"
```

Or simply run from the directory (Python 3.10+).

## Quick Start

```bash
# Play against the AI
python -m mcts play --game tictactoe --sims 5000

# Watch a self-play game
python -m mcts selfplay --game connect4 --sims 5000

# Run a tournament
python -m mcts tournament --game tictactoe --sims 1000 --rounds 2

# Exact analysis with minimax
python -m mcts minimax --game tictactoe
```

## Usage

### Play Against the AI

```bash
python -m mcts play --game tictactoe --sims 5000
python -m mcts play --game connect4 --sims 10000 --rave
python -m mcts play --game hex --size 7 --sims 20000 --time-limit 5
python -m mcts play --game tictactoe --heuristic --sims 5000
python -m mcts play --game connect4 --sims 20000 --parallel 4 --tree-reuse
python -m mcts play --game gomoku --size 9 --sims 10000
```

Use `--config config.yaml` to load all settings from a file:

```bash
python -m mcts play --config my_config.yaml
```

### Self-Play (engine vs. engine)

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

### Tournament Mode

Run a round-robin tournament between UCT, RAVE, and heuristic-guided
engines with Elo rating computation:

```bash
python -m mcts tournament --game tictactoe --sims 2000 --rounds 4
python -m mcts tournament --game connect4 --sims 3000 --rounds 2
```

Example output:

```
Tournament: tictactoe (4 rounds, 2000 sims/move)
==================================================
  UCT-c1.41 vs UCT-c0.5: UCT-c1.41 (5 moves, 0.1s)
  UCT-c0.5 vs UCT-c1.41: UCT-c1.41 (6 moves, 0.1s)
  ...

Tournament Results
========================================

Player                  W    L    D    Elo
----------------------------------------
UCT-c1.41              15    9    0   1057
RAVE                   13   11    0   1017
UCT-c0.5               12   12    0   1000
UCT+Heur                6   18    0    883

Total games: 48
```

### Minimax Analysis

Run exact minimax search with alpha-beta pruning on small games:

```bash
python -m mcts minimax --game tictactoe
python -m mcts minimax --game tictactoe --depth 5
python -m mcts minimax --game connect4 --size 4 --depth 4
```

Minimax plays perfectly on Tic-Tac-Toe (always draws or wins):

```
Minimax: score=+0.0, nodes=2626, time=0.018s

Result:
  Best move: Move(1,1)
  Score: +0.0
  Nodes searched: 2626
  Time: 0.0181s
  Principal variation: [Move(1,1), Move(2,2), Move(1,2), ...]

Perfect play: Draw (as expected for Tic-Tac-Toe)
```

### Configuration Files

Generate a default config:

```bash
python -m mcts config --save config.json
```

Load and display a config:

```bash
python -m mcts config config.json
python -m mcts config config.yaml
```

Example YAML configuration:

```yaml
# mcts-config.yaml
game:
  name: connect4
  size: 0            # 0 = default

engine:
  policy: rave       # uct | rave
  exploration: 1.4142
  rave_k: 300
  simulation_limit: 10000
  time_limit: 0.0
  max_depth: 0
  rollout_limit: 200
  seed: 42
  verbose: false
  tree_reuse: false
  use_transposition: false
  progressive_bias: 0.0
  heuristic: false
  epsilon_rollout: 0.0
  parallel: 0       # 0 = single-threaded
```

### List available games

```bash
python -m mcts list
```

## Python API

```python
from mcts import MCTSEngine, TicTacToe, UCTPolicy, RAVEPolicy
from mcts import get_heuristic, make_rollout_policy, GameRecord, play_recorded_game
from mcts import MinimaxEngine, OpeningBook, Tournament, PlayerSpec
from mcts import MCTSConfig

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

# Minimax exact search
minimax = MinimaxEngine(max_depth=9)
mm_result = minimax.search(game)
print(f"Minimax score: {mm_result.score}")  # 0.0 = draw with perfect play

# Opening book
book = OpeningBook.build_from_selfplay(game, engine, num_games=100, max_depth=4)
move = book.lookup(game)  # instant opening move

# Tournament
players = [
    PlayerSpec("UCT", MCTSEngine(UCTPolicy(1.4142), simulation_limit=2000, seed=42)),
    PlayerSpec("RAVE", MCTSEngine(RAVEPolicy(1.4142, 300), simulation_limit=2000, rave=True, seed=99)),
]
tourney = Tournament(players, game_factory=lambda: TicTacToe(), rounds=4)
result = tourney.run()
print(result.summary())

# Configuration from file
config = MCTSConfig.from_file("config.yaml")
game = config.game.create()
engine = config.engine.create(config.game.name)

# Play and record a full game
final_state, record = play_recorded_game(game, engine, game_type="tictactoe")
print(record.to_text())
record.save("my_game.json")
loaded = GameRecord.load("my_game.json")

# Search statistics
print(engine.stats.summary())
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                       │
│  play | selfplay | benchmark | analyze | replay |         │
│  tournament | minimax | config | list | version          │
├──────────────────────────────────────────────────────────┤
│                    Config (config.py)                     │
│            YAML/JSON → GameConfig + EngineConfig          │
├─────────────────────┬────────────────────────────────────┤
│   MCTS Engine        │   Minimax Engine (minimax.py)      │
│   (engine.py)        │   Alpha-beta + transposition       │
│   - UCT/RAVE select  │   - Exact search                   │
│   - Rollout policies │   - Move ordering                  │
│   - Tree reuse       │                                    │
│   - Parallel search  │                                    │
│   - Progressive bias │                                    │
├─────────────────────┴────────────────────────────────────┤
│              Selection Policies (uct.py)                  │
│         UCTPolicy  │  RAVEPolicy  │  SelectionPolicy       │
├──────────────────────────────────────────────────────────┤
│                   Games (games.py)                        │
│  TicTacToe │ Connect4 │ Gomoku │ Reversi │ Hex            │
│  All implement GameState (core.py)                       │
├──────────────────────────────────────────────────────────┤
│              Heuristics (heuristics.py)                   │
│  Per-game evaluation functions + rollout policy factory  │
├──────────────────────────────────────────────────────────┤
│          Opening Book (opening_book.py)                   │
│     Build from self-play, save/load, weighted lookup      │
├──────────────────────────────────────────────────────────┤
│           Tournament (tournament.py)                      │
│    Round-robin, Elo ratings, standings, game results      │
├──────────────────────────────────────────────────────────┤
│         Records (record.py) │ Logging (logging_utils.py)  │
│    JSON serialization       │  Configurable logging       │
└──────────────────────────────────────────────────────────┘
```

### Core Abstractions

- **`GameState`** (ABC): The interface all games implement. Defines
  `current_player()`, `legal_moves()`, `apply()`, `winner()`,
  `is_terminal()`, `hash_key()`, `display()`, and `reward()`.
- **`MCTSNode`**: A node in the search tree. Tracks visits, rewards,
  children, untried moves, and AMAF statistics. Provides UCB1 and RAVE
  value computation.
- **`SelectionPolicy`** (ABC): Pluggable child selection. Implementations:
  `UCTPolicy` and `RAVEPolicy`.
- **`MCTSEngine`**: The main search engine. Orchestrates selection,
  expansion, simulation, and backpropagation. Supports all advanced
  features.
- **`MinimaxEngine`**: Alternative exact search engine using minimax
  with alpha-beta pruning.
- **`MCTSConfig`**: Configuration dataclass with YAML/JSON serialization.

## How It Works

### UCT Selection

The UCB1 formula balances exploitation and exploration:

```
UCB1 = (total_reward / visits) + c * sqrt(ln(parent_visits) / visits)
```

- `c` = exploration constant (default √2 ≈ 1.4142)
- Unvisited nodes return +∞, ensuring all children are tried at least once

### RAVE / AMAF

RAVE (Rapid Action Value Estimation) uses the AMAF (All Moves As First)
heuristic: if a move `m` was played during a rollout and led to a win, we
update not just the node for `m` in the tree, but also the AMAF statistics
for any child with move `m` along the backpropagation path. This provides
faster value estimates early in the search when visit counts are low.

The blended value is:

```
β = N_amaf / (N_visits + N_amaf + 4·k·N_visits·N_amaf / (N_visits + N_amaf + 4·k))
value = (1 - β) · MCTS_avg + β · AMAF_avg + exploration
```

### Progressive Bias

Progressive bias injects heuristic knowledge into the tree by adding
virtual visits and rewards to newly created nodes. The heuristic evaluation
provides a prior that guides UCB1 selection early in the search. As real
visit counts grow, the virtual visits become statistically insignificant
and the MCTS estimates dominate.

### Heuristic-Guided Rollouts

Instead of purely random rollouts, an epsilon-greedy policy uses
game-specific heuristics to select moves during simulation. With probability
`epsilon`, a random move is chosen; otherwise, the move with the best
heuristic value is selected. This produces more realistic playouts and
improves search quality.

### Tree Reuse

Between moves in a game, the subtree rooted at the previously chosen move
can be reused for the next search. This preserves accumulated search
statistics, effectively giving the engine a "head start" on subsequent
moves. The engine performs a BFS over the previous tree to find the node
matching the current state.

### Parallel Search

Root parallelization runs independent MCTS searches in separate threads,
each with its own RNG seed, then merges the resulting trees by summing
visit counts and rewards. This provides near-linear speedup with thread
count.

### Minimax with Alpha-Beta

For small games, minimax with alpha-beta pruning provides exact play. The
engine evaluates all possible move sequences to a given depth, pruning
branches that cannot affect the final decision. Move ordering (trying
center moves first) improves pruning efficiency. A transposition table
caches previously evaluated positions.

### Opening Books

Opening books store pre-computed best moves for common opening positions.
They are built by running self-play games and recording the first N moves,
weighted by game outcome. During play, the engine checks the book first
for an instant move, falling back to MCTS search when the position is not
in the book.

### Tournament Mode

The tournament system runs a round-robin between engine configurations.
Each pair of players plays two games per round (swapping sides). Elo
ratings are updated after each game using the standard Elo formula with
a configurable K-factor.

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
│   ├── __init__.py        # Package exports
│   ├── __main__.py        # CLI entry point
│   ├── core.py            # GameState, MCTSNode, MCTSResult
│   ├── engine.py          # MCTSEngine, TranspositionTable, SearchStats
│   ├── games.py           # 5 game implementations
│   ├── uct.py             # UCTPolicy, RAVEPolicy, SelectionPolicy
│   ├── rave.py            # RAVE re-export
│   ├── heuristics.py      # 5 game heuristics + rollout policy factory
│   ├── record.py          # GameRecord, play_recorded_game
│   ├── cli.py             # Command-line interface (10 subcommands)
│   ├── config.py          # YAML/JSON configuration support
│   ├── minimax.py         # Minimax with alpha-beta pruning
│   ├── opening_book.py    # Opening book creation and lookup
│   ├── tournament.py      # Round-robin tournament with Elo ratings
│   └── logging_utils.py   # Configurable logging
├── tests/
│   ├── test_mcts.py       # Core tests (85 tests)
│   ├── test_bugs.py       # Bug regression tests (17 tests)
│   └── test_new_features.py  # New feature tests (52 tests)
├── examples/
│   ├── 01_basic_search.py
│   ├── 02_rave_vs_uct.py
│   ├── 03_heuristic_search.py
│   ├── 04_minimax.py
│   ├── 05_tournament.py
│   ├── 06_config_file.py
│   └── 07_opening_book.py
├── .github/
│   └── workflows/
│       └── mcts-engine.yml  # CI config
├── CONTRIBUTING.md
├── LICENSE
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
| `tournament` | Round-robin tournament between engine configs |
| `minimax` | Minimax analysis (exact search for small games) |
| `config` | Show or generate configuration files |
| `list` | List available games |
| `version` | Show version info |

## Examples

The `examples/` directory contains runnable demo scripts:

```bash
python examples/01_basic_search.py      # Basic MCTS search
python examples/02_rave_vs_uct.py      # RAVE vs UCT comparison
python examples/03_heuristic_search.py # Heuristic-guided search
python examples/04_minimax.py          # Minimax perfect play
python examples/05_tournament.py       # Tournament with Elo ratings
python examples/06_config_file.py      # Configuration file usage
python examples/07_opening_book.py     # Opening book creation
```

## Testing

```bash
# Run all 137 tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=mcts --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_new_features.py -v
```

Test breakdown:
- `test_mcts.py`: 85 tests — core engine, games, heuristics, records
- `test_bugs.py`: 17 tests — bug regression tests
- `test_new_features.py`: 52 tests — config, minimax, opening book, tournament, logging, CLI

## Known Issues (Resolved)

### Bug 1: Gomoku `_win_length` not copied in `apply()` (fixed)
**Symptom**: `AttributeError: 'Gomoku' object has no attribute '_win_length'`
when calling `apply()` on a Gomoku state.
**Root cause**: `GridGame.apply()` uses `__class__.__new__()` to create the
new state, bypassing `__init__()`. Subclass-specific attributes like
`Gomoku._win_length` were never set on the copied state.
**Fix**: Added `_copy_extra_attrs()` hook to `GridGame` that subclasses can
override. `Gomoku` overrides it to copy `_win_length`. Called during
`apply()` after `__new__`.

### Bug 2: `ucb_value()` crashes on `parent_visits=0` (fixed)
**Symptom**: `ValueError: math domain error` when calling `ucb_value()` or
`rave_value()` with `parent_visits=0`.
**Root cause**: `math.log(0)` raises a `ValueError` in Python. This can
happen for children of the root node when the root has 0 visits (before the
first backpropagation completes).
**Fix**: Added a guard: if `parent_visits <= 0`, return just the
exploitation term (average reward) without the exploration bonus.

### Bug 3: Reversi `legal_moves()` returns empty list when player must pass (fixed)
**Symptom**: When the current player in Reversi/Othello has no legal moves
but the opponent does, `legal_moves()` returned `[]`, causing the MCTS
engine to treat the position as a draw instead of a pass.
**Root cause**: The pass logic (switching to the opponent when the current
player can't move) was only in `_apply_move()`, not in `legal_moves()`.
**Fix**: `legal_moves()` now checks if the current player has no moves. If
so, it returns the opponent's legal moves (the pass case). Additionally,
`_apply_move()` handles the pass case by switching to the opponent before
applying the move.

### Bug 4: Connect4 diagonal test was incorrectly constructed (test fix)
**Symptom**: `test_win_diagonal` failed with `ValueError: Illegal move at
(2,2)`.
**Root cause**: The test tried to place a piece at (2,2) without first
filling the cells below it (violating Connect4's gravity rule).
**Fix**: Rewrote the test to directly construct a board with a diagonal and
test `_check_winner()` directly.

## Changelog

### v3.0.0 — Comprehensive Improvement
- **Minimax engine**: Alpha-beta pruning with transposition tables and
  move ordering. Plays perfectly on Tic-Tac-Toe.
- **Tournament mode**: Round-robin between engine configurations with Elo
  ratings and standings table.
- **Opening books**: Build from self-play, save/load as JSON, weighted
  probabilistic move selection.
- **Configuration files**: Full YAML/JSON config support with
  `MCTSConfig`, `GameConfig`, `EngineConfig` dataclasses.
- **Logging**: Configurable logging module with file output.
- **7 example scripts**: Runnable demos for every major feature.
- **GitHub Actions CI**: Automated testing on Python 3.10/3.11/3.12.
- **CONTRIBUTING.md**: Development setup and contribution guidelines.
- **LICENSE**: MIT license file.
- **52 new tests**: Comprehensive coverage of all new features (137 total).
- **CLI enhancements**: 3 new subcommands (`tournament`, `minimax`, `config`),
  `--config` flag, `--seed` flag.
- **Improved pyproject.toml**: Optional dependencies, classifiers, pytest
  config.

### v2.0.0 — Enhanced
- 5 game-specific heuristics
- Progressive bias
- Heuristic-guided rollouts
- Tree reuse
- Game records with JSON serialization
- Search statistics
- Expanded CLI (7 subcommands)

### v1.0.0 — Initial Release
- MCTS engine with UCT and RAVE
- 5 games: TicTacToe, Connect4, Gomoku, Reversi, Hex
- Parallel search
- Transposition tables
- CLI interface

## Roadmap

- **More games**: Chess, Go (small boards), Checkers, Backgammon
- **Neural network evaluation**: Learn value and policy networks
- **Opening theory**: Expand opening books with expert knowledge
- **Time management**: Adaptive time allocation based on game phase
- **Pondering**: Background search during opponent's turn
- **GTP protocol**: Support for Go Text Protocol for integration with
  Go GUIs
- **Web interface**: Browser-based visualization of search tree
- **MPI parallelization**: Distributed search across machines
- **Bitboard optimization**: Faster state representation for Connect4
- **Endgame databases**: Pre-computed perfect play for endgame positions

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style
guidelines, and instructions for adding new games, policies, and features.

## License

MIT — see [LICENSE](LICENSE) for details.