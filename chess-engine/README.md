# ♟️ chess-engine

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 114](https://img.shields.io/badge/tests-114-brightgreen.svg)](tests/)
[![Version: 3.0](https://img.shields.io/badge/version-3.0-orange.svg)](#changelog)

A from-scratch chess engine in pure Python — full legal move generation, alpha-beta search with quiescence, null-move pruning, late move reductions, transposition table, 35+ opening lines, PGN support, UCI protocol, and interactive human-vs-engine play.

```
8 r n b q k b n r
7 p p p p p p p p
6 . . . . . . . .
5 . . . . . . . .
4 . . . . . . . .
3 . . . . . . . .
2 P P P P P P P P
1 R N B Q K B N R
  a b c d e f g h
```

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Python API](#python-api)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Testing](#testing)
- [Examples](#examples)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [License](#license)

---

## Features

### Core Engine
- **Full legal move generation** — all chess rules: castling (kingside/queenside, with check-path validation), en passant, pawn promotion (Q/R/B/N), pins, check evasion
- **64-square board representation** with make/unmake move (push/pop) for efficient search
- **Null move support** — push_null/pop_null for null-move pruning
- **FEN support** — parse and generate Forsyth-Edwards Notation strings
- **Standard Algebraic Notation (SAN)** — convert moves to/from SAN with disambiguation, castling, promotion, check/mate suffixes
- **Game state detection** — checkmate, stalemate, insufficient material, fifty-move rule, threefold repetition

### Search (v3.0 enhancements in bold)
- **Alpha-beta search** (negamax framework) with:
  - Quiescence search (captures only, or all moves when in check) to avoid the horizon effect
  - MVV-LVA move ordering for captures
  - Killer move heuristic for quiet moves
  - **History heuristic** for improved quiet move ordering
  - **Late move reductions (LMR)** for poorly-ordered late moves
  - **Null move pruning (NMP)** to prune branches where the side to move is clearly winning
  - Transposition table with Zobrist hashing (depth-preferred replacement)
  - Iterative deepening
  - **Principal variation (PV) tracking** — the engine reports its expected line of play
  - Time management
  - Mate score handling (prefers faster mates, ply-adjusted for TT)
  - Threefold repetition detection in search

### Evaluation
- **Material values** (pawn=100, knight=320, bishop=330, rook=500, queen=900)
- **Piece-square tables (PST)** for all piece types
- **Midgame/endgame phase detection** with different king tables
- **Pawn structure evaluation**:
  - Doubled pawns (-15 penalty)
  - Isolated pawns (-20 penalty)
  - Passed pawns (+20 bonus, scaling with rank)
  - Backward pawns (-10 penalty)
- **Piece mobility** — bonus per available move by piece type
- **King safety** — pawn shield evaluation (-15 per missing shield square)
- **Tempo bonus** (+10)

### Additional Features
- **Opening book** — 35+ common opening lines (Ruy Lopez, Italian, Sicilian, French, Caro-Kann, Pirc, Queen's Gambit, King's Indian, Nimzo-Indian, Slav, Dutch, English, Réti, London, King's Gambit, etc.) with weighted random selection and JSON import/export
- **PGN support** — read and write Portable Game Notation files with comments, variations, and NAG support
- **UCI protocol** — use the engine with GUI tools (Arena, Cute Chess, etc.) with configurable search options
- **Interactive game manager** — play human vs engine from the CLI or programmatically
- **CLI tool** with 13 subcommands: display, move, bestmove, analyze, eval, fen, perft, perft-suite, play, play-human, moves, pgn, uci
- **Configuration file support** — YAML or JSON config for all search parameters
- **Logging** — configurable via config file

---

## Installation

### From source (recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/chess-engine
pip install -e ".[test]"
```

### Direct usage (no install needed)

```bash
cd creative-projects/chess-engine
PYTHONPATH=. python3 -m chess_engine.cli display
```

### Requirements
- Python 3.9+
- Optional: PyYAML for YAML config files (`pip install pyyaml`)
- Optional: pytest for running tests (`pip install pytest`)

---

## Quick Start

```bash
# Display the board
python -m chess_engine.cli display

# Get the engine's best move
python -m chess_engine.cli bestmove --depth 4

# Play interactively against the engine (you play White)
python -m chess_engine.cli play-human --depth 4 --color white

# Engine vs engine self-play
python -m chess_engine.cli play --depth 3 --max-moves 50 --pgn game.pgn
```

---

## CLI Usage

### Display the board
```bash
python -m chess_engine.cli display
```
```
8 ♜♞♝♛♚♝♞♜
7 ♟♟♟♟♟♟♟♟
6 . . . . . . . .
5 . . . . . . . .
4 . . . . . . . .
3 . . . . . . . .
2 ♙♙♙♙♙♙♙♙
1 ♖♘♗♕♔♗♘♖
  a b c d e f g h

FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
Turn: white
Legal moves: 20
```

### Make a move (UCI format)
```bash
python -m chess_engine.cli move e2e4
```

### Get the engine's best move
```bash
python -m chess_engine.cli bestmove --depth 4
# Best move: d4 (d2d4)  [from book]

python -m chess_engine.cli bestmove --depth 4 --no-book
# Best move: Nc3 (b1c3)  score: 48
# Nodes: 12453  Time: 0.52s  NPS: 23948
# PV: b1c3 g8f6 e2e4
```

### Analyze a position
```bash
python -m chess_engine.cli --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" analyze --depth 4
```

### Static evaluation breakdown
```bash
python -m chess_engine.cli --fen "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3" eval
```

### Perft (move generation verification)
```bash
python -m chess_engine.cli perft 4
# Perft(4) = 197281
# Time: 3.21s  NPS: 61460
```

### Standard perft test suite
```bash
python -m chess_engine.cli perft-suite --depth 3
```
Runs 6 standard perft positions (starting position, Kiwipete, Positions 3–6) and verifies against known node counts.

### Engine vs engine self-play
```bash
python -m chess_engine.cli play --depth 3 --max-moves 50 --pgn game.pgn
```

### Interactive human vs engine
```bash
python -m chess_engine.cli play-human --depth 4 --color white
```
```
┌─────────────────────────────────────────┐
│       chess-engine — Interactive        │
│   Enter moves in SAN (e.g. e4, Nf3)     │
│   or UCI (e.g. e2e4, g1f3).             │
│   Commands: quit, moves, fen             │
└─────────────────────────────────────────┘
8 ♜♞♝♛♚♝♞♜
...
white's turn. Enter move (SAN/UCI): e4
Engine plays: e5 (score: 0)
...
```

### List legal moves
```bash
python -m chess_engine.cli moves
```

### Output game as PGN
```bash
python -m chess_engine.cli pgn
```

### Run as UCI engine (for GUI integration)
```bash
python -m chess_engine.cli uci
```

### Use a configuration file
```bash
python -m chess_engine.cli --config engine.yaml bestmove --depth 6
```

---

## Python API

```python
from chess_engine import Board, Move, Search, Evaluator, Game
from chess_engine.notation import to_algebraic, parse_algebraic
from chess_engine.opening_book import create_default_book
from chess_engine.pgn import PGNGame
from chess_engine.config import load_config, apply_search_config

# Basic board operations
board = Board()
print(board)

# Opening book
book = create_default_book()
book_move = book.probe(board)
if book_move:
    print(f"Book suggests: {book_move.uci()}")

# Generate legal moves
moves = board.legal_moves()
print(f"{len(moves)} legal moves")

# Make a move
board.push(Move(12, 28))  # e2-e4

# Search for best move (with PV tracking)
search = Search()
move, score = search.search(board, depth=4)
print(f"Best: {move.uci()}, score: {score}")
info = search.get_info()
print(f"PV: {' '.join(info['pv'])}")

# Check game state
print(board.is_checkmate())
print(board.is_stalemate())
print(board.is_threefold_repetition())
print(board.result())

# Play a game with the Game manager
game = Game()
game.play_human_move("e4")
game.play_human_move("e5")
game.play_engine_move(depth=4)
print(game.to_pgn())

# Configuration
cfg = load_config("engine.yaml")
search = Search()
apply_search_config(search, cfg)
move, score = search.search(board, depth=6)

# PGN
game = PGNGame()
game.add_header("White", "Engine A")
game.add_header("Black", "Engine B")
game.add_move("e4")
game.add_move("e5")
print(game.to_string())
```

---

## Configuration

The engine supports YAML and JSON configuration files for all search parameters.

Example `engine.yaml`:
```yaml
search:
  max_depth: 6
  time_limit: 5.0
  use_quiescence: true
  use_killers: true
  use_history: true
  use_lmr: true
  use_null_move: true
  use_iterative_deepening: true
  use_tt: true

evaluation:
  tempo_bonus: 10

opening_book:
  enabled: true
  file: null  # null = built-in book

logging:
  level: INFO
  file: null
```

See `engine.yaml.example` for a template.

---

## Architecture

```
chess-engine/
├── chess_engine/
│   ├── __init__.py          # Package exports
│   ├── board.py             # Board representation, move generation, push/pop
│   ├── search.py            # Alpha-beta search with all optimizations
│   ├── evaluate.py          # Position evaluation (material, PST, structure)
│   ├── notation.py          # SAN/FEN notation conversion
│   ├── pgn.py                # PGN read/write
│   ├── uci.py                # UCI protocol handler
│   ├── opening_book.py       # Opening book with 35+ lines
│   ├── zobrist.py            # Zobrist hashing for transposition table
│   ├── transposition.py      # Transposition table
│   ├── game.py               # Game manager (human vs engine)
│   ├── config.py             # Configuration file support
│   └── cli.py                # Command-line interface (13 subcommands)
├── tests/
│   ├── test_engine.py        # Core engine tests (41 tests)
│   ├── test_bug_hunt.py      # Bug hunt verification tests (30 tests)
│   └── test_improvements.py  # New feature tests (43 tests)
├── examples/
│   ├── 01_basic_search.py    # Basic search usage
│   ├── 02_play_game.py       # Game manager usage
│   ├── 03_engine_vs_engine.py
│   ├── 04_analyze_position.py
│   ├── 05_configuration.py
│   └── 06_pgn_and_book.py
├── pyproject.toml            # Installable package configuration
├── engine.yaml.example       # Sample config file
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### Module Overview

| Module | Responsibility |
|--------|---------------|
| `board.py` | 64-square array, move generation (pseudo-legal → legal filtering), push/pop with state undo, null move support, FEN parse/generate, game state queries |
| `search.py` | Negamax alpha-beta search with quiescence, null-move pruning, LMR, killer moves, history heuristic, transposition table, iterative deepening, PV tracking |
| `evaluate.py` | Material + piece-square tables + pawn structure (doubled/isolated/passed/backward) + mobility + king safety + tempo |
| `notation.py` | SAN generation (with disambiguation, check/mate suffixes) and parsing |
| `pgn.py` | PGN game creation, parsing (with comments/variations/NAGs), board-to-PGN conversion |
| `uci.py` | UCI protocol: uci, isready, setoption, ucinewgame, position, go, stop, quit |
| `opening_book.py` | Position-hash-based book with weighted random selection, JSON import/export |
| `game.py` | Game orchestration: human input (SAN/UCI), engine moves, PGN export |
| `config.py` | YAML/JSON config loading with deep merge, search config application, logging setup |
| `cli.py` | 13 subcommands: display, move, bestmove, analyze, eval, fen, perft, perft-suite, play, play-human, moves, pgn, uci |

---

## How It Works

### Board Representation
The board uses a flat 64-element array where index 0 = a1, 7 = h1, 56 = a8, 63 = h8. Pieces are represented as `Piece(type, color)` objects.

### Move Generation
Pseudo-legal moves are generated for each piece type:
- **Pawns**: single/double push, captures, en passant, promotion
- **Knights**: 8 jump offsets
- **Bishops/Rooks/Queens**: sliding ray generation
- **King**: 8 adjacent squares + castling (with attack-square validation)

Legal moves are filtered by making each move and checking if the mover's king is in check.

### Attack Detection
`_is_attacked()` checks if a square is attacked by any enemy piece using reverse pawn/knight/king/slider ray scans. This is used for check detection and castling legality.

### Search
The search uses **negamax with alpha-beta pruning** — the standard framework for zero-sum game search. Key optimizations:
- **Transposition table**: positions are hashed using Zobrist hashing (XOR of random numbers for each piece/square/state) and stored in a table to avoid re-searching
- **Quiescence search**: at leaf nodes, continue searching captures (or all moves when in check) to avoid blundering due to the horizon effect
- **MVV-LVA ordering**: try capturing the most valuable piece with the least valuable attacker first
- **Killer moves**: remember non-capture moves that caused beta cutoffs at each depth
- **History heuristic**: track how often quiet moves caused cutoffs, ordered by depth²
- **Late move reductions**: poorly-ordered moves late in the move list are searched at reduced depth
- **Null move pruning**: if the side to move can "pass" and still be winning, prune the branch
- **Iterative deepening**: search at increasing depths, using results to inform the next iteration

### Evaluation
Material values plus piece-square tables that encode positional bonuses. The evaluation also includes:
- **Pawn structure**: detects doubled, isolated, passed, and backward pawns
- **Mobility**: counts available moves per piece type
- **King safety**: checks pawn shield in front of the king (midgame only)

### Zobrist Hashing
Each (piece, square) combination, castling right, en passant file, and side-to-move has a precomputed random 64-bit number. A position's hash is the XOR of all active numbers. This enables efficient transposition table lookups.

### Opening Book
The book stores position hashes mapped to candidate moves with weights. When the current position is in the book, a weighted random move is returned. The default book includes 35+ named opening lines covering all major chess opening systems.

---

## Testing

```bash
python -m pytest tests/ -v
```

**114 tests total** across three test suites:

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_engine.py` | 41 | Board basics, perft, castling, en passant, checkmate, evaluation, search, notation, TT, Zobrist, opening book, PGN, threefold repetition, pawn structure |
| `test_bug_hunt.py` | 30 | Edge cases: promotion undo, castling rights undo, stalemate, pins, search-in-check, insufficient material, fifty-move rule, SAN disambiguation, board copy, Kiwipete perft, blocked double push, quiescence-in-check, TT mate scores, backward pawn detection |
| `test_improvements.py` | 43 | Null move push/pop, null move pruning, LMR, history heuristic, PV tracking, search config flags, config loading, Game manager, expanded opening book, perft suite (6 positions), CLI parser |

### Perft Verification

Perft (performance test) counts leaf nodes in the move tree — the gold standard for move generation correctness.

```bash
python -m chess_engine.cli perft-suite --depth 3
```

Verified positions:
| Position | Perft(1) | Perft(2) | Perft(3) |
|----------|----------|----------|----------|
| Starting position | 20 | 400 | 8,902 |
| Kiwipete | 48 | 2,039 | 97,862 |
| Position 3 | 14 | 191 | 2,812 |
| Position 4 | 6 | 264 | 9,467 |
| Position 5 | 44 | 1,486 | 62,379 |
| Position 6 | 46 | 2,079 | 89,890 |

---

## Examples

The `examples/` directory contains runnable demos:

```bash
# Basic search
PYTHONPATH=. python3 examples/01_basic_search.py

# Play a game programmatically
PYTHONPATH=. python3 examples/02_play_game.py

# Engine vs engine
PYTHONPATH=. python3 examples/03_engine_vs_engine.py

# Analyze a position
PYTHONPATH=. python3 examples/04_analyze_position.py

# Configuration files
PYTHONPATH=. python3 examples/05_configuration.py

# PGN and opening book
PYTHONPATH=. python3 examples/06_pgn_and_book.py
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to add new features.

---

## Roadmap

- [ ] Bitboard representation for faster move generation
- [ ] Aspiration windows for iterative deepening
- [ ] Check extensions in search
- [ ] Singular extensions
- [ ] Multi-threaded search
- [ ] Endgame tablebase support (Syzygy)
- [ ] Neural network evaluation (NNUE-style)
- [ ] Opening book in binary format for faster loading
- [ ] XBoard/WinBoard protocol support
- [ ] Web-based GUI
- [ ] Chess960 (Fischer Random) support

---

## Changelog

### v3.0 — Comprehensive Improvement
- **Null move pruning (NMP)** — prune branches where the side to move is clearly winning by passing the move
- **Late move reductions (LMR)** — poorly-ordered late moves are searched at reduced depth, with re-search if they improve alpha
- **History heuristic** — quiet moves that cause cutoffs are ordered by depth², improving move ordering over time
- **Principal variation (PV) tracking** — the engine now reports its expected line of play
- **Board.push_null() / pop_null()** — null move support on the Board class for search
- **Interactive game manager** (`game.py`) — human vs engine play with SAN/UCI input, engine vs engine, PGN export
- **`play-human` CLI command** — interactive human vs engine game from the command line
- **`eval` CLI command** — static evaluation breakdown
- **`perft-suite` CLI command** — run 6 standard perft test positions with verification
- **Configuration file support** (`config.py`) — YAML/JSON config for all search parameters with deep merge
- **Logging** — configurable via config file
- **Expanded opening book** — from 15 to 35+ named opening lines
- **Enhanced pyproject.toml** — proper classifiers, optional dependencies, pytest config
- **6 example scripts** — `examples/` directory with runnable demos
- **CONTRIBUTING.md and LICENSE** — proper project documentation
- **GitHub Actions CI** — automated testing across Python 3.9–3.12
- **43 new tests** (114 total) — covering all new features
- **`--config` CLI flag** — load search settings from a file

### v2.0 — Enhancement & Bug Hunt
- Transposition table with Zobrist hashing
- Opening book with 15+ common openings
- PGN read/write support
- UCI protocol for GUI integration
- Enhanced evaluation: pawn structure, mobility, king safety
- Threefold repetition detection
- Fixed 5 bugs (quiescence-in-check, TT mate scores, backward pawn, board copy, UCI position)

### v1.0 — Initial Release
- Full legal move generation (castling, en passant, promotion, pins)
- Alpha-beta search with quiescence, MVV-LVA, killer moves, iterative deepening
- Material + PST evaluation with midgame/endgame detection
- FEN parse/generate, SAN notation with disambiguation
- CLI with 8 subcommands
- 29 tests, perft verified to 8902@depth3

---

## Known Issues (Resolved)

### Bug 1: Quiescence search missed check evasions (Fixed in v2.0)
**Problem**: The quiescence search only considered capture moves, even when the side to move was in check. This meant it could miss checkmates and fail to find check evasions at the search horizon, leading to incorrect evaluations.

**Fix**: When the side to move is in check, the quiescence search now considers ALL legal moves (not just captures), ensuring check evasions are always found. The stand-pat evaluation is also skipped when in check (since the player cannot "pass").

### Bug 2: Transposition table mate scores not adjusted for ply (Fixed in v2.0)
**Problem**: Mate scores stored in the transposition table were relative to the ply at which they were found. When the same position was probed at a different ply (common with iterative deepening), the mate score would be incorrect.

**Fix**: Mate scores are now adjusted when storing (subtracting the current ply) and when probing (adding the current ply), ensuring correct mate distance reporting regardless of when the position was evaluated.

### Bug 3: Backward pawn detection wrong for black pawns (Fixed in v2.0)
**Problem**: The backward pawn detection searched "behind" the pawn using `range(behind_rank, -1, -1)`, which always searched downward (toward rank 1). For black pawns, "behind" means toward rank 8 (higher ranks), so the search direction was reversed.

**Fix**: The search direction is now color-dependent: `range(behind_rank, -1, -1)` for white pawns (toward rank 1) and `range(behind_rank, 8)` for black pawns (toward rank 8).

### Bug 4: Board.copy() didn't copy position history (Fixed in v2.0)
**Problem**: `Board.copy()` created a new board from FEN and copied `history` but forgot to copy `_position_history` (the repetition detection dictionary). This meant threefold repetition detection would not work correctly on copied boards.

**Fix**: `_position_history` is now explicitly copied in `Board.copy()`.

### Bug 5: UCI position command set non-existent attribute (Fixed in v2.0)
**Problem**: The UCI `_cmd_position` handler set `self._position_history = {}` on the `UCIEngine` object, which was a no-op (the Board manages its own position history internally via push/pop).

**Fix**: Removed the unnecessary attribute assignment.

---

## License

[MIT License](LICENSE) — Copyright (c) 2024-2026 creative-projects