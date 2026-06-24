"""Command-line interface for the chess engine.

Usage:
    python -m chess_engine.cli move e2e4            # make a move (UCI format)
    python -m chess_engine.cli bestmove              # get engine's best move
    python -m chess_engine.cli display               # show the board
    python -m chess_engine.cli fen                    # output FEN string
    python -m chess_engine.cli perft 3               # count move tree nodes
    python -m chess_engine.cli play --depth 3        # engine vs engine
    python -m chess_engine.cli play-human --depth 4  # human vs engine
    python -m chess_engine.cli analyze --depth 4     # analyze position
    python -m chess_engine.cli eval                   # static evaluation
    python -m chess_engine.cli moves                  # list legal moves
    python -m chess_engine.cli pgn                    # output PGN
    python -m chess_engine.cli uci                    # run UCI protocol
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from .board import Board, Move, Color, Piece
from .search import Search
from .evaluate import Evaluator
from .notation import to_algebraic, parse_algebraic, square_name, parse_square

logger = logging.getLogger(__name__)


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


def _make_search(args: argparse.Namespace) -> Search:
    """Create a Search instance, optionally applying config file settings."""
    search = Search()
    if hasattr(args, "config") and args.config:
        from .config import load_config, apply_search_config, setup_logging
        cfg = load_config(args.config)
        apply_search_config(search, cfg)
        setup_logging(cfg)
    return search


# ── Subcommands ──────────────────────────────────────────────────

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
    # Check opening book first
    if not args.no_book:
        from .opening_book import create_default_book
        book = create_default_book()
        book_move = book.probe(board)
        if book_move is not None:
            san = to_algebraic(book_move, board)
            print(f"Best move: {san} ({book_move.uci()})  [from book]")
            return 0
    search = _make_search(args)
    move, score = search.search(board, depth=args.depth, time_limit=args.time)
    if move:
        san = to_algebraic(move, board)
        print(f"Best move: {san} ({move.uci()})  score: {score}")
    else:
        print("No legal moves (game over)")
    info = search.get_info()
    print(f"Nodes: {info['nodes']}  Time: {info['time']:.2f}s  "
          f"NPS: {info['nps']}")
    if info.get("pv"):
        print(f"PV: {' '.join(info['pv'])}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    board = _load_board(args)
    evaluator = Evaluator()
    score = evaluator.evaluate(board)
    print(f"Static evaluation: {score} (from {board.turn}'s perspective)")
    search = _make_search(args)
    move, sc = search.search(board, depth=args.depth, time_limit=args.time)
    if move:
        san = to_algebraic(move, board)
        print(f"Best move: {san} ({move.uci()})  score: {sc}")
    info = search.get_info()
    print(f"Nodes: {info['nodes']}  Time: {info['time']:.2f}s  "
          f"NPS: {info['nps']}")
    if info.get("pv"):
        print(f"PV: {' '.join(info['pv'])}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """Print static evaluation breakdown."""
    board = _load_board(args)
    evaluator = Evaluator()
    score = evaluator.evaluate(board)
    print(f"Static evaluation: {score} (from {board.turn}'s perspective)")
    print(f"Endgame: {evaluator.is_endgame(board)}")
    print(f"Material (absolute): {evaluator._evaluate_absolute(board)}")
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
    import time
    t0 = time.time()
    total = _perft(board, args.depth)
    elapsed = time.time() - t0
    nps = int(total / elapsed) if elapsed > 0 else 0
    print(f"Perft({args.depth}) = {total}")
    print(f"Time: {elapsed:.2f}s  NPS: {nps}")
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    """Engine vs engine self-play."""
    from .game import Game
    board = _load_board(args)
    search = _make_search(args)
    game = Game(board=board, search=search)
    result = game.play_engine_vs_engine(
        depth=args.depth, max_moves=args.max_moves,
        time_limit=args.time,
    )
    if args.pgn:
        pgn_text = game.to_pgn()
        with open(args.pgn, "w") as f:
            f.write(pgn_text)
        print(f"PGN saved to {args.pgn}")
    _save_board(args, game.board)
    return 0


def cmd_play_human(args: argparse.Namespace) -> int:
    """Interactive human vs engine game."""
    from .game import Game
    board = _load_board(args)
    search = _make_search(args)
    game = Game(board=board, search=search)
    human_color = Color.BLACK if args.color.lower() == "black" else Color.WHITE
    game.play_human_vs_engine(
        human_color=human_color,
        depth=args.depth,
        time_limit=args.time,
    )
    if args.pgn:
        pgn_text = game.to_pgn()
        with open(args.pgn, "w") as f:
            f.write(pgn_text)
        print(f"PGN saved to {args.pgn}")
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


def cmd_uci(args: argparse.Namespace) -> int:
    """Run UCI protocol loop."""
    from .uci import UCIEngine
    engine = UCIEngine()
    engine.run()
    return 0


def cmd_pgn(args: argparse.Namespace) -> int:
    """Output the game as PGN."""
    from .pgn import board_to_pgn
    board = _load_board(args)
    pgn_text = board_to_pgn(board, headers={
        "Event": "chess-engine game",
        "White": "chess-engine",
        "Black": "chess-engine",
    })
    print(pgn_text)
    return 0


def cmd_perft_suite(args: argparse.Namespace) -> int:
    """Run a standard perft test suite to verify move generation."""
    suite = [
        ("Starting position",
         "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
         [20, 400, 8902, 197281]),
        ("Kiwipete",
         "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
         [48, 2039, 97862]),
        ("Position 3",
         "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
         [14, 191, 2812, 43238]),
        ("Position 4",
         "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
         [6, 264, 9467]),
        ("Position 5",
         "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
         [44, 1486, 62379]),
        ("Position 6",
         "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
         [46, 2079, 89890]),
    ]
    max_depth = args.depth
    all_pass = True
    for name, fen, expected in suite:
        print(f"\n{name}: {fen}")
        for d in range(1, min(max_depth + 1, len(expected) + 1)):
            b = Board.from_fen(fen)
            count = _perft(b, d)
            exp = expected[d - 1]
            status = "OK" if count == exp else "FAIL"
            if count != exp:
                all_pass = False
            print(f"  Perft({d}) = {count:>10,}  expected {exp:>10,}  [{status}]")
    print(f"\n{'All tests passed!' if all_pass else 'SOME TESTS FAILED!'}")
    return 0 if all_pass else 1


# ── Parser ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-engine",
        description="A chess engine in pure Python — full legal move "
                    "generation, alpha-beta search, opening book, PGN, UCI.",
    )
    parser.add_argument("--fen", default=None, help="FEN string for position")
    parser.add_argument("--file", default=None, help="Load FEN from file")
    parser.add_argument("--save", default=None, help="Save resulting FEN to file")
    parser.add_argument("--config", default=None,
                        help="Path to YAML/JSON config file")

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
    sub_best.add_argument("--no-book", action="store_true",
                          help="Disable opening book")
    sub_best.set_defaults(func=cmd_bestmove)

    sub_analyze = subparsers.add_parser("analyze", help="Analyze position")
    sub_analyze.add_argument("--depth", type=int, default=4,
                             help="Search depth (default: 4)")
    sub_analyze.add_argument("--time", type=float, default=None,
                             help="Time limit in seconds")
    sub_analyze.set_defaults(func=cmd_analyze)

    sub_eval = subparsers.add_parser("eval", help="Print static evaluation")
    sub_eval.set_defaults(func=cmd_eval)

    sub_fen = subparsers.add_parser("fen", help="Output FEN string")
    sub_fen.set_defaults(func=cmd_fen)

    sub_perft = subparsers.add_parser("perft", help="Count move tree nodes")
    sub_perft.add_argument("depth", type=int, help="Perft depth")
    sub_perft.set_defaults(func=cmd_perft)

    sub_perft_suite = subparsers.add_parser(
        "perft-suite", help="Run standard perft test suite")
    sub_perft_suite.add_argument("--depth", type=int, default=3,
                                 help="Max depth to test (default: 3)")
    sub_perft_suite.set_defaults(func=cmd_perft_suite)

    sub_play = subparsers.add_parser("play", help="Engine vs engine self-play")
    sub_play.add_argument("--depth", type=int, default=3,
                          help="Search depth per move (default: 3)")
    sub_play.add_argument("--time", type=float, default=None,
                          help="Time limit per move in seconds")
    sub_play.add_argument("--max-moves", type=int, default=100,
                          help="Maximum moves in game (default: 100)")
    sub_play.add_argument("--pgn", default=None,
                          help="Save game to PGN file")
    sub_play.set_defaults(func=cmd_play)

    sub_play_human = subparsers.add_parser(
        "play-human", help="Play interactively against the engine")
    sub_play_human.add_argument("--depth", type=int, default=4,
                                help="Engine search depth (default: 4)")
    sub_play_human.add_argument("--time", type=float, default=None,
                                help="Engine time limit in seconds")
    sub_play_human.add_argument("--color", default="white",
                                choices=["white", "black"],
                                help="Human color (default: white)")
    sub_play_human.add_argument("--pgn", default=None,
                                help="Save game to PGN file")
    sub_play_human.set_defaults(func=cmd_play_human)

    sub_moves = subparsers.add_parser("moves", help="List all legal moves")
    sub_moves.set_defaults(func=cmd_moves)

    sub_uci = subparsers.add_parser("uci", help="Run UCI protocol (for GUI integration)")
    sub_uci.set_defaults(func=cmd_uci)

    sub_pgn = subparsers.add_parser("pgn", help="Output game as PGN")
    sub_pgn.set_defaults(func=cmd_pgn)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())