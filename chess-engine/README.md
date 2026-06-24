# chess-engine

A from-scratch chess engine in pure Python with full legal move generation, alpha-beta search with quiescence and transposition table, opening book, PGN support, and UCI protocol.

## Features

### Core Engine
- **Full legal move generation** — all chess rules: castling (kingside/queenside, with check-path validation), en passant, pawn promotion (Q/R/B/N), pins, check evasion
- **64-square board representation** with make/unmake move (push/pop) for efficient search
- **FEN support** — parse and generate Forsyth-Edwards Notation strings
- **Standard Algebraic Notation (SAN)** — convert moves to/from SAN with disambiguation, castling, promotion, check/mate suffixes
- **Game state detection** — checkmate, stalemate, insufficient material, fifty-move rule, threefold repetition

### Search
- **Alpha-beta search** (negamax framework) with:
  - Quiescence search (captures only) to avoid the horizon effect
  - MVV-LVA move ordering for captures
  - Killer move heuristic for quiet moves
  - **Transposition table** with Zobrist hashing (depth-preferred replacement)
  - Iterative deepening
  - Time management
  - Mate score handling (prefers faster mates)
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
- **Opening book** — 15+ common opening lines (Ruy Lopez, Italian, Sicilian, French, Caro-Kann, Queen's Gambit, King's Indian, etc.) with weighted random selection
- **PGN support** — read and write Portable Game Notation files
- **UCI protocol** — use the engine with GUI tools (Arena, Cute Chess, etc.)
- **CLI tool** with subcommands: display, move, bestmove, analyze, fen, perft, play, moves, pgn, uci

## Installation

```bash
pip install -e .
```

Or run directly with `PYTHONPATH=. python3 -m chess_engine.cli`.

## Usage

### Display the board
```bash
python -m chess_engine.cli display
```
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
```

### Analyze a position
```bash
python -m chess_engine.cli --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" analyze --depth 4
```

### Perft (move generation verification)
```bash
python -m chess_engine.cli perft 4
# Perft(4) = 197281
```

### Engine vs engine self-play
```bash
python -m chess_engine.cli play --depth 3 --max-moves 50
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

## Python API

```python
from chess_engine import Board, Move, Search, Evaluator
from chess_engine.notation import to_algebraic
from chess_engine.opening_book import create_default_book
from chess_engine.pgn import PGNGame

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

# Search for best move
search = Search()
best_move, score = search.search(board, depth=4)
print(f"Best: {best_move.uci()}, score: {score}")

# Check game state
print(board.is_checkmate())
print(board.is_stalemate())
print(board.is_threefold_repetition())
print(board.result())

# PGN
game = PGNGame()
game.add_header("White", "Engine A")
game.add_header("Black", "Engine B")
game.add_move("e4")
game.add_move("e5")
print(game.to_string())
```

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
- **Quiescence search**: at leaf nodes, continue searching only captures to avoid blundering due to the horizon effect
- **MVV-LVA ordering**: try capturing the most valuable piece with the least valuable attacker first
- **Killer moves**: remember non-capture moves that caused beta cutoffs at each depth
- **Iterative deepening**: search at increasing depths, using results to inform the next iteration

### Evaluation
Material values plus piece-square tables that encode positional bonuses. The evaluation also includes:
- **Pawn structure**: detects doubled, isolated, passed, and backward pawns
- **Mobility**: counts available moves per piece type
- **King safety**: checks pawn shield in front of the king (midgame only)

### Zobrist Hashing
Each (piece, square) combination, castling right, en passant file, and side-to-move has a precomputed random 64-bit number. A position's hash is the XOR of all active numbers. This enables efficient transposition table lookups.

### Opening Book
The book stores position hashes mapped to candidate moves with weights. When the current position is in the book, a weighted random move is returned. The default book includes 15+ common openings.

## Testing

```bash
python -m pytest tests/ -v
```

Tests include perft verification (the gold standard for move generation correctness — verified to 8902 nodes at depth 3), castling, en passant, checkmate detection, search, notation conversion, transposition table, Zobrist hashing, opening book, PGN, threefold repetition, and pawn structure evaluation. 41 tests total.