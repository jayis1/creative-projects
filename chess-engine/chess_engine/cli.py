"""Command-line interface for the chess engine.

Usage:
    python -m chess_engine.cli move e2e4      # make a move (UCI format)
    python -m chess_engine.cli bestmove        # get engine's best move
    python -m chess_engine.cli display         # show the board
    python -m chess_engine.cli fen             # output FEN string
    python -m chess_engine.cli perft 3         # count move tree nodes (depth 3)
    python -m chess_engine.cli play            # engine vs engine game
    python -m chess_engine.cli analyze --depth 4   # analyze position
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from .board import Board, Move, Color, Piece
from .search import Search
from .evaluate import Evaluator
from .notation import to_algebraic, parse_algebraic, square_name, parse_square


def _parse_uci_move(uci: str, board: Board) -> Move:
    """Parse a UCI move string like 'e2e4' or 'e7e8q' into a Move."""
    uci = uci.strip().lower()
    if len(uci) < 4 or len(uci) > 5:
        raise ValueError(f"Invalid UCI move: {uci!r}")

    from_sq = parse_square(uci[:2])
    to_sq = parse_square(uci[2:4])

    promotion = None
    if len(uci) == 5:
        promo_map = {
            "q": Piece.QUEEN, "r": Piece.ROOK,
            "b": Piece.BISHOP, "n": Piece.KNIGHT,
        }
        ptype = promo_map.get(uci[4])
        if ptype is None:
            raise ValueError(f"Invalid promotion: {uci[4]!r}")
        promotion = Piece(ptype, board.turn)

    # Check for castling and en passant by matching legal moves
    for m in board.legal_moves():
        if (m.from_square == from_sq and m.to_square == to_sq
                and (m.promotion == promotion
                     or (m.promotion and promotion
                         and m.promotion.piece_type == promotion.piece_type))):
            return m

    # If no exact match, return a plain move (will be rejected if illegal)
    return Move(from_sq, to_sq, promotion=promotion)


def cmd_display(args: argparse.Namespace) -> int:
    board = _load_board(args)
    print(board.to_string(unicode=not args.ascii))
    print(f"\nFEN: {board.fen()}")
    print(f"Turn: {board.turn}")
    legal = board.legal_moves()
    print(f"Legal moves: {len(legal)}")
    if board.is_check():
        print("** CHECK **")
    if board.is_game_over():
        print(f"Game over: {board.result()}")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    board = _load_board(args)
    move = _parse_uci_move(args.mv, board)
    san = to_algebraic(move, board)
    board.push(move)
    _save_board(args, board)
    print(f"Move: {san} ({move.uci()})")
    print(board.to_string(unicode=True))
    print(f"\nFEN: {board.fen()}")
    if board.is_game_over():
        print(f"Game over: {board.result()}")
    return 0


def cmd_bestmove(args: argparse.Namespace) -> int:
    board = _load_board(args)
    search = Search()
    move, score = search.search(board, depth=args.depth, time_limit=args.time)
    if move:
        san = to_algebraic(move, board)
        print(f"Best move: {san} ({move.uci()})  score: {score}")
    else:
        print("No legal moves (game over)")
    info = search.get_info()
    print(f"Nodes: {info['nodes']}  Time: {info['time']:.2f}s  "
          f"NPS: {info['nps']}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    board = _load_board(args)
    evaluator = Evaluator()
    score = evaluator.evaluate(board)
    print(f"Static evaluation: {score} (from {board.turn}'s perspective)")
    search = Search()
    move, sc = search.search(board, depth=args.depth, time_limit=args.time)
    if move:
        san = to_algebraic(move, board)
        print(f"Best move: {san} ({move.uci()})  score: {sc}")
    info = search.get_info()
    print(f"Nodes: {info['nodes']}  Time: {info['time']:.2f}s  "
          f"NPS: {info['nps']}")
    return 0


def cmd_fen(args: argparse.Namespace) -> int:
    board = _load_board(args)
    print(board.fen())
    return 0


def _perft(board: Board, depth: int) -> int:
    """Count the number of leaf nodes at the given depth."""
    if depth == 0:
        return 1
    if depth == 1:
        return len(board.legal_moves())
    count = 0
    for move in board.legal_moves():
        board.push(move)
        count += _perft(board, depth - 1)
        board.pop()
    return count


def cmd_perft(args: argparse.Namespace) -> int:
    board = _load_board(args)
    total = _perft(board, args.depth)
    print(f"Perft({args.depth}) = {total}")
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    """Engine vs engine self-play."""
    board = _load_board(args)
    search = Search()
    moves_list = []
    max_moves = args.max_moves

    while not board.is_game_over() and len(moves_list) < max_moves:
        move, score = search.search(board, depth=args.depth,
                                    time_limit=args.time)
        if move is None:
            break
        san = to_algebraic(move, board)
        moves_list.append(san)
        print(f"{len(moves_list):3d}. {board.turn.symbol()} {san:8s} "
              f"score={score:7d}  fen={board.fen()}")
        board.push(move)

    print(f"\nGame over: {board.result()}")
    print(f"Moves: {' '.join(moves_list)}")
    _save_board(args, board)
    return 0


def cmd_moves(args: argparse.Namespace) -> int:
    """List all legal moves."""
    board = _load_board(args)
    moves = board.legal_moves()
    print(f"Legal moves ({len(moves)}):")
    for m in moves:
        san = to_algebraic(m, board)
        print(f"  {san:8s}  {m.uci()}")
    return 0


def _load_board(args: argparse.Namespace) -> Board:
    """Load board from FEN argument or file, else starting position."""
    if hasattr(args, "fen") and args.fen:
        return Board.from_fen(args.fen)
    if hasattr(args, "file") and args.file:
        with open(args.file) as f:
            fen = f.read().strip()
        return Board.from_fen(fen)
    return Board()


def _save_board(args: argparse.Namespace, board: Board) -> None:
    """Save board FEN to file if --save is specified."""
    if hasattr(args, "save") and args.save:
        with open(args.save, "w") as f:
            f.write(board.fen())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-engine",
        description="A chess engine in pure Python",
    )
    parser.add_argument("--fen", default=None, help="FEN string for position")
    parser.add_argument("--file", default=None, help="Load FEN from file")
    parser.add_argument("--save", default=None, help="Save resulting FEN to file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    sub_display = subparsers.add_parser("display", help="Show the board")
    sub_display.add_argument("--ascii", action="store_true",
                             help="Use ASCII instead of unicode")
    sub_display.set_defaults(func=cmd_display)

    sub_move = subparsers.add_parser("move", help="Make a move (UCI format)")
    sub_move.add_argument("mv", help="Move in UCI format (e.g. 'e2e4')")
    sub_move.set_defaults(func=cmd_move)

    sub_best = subparsers.add_parser("bestmove", help="Get engine's best move")
    sub_best.add_argument("--depth", type=int, default=4,
                          help="Search depth (default: 4)")
    sub_best.add_argument("--time", type=float, default=None,
                          help="Time limit in seconds")
    sub_best.set_defaults(func=cmd_bestmove)

    sub_analyze = subparsers.add_parser("analyze", help="Analyze position")
    sub_analyze.add_argument("--depth", type=int, default=4,
                             help="Search depth (default: 4)")
    sub_analyze.add_argument("--time", type=float, default=None,
                             help="Time limit in seconds")
    sub_analyze.set_defaults(func=cmd_analyze)

    sub_fen = subparsers.add_parser("fen", help="Output FEN string")
    sub_fen.set_defaults(func=cmd_fen)

    sub_perft = subparsers.add_parser("perft", help="Count move tree nodes")
    sub_perft.add_argument("depth", type=int, help="Perft depth")
    sub_perft.set_defaults(func=cmd_perft)

    sub_play = subparsers.add_parser("play", help="Engine vs engine self-play")
    sub_play.add_argument("--depth", type=int, default=3,
                          help="Search depth per move (default: 3)")
    sub_play.add_argument("--time", type=float, default=None,
                          help="Time limit per move in seconds")
    sub_play.add_argument("--max-moves", type=int, default=100,
                          help="Maximum moves in game (default: 100)")
    sub_play.set_defaults(func=cmd_play)

    sub_moves = subparsers.add_parser("moves", help="List all legal moves")
    sub_moves.set_defaults(func=cmd_moves)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())