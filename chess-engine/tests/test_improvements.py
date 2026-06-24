"""Tests for the comprehensive improvement features.

Covers:
- Null move pruning
- Late move reductions (LMR)
- History heuristic
- Principal variation tracking
- Push/pop null move
- Configuration loading
- Game manager
- Expanded opening book
- Perft suite (standard positions)
- CLI parser
"""

import sys
import os
import io
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_engine.board import Board, Move, Piece, Color
from chess_engine.search import Search
from chess_engine.evaluate import Evaluator
from chess_engine.notation import to_algebraic, parse_algebraic, square_name
from chess_engine.config import load_config, apply_search_config, DEFAULT_CONFIG
from chess_engine.game import Game
from chess_engine.opening_book import create_default_book
from chess_engine.pgn import PGNGame


class TestNullMovePruning:
    """Test null-move pruning and null push/pop."""

    def test_push_null_changes_turn(self):
        b = Board()
        assert b.turn == Color.WHITE
        b.push_null()
        assert b.turn == Color.BLACK
        b.pop_null()
        assert b.turn == Color.WHITE

    def test_push_null_clears_ep(self):
        """En passant square should be cleared on null move."""
        b = Board()
        b.push(Move(12, 28))  # e2-e4, sets ep to e3
        assert b.ep_square == 20
        b.push_null()
        assert b.ep_square == -1
        b.pop_null()
        assert b.ep_square == 20
        b.pop()

    def test_push_null_increments_halfmove(self):
        b = Board.from_fen("4k3/8/8/8/8/8/8/4K3 w - - 5 10")
        b.push_null()
        assert b.halfmove_clock == 6
        b.pop_null()
        assert b.halfmove_clock == 5

    def test_null_move_pruning_enabled(self):
        """Search with null move pruning should still find mates."""
        fen = "7k/5K2/8/8/8/8/8/5Q2 w - - 0 1"
        b = Board.from_fen(fen)
        search = Search()
        search.use_null_move = True
        move, score = search.search(b, depth=4)
        assert move is not None
        assert score > 99000  # mate found

    def test_null_move_disabled_still_correct(self):
        """Search without null move pruning should also find mates."""
        fen = "7k/5K2/8/8/8/8/8/5Q2 w - - 0 1"
        b = Board.from_fen(fen)
        search = Search()
        search.use_null_move = False
        move, score = search.search(b, depth=4)
        assert move is not None
        assert score > 99000

    def test_null_move_fen_roundtrip(self):
        """Null move push/pop should preserve FEN (except ep)."""
        b = Board.from_fen("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        original_fen = b.fen()
        b.push_null()
        b.pop_null()
        # EP square is cleared and restored, so FEN should match
        assert b.fen() == original_fen


class TestLateMoveReductions:
    """Test late move reductions don't break search."""

    def test_lmr_enabled_finds_mate(self):
        fen = "7k/5K2/8/8/8/8/8/5Q2 w - - 0 1"
        b = Board.from_fen(fen)
        search = Search()
        search.use_lmr = True
        move, score = search.search(b, depth=4)
        assert move is not None
        assert score > 99000

    def test_lmr_disabled_finds_mate(self):
        fen = "7k/5K2/8/8/8/8/8/5Q2 w - - 0 1"
        b = Board.from_fen(fen)
        search = Search()
        search.use_lmr = False
        move, score = search.search(b, depth=4)
        assert move is not None
        assert score > 99000

    def test_lmr_starting_position(self):
        """Search with LMR should return a legal move from the start."""
        b = Board()
        search = Search()
        search.use_lmr = True
        move, score = search.search(b, depth=3)
        assert move is not None
        assert move in b.legal_moves()


class TestHistoryHeuristic:
    """Test history heuristic move ordering."""

    def test_history_starts_zero(self):
        search = Search()
        for i in range(64):
            for j in range(64):
                assert search.history[i][j] == 0

    def test_history_updates_on_cutoff(self):
        """After searching, history table should have some entries."""
        b = Board()
        search = Search()
        search.use_history = True
        search.search(b, depth=3)
        # After a search, some history entries should be non-zero
        total = sum(search.history[i][j]
                     for i in range(64) for j in range(64))
        assert total > 0, "History heuristic didn't record any cutoffs"

    def test_history_disabled(self):
        """Search should still work with history disabled."""
        b = Board()
        search = Search()
        search.use_history = False
        move, score = search.search(b, depth=3)
        assert move is not None


class TestPrincipalVariation:
    """Test principal variation tracking."""

    def test_pv_returned_after_search(self):
        b = Board()
        search = Search()
        search.search(b, depth=3)
        info = search.get_info()
        assert "pv" in info
        assert isinstance(info["pv"], list)

    def test_pv_leads_to_mate(self):
        """PV from a mate search should contain moves leading to mate."""
        fen = "7k/5K2/8/8/8/8/8/5Q2 w - - 0 1"
        b = Board.from_fen(fen)
        search = Search()
        search.search(b, depth=4)
        info = search.get_info()
        assert len(info["pv"]) > 0
        # PV moves should be valid UCI strings
        for uci in info["pv"]:
            assert len(uci) >= 4


class TestSearchConfiguration:
    """Test that search flags can be toggled."""

    def test_all_features_enabled(self):
        search = Search()
        assert search.use_quiescence
        assert search.use_killers
        assert search.use_history
        assert search.use_lmr
        assert search.use_null_move
        assert search.use_iterative_deepening
        assert search.use_tt

    def test_disable_each_feature(self):
        search = Search()
        search.use_null_move = False
        search.use_lmr = False
        search.use_history = False
        search.use_killers = False
        b = Board()
        move, score = search.search(b, depth=2)
        assert move is not None

    def test_reset(self):
        search = Search()
        search.nodes = 100
        search.best_score = 50
        search.reset()
        assert search.nodes == 0
        assert search.best_score == 0
        assert search.best_move is None


class TestConfig:
    """Test configuration file support."""

    def test_default_config(self):
        cfg = load_config(None)
        assert cfg == DEFAULT_CONFIG
        assert cfg["search"]["max_depth"] == 4

    def test_json_config(self):
        """Load a JSON config file."""
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False) as f:
            json.dump({"search": {"max_depth": 6, "use_null_move": False}}, f)
            path = f.name
        try:
            cfg = load_config(path)
            assert cfg["search"]["max_depth"] == 6
            assert cfg["search"]["use_null_move"] is False
            # Other defaults preserved
            assert cfg["search"]["use_killers"] is True
        finally:
            os.unlink(path)

    def test_apply_search_config(self):
        cfg = {"search": {"max_depth": 7, "use_lmr": False}}
        search = Search()
        apply_search_config(search, cfg)
        assert search.max_depth == 7
        assert search.use_lmr is False
        # Others unchanged
        assert search.use_null_move is True

    def test_nonexistent_file_returns_defaults(self):
        cfg = load_config("/nonexistent/path/to/config.yaml")
        assert cfg == DEFAULT_CONFIG


class TestGame:
    """Test the Game manager."""

    def test_engine_move_from_start(self):
        game = Game()
        result = game.play_engine_move(depth=2)
        assert result is not None
        move, score = result
        assert move is not None
        assert len(game.move_history) == 1
        assert len(game.san_history) == 1

    def test_human_move_san(self):
        game = Game()
        assert game.play_human_move("e4")
        assert len(game.move_history) == 1

    def test_human_move_uci(self):
        game = Game()
        assert game.play_human_move("e2e4")
        assert len(game.move_history) == 1

    def test_illegal_human_move(self):
        game = Game()
        assert not game.play_human_move("e5")  # black's move, illegal for white
        assert not game.play_human_move("z9z9")  # garbage
        assert not game.play_human_move("e2e5")  # not a legal pawn move
        assert len(game.move_history) == 0

    def test_engine_vs_engine(self):
        game = Game()
        output = io.StringIO()
        result = game.play_engine_vs_engine(
            depth=2, max_moves=20, output=output)
        # Game should have produced some moves
        assert len(game.move_history) > 0
        # Result should be a valid result string
        assert result in ("1-0", "0-1", "1/2-1/2", "*")

    def test_to_pgn(self):
        game = Game()
        game.play_engine_move(depth=2)
        game.play_engine_move(depth=2)
        pgn = game.to_pgn()
        assert "[Event" in pgn
        assert len(game.san_history) == 2

    def test_game_from_fen(self):
        """Game should work from a custom FEN position."""
        board = Board.from_fen("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        game = Game(board=board)
        result = game.play_engine_move(depth=2)
        assert result is not None

    def test_game_over_no_move(self):
        """When game is over, play_engine_move should return None."""
        # Fool's mate
        board = Board()
        board.push(Move(13, 21))  # f3
        board.push(Move(52, 36))  # e5
        board.push(Move(14, 30))  # g4
        board.push(Move(59, 31))  # Qh4#
        game = Game(board=board)
        assert game.play_engine_move(depth=2) is None


class TestExpandedOpeningBook:
    """Test the expanded opening book."""

    def test_book_has_more_entries(self):
        book = create_default_book()
        # Should have more entries than the old 15-line book
        assert len(book.entries) >= 30

    def test_book_covers_sicilian(self):
        """Sicilian Defense lines should be in the book."""
        book = create_default_book()
        b = Board()
        b.push(Move(12, 28))  # e4
        b.push(Move(48, 34))  # c5  (a7-a6? no, c5 = square 34)
        # Actually c5 = file 2, rank 4 = 4*8+2 = 34
        # But pawn is on c7 = 50, so c7-c5 = 50->34... wait
        # c7 = 50? c=2, rank 7=6, so 6*8+2=50. c5 = 4*8+2=34
        # Move(50, 34)
        b2 = Board()
        b2.push(Move(12, 28))  # e4
        b2.push(Move(50, 34))  # c5
        move = book.probe(b2)
        assert move is not None  # Should have Nf3 in book

    def test_book_covers_queens_gambit(self):
        book = create_default_book()
        b = Board()
        b.push(Move(11, 27))  # d4
        b.push(Move(51, 35))  # d5
        move = book.probe(b)
        assert move is not None  # Should have c4 in book

    def test_book_covers_kings_indian(self):
        book = create_default_book()
        b = Board()
        b.push(parse_algebraic("d4", b))
        b.push(parse_algebraic("Nf6", b))
        b.push(parse_algebraic("c4", b))
        b.push(parse_algebraic("g6", b))
        move = book.probe(b)
        assert move is not None  # Should have Nc3 in book


class TestPerftSuite:
    """Standard perft test positions to verify move generation correctness."""

    def _perft(self, board, depth):
        if depth == 0:
            return 1
        if depth == 1:
            return len(board.legal_moves())
        count = 0
        for move in board.legal_moves():
            board.push(move)
            count += self._perft(board, depth - 1)
            board.pop()
        return count

    def test_starting_perft_1(self):
        b = Board()
        assert self._perft(b, 1) == 20

    def test_starting_perft_2(self):
        b = Board()
        assert self._perft(b, 2) == 400

    def test_starting_perft_3(self):
        b = Board()
        assert self._perft(b, 3) == 8902

    def test_kiwipete_perft_1(self):
        fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
        b = Board.from_fen(fen)
        assert self._perft(b, 1) == 48

    def test_kiwipete_perft_2(self):
        fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
        b = Board.from_fen(fen)
        assert self._perft(b, 2) == 2039

    def test_position3_perft_1(self):
        fen = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
        b = Board.from_fen(fen)
        assert self._perft(b, 1) == 14

    def test_position3_perft_2(self):
        fen = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
        b = Board.from_fen(fen)
        assert self._perft(b, 2) == 191

    def test_position4_perft_1(self):
        fen = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
        b = Board.from_fen(fen)
        assert self._perft(b, 1) == 6

    def test_position5_perft_1(self):
        fen = "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"
        b = Board.from_fen(fen)
        assert self._perft(b, 1) == 44


class TestCLIParser:
    """Test CLI argument parser construction."""

    def test_parser_has_all_commands(self):
        from chess_engine.cli import build_parser
        parser = build_parser()
        # Check that all subcommands exist
        actions = {a.choices for a in parser._actions
                   if isinstance(a, type(parser._subparsers))}
        # The subparsers action should have choices
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                commands = action.choices
                assert "display" in commands
                assert "move" in commands
                assert "bestmove" in commands
                assert "analyze" in commands
                assert "fen" in commands
                assert "perft" in commands
                assert "perft-suite" in commands
                assert "play" in commands
                assert "play-human" in commands
                assert "moves" in commands
                assert "uci" in commands
                assert "pgn" in commands
                assert "eval" in commands
                break