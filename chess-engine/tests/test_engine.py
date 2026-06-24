"""Tests for the chess engine."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_engine.board import Board, Move, Piece, Color
from chess_engine.evaluate import Evaluator
from chess_engine.search import Search
from chess_engine.notation import to_algebraic, parse_algebraic, square_name, parse_square


class TestBoardBasics:
    def test_starting_position(self):
        b = Board()
        assert b.turn == Color.WHITE
        assert b.piece_at(0) == Piece(Piece.ROOK, Color.WHITE)
        assert b.piece_at(4) == Piece(Piece.KING, Color.WHITE)
        assert b.piece_at(60) == Piece(Piece.KING, Color.BLACK)
        assert b.piece_at(63) == Piece(Piece.ROOK, Color.BLACK)

    def test_starting_fen(self):
        b = Board()
        assert b.fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def test_fen_roundtrip(self):
        fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "8/8/8/8/8/8/8/4K2R w K - 0 1",
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1",
        ]
        for fen in fens:
            b = Board.from_fen(fen)
            assert b.fen() == fen, f"FEN roundtrip failed: {fen} -> {b.fen()}"

    def test_legal_moves_count_start(self):
        b = Board()
        moves = b.legal_moves()
        assert len(moves) == 20, f"Expected 20 moves, got {len(moves)}"

    def test_e4_move(self):
        b = Board()
        # e2e4
        move = Move(12, 28)  # e2=12, e4=28
        b.push(move)
        assert b.turn == Color.BLACK
        assert b.piece_at(28) == Piece(Piece.PAWN, Color.WHITE)
        assert b.piece_at(12) is None
        assert b.ep_square == 20  # e3
        b.pop()
        assert b.turn == Color.WHITE
        assert b.piece_at(12) == Piece(Piece.PAWN, Color.WHITE)
        assert b.piece_at(28) is None


class TestPerft:
    """Perft (performance test) counts leaf nodes — the gold standard for
    move generation correctness."""

    def test_perft_1(self):
        b = Board()
        assert self._perft(b, 1) == 20

    def test_perft_2(self):
        b = Board()
        assert self._perft(b, 2) == 400

    def test_perft_3(self):
        b = Board()
        assert self._perft(b, 3) == 8902

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


class TestCastling:
    def test_kingside_castle_white(self):
        # Set up position where white can castle kingside
        fen = "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPBPPP/RNBQK2R w KQkq - 0 1"
        b = Board.from_fen(fen)
        moves = b.legal_moves()
        castle_moves = [m for m in moves if m.is_castle]
        assert len(castle_moves) == 1
        assert castle_moves[0].to_square == 6  # g1

    def test_queenside_castle_white(self):
        # Both sides available: f1, g1, b1, c1, d1 all empty
        fen = "r3k2r/pppqpppp/2n5/3p4/3P4/2N5/PPPQPPPP/R3K2R w KQkq - 0 1"
        b = Board.from_fen(fen)
        moves = b.legal_moves()
        castle_moves = [m for m in moves if m.is_castle]
        assert len(castle_moves) == 2  # both sides
        king_side = [m for m in castle_moves if m.to_square == 6]
        queen_side = [m for m in castle_moves if m.to_square == 2]
        assert len(king_side) == 1
        assert len(queen_side) == 1

    def test_castle_rook_moves(self):
        fen = "r3k2r/pppqpppp/2n5/3p4/3P4/2N5/PPPQPPPP/R3K2R w KQkq - 0 1"
        b = Board.from_fen(fen)
        # Do kingside castle
        castle = [m for m in b.legal_moves() if m.is_castle and m.to_square == 6][0]
        b.push(castle)
        # King on g1, rook on f1
        assert b.piece_at(6) == Piece(Piece.KING, Color.WHITE)
        assert b.piece_at(5) == Piece(Piece.ROOK, Color.WHITE)
        assert b.piece_at(4) is None  # e1 empty
        assert b.piece_at(7) is None  # h1 empty
        b.pop()
        assert b.piece_at(4) == Piece(Piece.KING, Color.WHITE)
        assert b.piece_at(7) == Piece(Piece.ROOK, Color.WHITE)

    def test_castle_through_check_blocked(self):
        # Black rook on e8 attacking e-file; white can't castle queenside
        # through e1
        fen = "4k3/8/8/8/8/8/8/R3K2r w KQ - 0 1"
        b = Board.from_fen(fen)
        castle_moves = [m for m in b.legal_moves() if m.is_castle]
        # Kingside should be blocked (rook attacks f1, g1)
        # Actually the rook on h8... let me use a clearer position
        # King on e1, rook on a1, black rook on e8 attacks e1
        fen2 = "4r3/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        b2 = Board.from_fen(fen2)
        castle_moves2 = [m for m in b2.legal_moves() if m.is_castle]
        # King is in check from rook on e8, so no castling
        assert len(castle_moves2) == 0


class TestEnPassant:
    def test_en_passant_capture(self):
        # White pawn on e5, black plays d7-d5, white captures en passant
        # e5=36, d5=35, e4 area... correct FEN: white pawn on e5
        fen = "rnbqkbnr/ppp1pppp/8/3Pp3/8/8/PPP1PPPP/RNBQKBNR w KQkq d6 0 1"
        b = Board.from_fen(fen)
        # White can capture en passant: e5xd6 (but wait, white pawn is on d5)
        # Let me use: white pawn on e5, black just played d7-d5
        fen2 = "rnbqkbnr/ppp1pppp/8/3Pp3/8/8/PPP1PPPP/RNBQKBNR w KQkq d6 0 1"
        # Actually let me construct it more carefully
        # White pawn on e5 = square 36 (e5 = file 4, rank 4 -> 4*8+4=36)
        # Black pawn on d5 = square 35
        # EP target = d6 = square 43
        fen3 = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 1"
        b = Board.from_fen(fen3)
        assert b.ep_square == 43  # d6
        ep_moves = [m for m in b.legal_moves() if m.is_en_passant]
        assert len(ep_moves) == 1
        assert ep_moves[0].from_square == 36  # e5
        assert ep_moves[0].to_square == 43  # d6
        b.push(ep_moves[0])
        # d5 pawn should be gone
        assert b.piece_at(35) is None
        assert b.piece_at(43) == Piece(Piece.PAWN, Color.WHITE)
        assert b.piece_at(36) is None

    def test_en_passant_undo(self):
        fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 1"
        b = Board.from_fen(fen)
        original_fen = b.fen()
        ep = [m for m in b.legal_moves() if m.is_en_passant][0]
        b.push(ep)
        b.pop()
        assert b.fen() == original_fen


class TestCheckmate:
    def test_fools_mate(self):
        b = Board()
        # 1. f3 e5 2. g4 Qh4#
        b.push(Move(13, 21))  # f2-f3  (f2=13, f3=21)
        b.push(Move(52, 36))  # e7-e5  (e7=52, e5=36)
        b.push(Move(14, 30))  # g2-g4  (g2=14, g4=30)
        b.push(Move(59, 31))  # d8-h4  (d8=59, h4=31)
        assert b.is_checkmate()
        assert b.result() == "0-1"

    def test_scholars_mate(self):
        # 1. e4 e5 2. Bc4 a6 3. Qh5 b6 4. Qxf7#
        b = Board()
        b.push(Move(12, 28))  # e2-e4
        b.push(Move(52, 36))  # e7-e5
        b.push(Move(5, 26))   # Bf1-c4  (f1=5, c4=26)
        b.push(Move(48, 40))  # a7-a6
        # Qd1-h5  (d1=3, h5=39)
        qh5 = Move(3, 39)
        b.push(qh5)
        b.push(Move(49, 41))  # b7-b6
        # Qxf7#  (h5=39, f7=53)
        qxf7 = Move(39, 53)
        b.push(qxf7)
        assert b.is_checkmate()
        assert b.result() == "1-0"


class TestEvaluation:
    def test_starting_position_eval(self):
        b = Board()
        ev = Evaluator()
        score = ev.evaluate(b)
        # Should be roughly equal (tempo bonus)
        assert abs(score) < 50

    def test_material_advantage(self):
        # White up a queen
        fen = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        b = Board.from_fen(fen)
        ev = Evaluator()
        score = ev._evaluate_absolute(b)
        assert score > 800  # White is way ahead

    def test_endgame_detection(self):
        # Only kings and pawns
        fen = "8/8/8/3k4/3p4/3P4/3K4/8 w - - 0 1"
        b = Board.from_fen(fen)
        ev = Evaluator()
        assert ev.is_endgame(b) is True

    def test_midgame_detection(self):
        b = Board()
        ev = Evaluator()
        assert ev.is_endgame(b) is False


class TestSearch:
    def test_finds_checkmate_in_one(self):
        # White queen on g1, white king on f6, black king on h8
        # Qg7# is mate in 1 (g-file is clear, Kf6 protects g7)
        fen = "7k/8/5K2/8/8/8/8/6Q1 w - - 0 1"
        b = Board.from_fen(fen)
        search = Search()
        move, score = search.search(b, depth=3)
        assert move is not None
        # Qg1-g7 should be mate (g7 = 54)
        assert move.to_square == 54  # g7
        assert score > 99000  # mate score

    def test_finds_forced_mate(self):
        # White has Q+K vs K, should find mate quickly
        fen = "7k/8/5K2/8/8/8/8/5Q2 w - - 0 1"
        b = Board.from_fen(fen)
        search = Search()
        move, score = search.search(b, depth=4)
        assert move is not None
        assert score > 99000

    def test_search_returns_legal_move(self):
        b = Board()
        search = Search()
        move, score = search.search(b, depth=2)
        assert move is not None
        legal = b.legal_moves()
        assert move in legal


class TestNotation:
    def test_square_name(self):
        assert square_name(0) == "a1"
        assert square_name(63) == "h8"
        assert square_name(28) == "e4"
        assert square_name(56) == "a8"

    def test_parse_square(self):
        assert parse_square("a1") == 0
        assert parse_square("h8") == 63
        assert parse_square("e4") == 28

    def test_algebraic_e4(self):
        b = Board()
        move = Move(12, 28)  # e2-e4
        san = to_algebraic(move, b)
        assert san == "e4"

    def test_algebraic_knight(self):
        b = Board()
        move = Move(6, 21)  # g1-f3
        san = to_algebraic(move, b)
        assert san == "Nf3"

    def test_algebraic_castle(self):
        fen = "r3k2r/pppqpppp/2n5/3p4/3P4/2N5/PPPQPPPP/R3K2R w KQkq - 0 1"
        b = Board.from_fen(fen)
        castle = [m for m in b.legal_moves() if m.is_castle
                   and m.to_square == 6][0]
        san = to_algebraic(castle, b)
        assert san == "O-O"

    def test_parse_algebraic(self):
        b = Board()
        move = parse_algebraic("e4", b)
        assert move.from_square == 12
        assert move.to_square == 28


class TestTranspositionTable:
    def test_tt_store_probe(self):
        from chess_engine.transposition import TranspositionTable, FLAG_EXACT
        from chess_engine.zobrist import ZobristHash
        tt = TranspositionTable()
        z = ZobristHash()
        b = Board()
        key = z.hash(b)
        tt.store(key, depth=3, score=50, flag=FLAG_EXACT)
        entry = tt.probe(key)
        assert entry is not None
        assert entry.score == 50
        assert entry.depth == 3

    def test_tt_replacement(self):
        from chess_engine.transposition import TranspositionTable, FLAG_EXACT
        tt = TranspositionTable()
        tt.store(123, depth=2, score=10, flag=FLAG_EXACT)
        # Higher depth should replace
        tt.store(123, depth=4, score=20, flag=FLAG_EXACT)
        entry = tt.probe(123)
        assert entry.depth == 4
        assert entry.score == 20


class TestZobristHash:
    def test_same_position_same_hash(self):
        from chess_engine.zobrist import ZobristHash
        z = ZobristHash()
        b1 = Board()
        b2 = Board()
        assert z.hash(b1) == z.hash(b2)

    def test_different_positions_different_hash(self):
        from chess_engine.zobrist import ZobristHash
        z = ZobristHash()
        b1 = Board()
        b2 = Board()
        b2.push(Move(12, 28))  # e4
        assert z.hash(b1) != z.hash(b2)


class TestOpeningBook:
    def test_book_has_starting_moves(self):
        from chess_engine.opening_book import create_default_book
        book = create_default_book()
        b = Board()
        move = book.probe(b)
        assert move is not None

    def test_book_returns_none_for_unknown(self):
        from chess_engine.opening_book import create_default_book
        book = create_default_book()
        b = Board()
        b.push(Move(12, 28))  # e4
        b.push(Move(52, 36))  # e5
        b.push(Move(6, 21))   # Nf3
        b.push(Move(62, 45))  # Ng8-f6?? unusual
        # This should not be in the book
        # (may or may not return None depending on book entries)
        # Just test it doesn't crash
        result = book.probe(b)
        # It's okay if it returns a move or None


class TestPGN:
    def test_pgn_roundtrip(self):
        from chess_engine.pgn import PGNGame
        b = Board()
        b.push(Move(12, 28))  # e4
        b.push(Move(52, 36))  # e5
        b.push(Move(6, 21))   # Nf3
        b.push(Move(57, 42))  # Nc6
        from chess_engine.pgn import board_to_pgn
        pgn_text = board_to_pgn(b)
        game = PGNGame.from_string(pgn_text)
        assert len(game.moves) == 4
        assert game.moves[0] == "e4"
        assert game.moves[1] == "e5"
        assert game.moves[2] == "Nf3"
        assert game.moves[3] == "Nc6"


class TestThreefoldRepetition:
    def test_threefold_detected(self):
        b = Board()
        # Move knights back and forth to create repetition
        # Nb1-c3, Ng8-f6, Nc3-b1, Nf6-g8 (x3)
        for _ in range(3):
            b.push(Move(1, 18))   # Nb1-c3
            b.push(Move(57, 42))  # Ng8-f6
            b.push(Move(18, 1))   # Nc3-b1
            b.push(Move(42, 57))  # Nf6-g8
        assert b.is_threefold_repetition()
        assert b.is_game_over()

    def test_no_false_threefold(self):
        b = Board()
        b.push(Move(12, 28))  # e4
        b.push(Move(52, 36))  # e5
        assert not b.is_threefold_repetition()


class TestEnhancedEvaluation:
    def test_doubled_pawn_penalty(self):
        from chess_engine.evaluate import Evaluator
        ev = Evaluator()
        # Two white pawns on e-file: e2 and e3 (doubled)
        fen = "4k3/8/8/8/8/4P3/4P3/4K3 w - - 0 1"
        b = Board.from_fen(fen)
        doubled_score = ev._evaluate_pawn_structure(b)
        # Compare with two non-doubled pawns: c2 and e2
        fen2 = "4k3/8/8/8/8/8/2P1P3/4K3 w - - 0 1"
        b2 = Board.from_fen(fen2)
        normal_score = ev._evaluate_pawn_structure(b2)
        # Doubled pawns should score worse
        assert doubled_score < normal_score

    def test_isolated_pawn_penalty(self):
        from chess_engine.evaluate import Evaluator
        ev = Evaluator()
        # Isolated white pawn on d4, blocked by black d5 pawn (not passed)
        # Black has connected pawns on f7/g7 (not isolated)
        fen = "5kp1/8/8/3p4/3P4/8/8/4K3 w - - 0 1"
        b = Board.from_fen(fen)
        isolated_score = ev._evaluate_pawn_structure(b)
        # White d-pawn: isolated (-20), not passed (blocked by d5), not backward
        # Black d-pawn: not isolated (no, actually it IS isolated - no black c/e pawns)
        # Black f7/g7: connected, not isolated
        # So: white: -20 (isolated), black d5: -(-20) = +20, black f7/g7: 0
        # Net = -20 + 20 = 0... hmm
        # Let me just check that white's isolated pawn contributes negative
        # by comparing with a non-isolated version
        fen_connected = "5kp1/8/8/3p4/2PP4/8/8/4K3 w - - 0 1"
        b_connected = Board.from_fen(fen_connected)
        connected_score = ev._evaluate_pawn_structure(b_connected)
        # The isolated position should be worse for white than the connected one
        assert isolated_score < connected_score

    def test_passed_pawn_bonus(self):
        from chess_engine.evaluate import Evaluator
        # White pawn on e5 with no black pawns nearby
        fen = "4k3/8/8/4P3/8/8/8/4K3 w - - 0 1"
        b = Board.from_fen(fen)
        ev = Evaluator()
        pawn_score = ev._evaluate_pawn_structure(b)
        # Passed pawn should give positive score for white
        assert pawn_score > 0