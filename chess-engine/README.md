# chess-engine

A from-scratch chess engine in pure Python with full legal move generation, alpha-beta search with quiescence, and a CLI.

## Features

- **Full legal move generation** — all chess rules: castling (kingside/queenside, with check-path validation), en passant, pawn promotion (Q/R/B/N), pins, check evasion
- **64-square board representation** with make/unmake move (push/pop) for efficient search
- **FEN support** — parse and generate Forsyth-Edwards Notation strings
- **Standard Algebraic Notation (SAN)** — convert moves to/from SAN with disambiguation, castling, promotion, check/mate suffixes
- **Position evaluation** — material + piece-square tables (PST) with midgame/endgame phase detection
- **Alpha-beta search** with:
  - Negamax framework
  - Quiescence search (captures only) to avoid the horizon effect
  - MVV-LVA move ordering for captures
  - Killer move heuristic for quiet moves
  - Iterative deepening
  - Time management
  - Mate score handling (prefers faster mates)
- **Game state detection** — checkmate, stalemate, insufficient material, fifty-move rule
- **CLI tool** with subcommands: display, move, bestmove, analyze, fen, perft, play (engine vs engine), moves

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
# Best move: Nc3 (b1c3)  score: 40
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

## Python API

```python
from chess_engine import Board, Move, Search, Evaluator
from chess_engine.notation import to_algebraic

board = Board()
print(board)

# Generate legal moves
moves = board.legal_moves()
print(f"{len(moves)} legal moves")

# Make a move
board.push(Move(12, 28))  # e2-e4
print(to_algebraic(Move(12, 28), board))  # "e4" (before push)

# Search for best move
search = Search()
best_move, score = search.search(board, depth=4)
print(f"Best: {best_move.uci()}, score: {score}")

# Check game state
print(board.is_checkmate())
print(board.is_stalemate())
print(board.result())
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
- **Quiescence search**: at leaf nodes, continue searching only captures to avoid blundering due to the horizon effect
- **MVV-LVA ordering**: try capturing the most valuable piece with the least valuable attacker first
- **Killer moves**: remember non-capture moves that caused beta cutoffs at each depth
- **Iterative deepening**: search at increasing depths, using results to inform the next iteration

### Evaluation
Material values (pawn=100, knight=320, bishop=330, rook=500, queen=900) plus piece-square tables that encode positional bonuses (e.g., knights are better in the center, pawns advance better). King evaluation switches between midgame (castle safety) and endgame (centralization) tables based on remaining material.

## Testing

```bash
python -m pytest tests/ -v
```

Tests include perft verification (the gold standard for move generation correctness), castling, en passant, checkmate detection, search, and notation conversion.