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

Tests include perft verification (the gold standard for move generation correctness — verified to 8902 nodes at depth 3, Kiwipete position verified to 97862 at depth 3), castling, en passant, checkmate detection, search, notation conversion, transposition table, Zobrist hashing, opening book, PGN, threefold repetition, pawn structure evaluation, quiescence-in-check, TT mate score adjustment, backward pawn for black, and copy semantics. 71 tests total.

## Known Issues (Resolved)

### Bug 1: Quiescence search missed check evasions (Fixed)
**Problem**: The quiescence search only considered capture moves, even when the side to move was in check. This meant it could miss checkmates and fail to find check evasions at the search horizon, leading to incorrect evaluations.

**Fix**: When the side to move is in check, the quiescence search now considers ALL legal moves (not just captures), ensuring check evasions are always found. The stand-pat evaluation is also skipped when in check (since the player cannot "pass").

### Bug 2: Transposition table mate scores not adjusted for ply (Fixed)
**Problem**: Mate scores stored in the transposition table were relative to the ply at which they were found. When the same position was probed at a different ply (common with iterative deepening), the mate score would be incorrect — e.g., a mate-in-2 found at ply 4 would be reported as mate-in-2 when probed at ply 2, making it seem closer than it actually is.

**Fix**: Mate scores are now adjusted when storing (subtracting the current ply) and when probing (adding the current ply), ensuring correct mate distance reporting regardless of when the position was evaluated.

### Bug 3: Backward pawn detection wrong for black pawns (Fixed)
**Problem**: The backward pawn detection searched "behind" the pawn using `range(behind_rank, -1, -1)`, which always searched downward (toward rank 1). For black pawns, "behind" means toward rank 8 (higher ranks), so the search direction was reversed.

**Fix**: The search direction is now color-dependent: `range(behind_rank, -1, -1)` for white pawns (toward rank 1) and `range(behind_rank, 8)` for black pawns (toward rank 8).

### Bug 4: Board.copy() didn't copy position history (Fixed)
**Problem**: `Board.copy()` created a new board from FEN and copied `history` but forgot to copy `_position_history` (the repetition detection dictionary). This meant threefold repetition detection would not work correctly on copied boards.

**Fix**: `_position_history` is now explicitly copied in `Board.copy()`.

### Bug 5: UCI position command set non-existent attribute (Fixed)
**Problem**: The UCI `_cmd_position` handler set `self._position_history = {}` on the `UCIEngine` object, which was a no-op (the Board manages its own position history internally via push/pop). This was harmless but indicated a misunderstanding of the architecture.

**Fix**: Removed the unnecessary attribute assignment.