"""Core chess board representation, move generation, and game state.

Uses a 0x88-style board representation on a 64-square array.
Square indexing: 0 = a1, 1 = b1, ..., 7 = h1, 8 = a2, ..., 63 = h8.
"""

from __future__ import annotations

import copy
from enum import IntEnum
from typing import List, Optional, Tuple, Iterator

FILE_NAMES = "abcdefgh"
RANK_NAMES = "12345678"


class Color(IntEnum):
    WHITE = 0
    BLACK = 1

    @property
    def opposite(self) -> "Color":
        return Color.BLACK if self == Color.WHITE else Color.WHITE

    def symbol(self) -> str:
        return "w" if self == Color.WHITE else "b"

    def __str__(self) -> str:
        return "white" if self == Color.WHITE else "black"


class Square(IntEnum):
    A1 = 0; B1 = 1; C1 = 2; D1 = 3; E1 = 4; F1 = 5; G1 = 6; H1 = 7
    A2 = 8; B2 = 9; C2 = 10; D2 = 11; E2 = 12; F2 = 13; G2 = 14; H2 = 15
    A3 = 16; B3 = 17; C3 = 18; D3 = 19; E3 = 20; F3 = 21; G3 = 22; H3 = 23
    A4 = 24; B4 = 25; C4 = 26; D4 = 27; E4 = 28; F4 = 29; G4 = 30; H4 = 31
    A5 = 32; B5 = 33; C5 = 34; D5 = 35; E5 = 36; F5 = 37; G5 = 38; H5 = 39
    A6 = 40; B6 = 41; C6 = 42; D6 = 43; E6 = 44; F6 = 45; G6 = 46; H6 = 47
    A7 = 48; B7 = 49; C7 = 50; D7 = 51; E7 = 52; F7 = 53; G7 = 54; H7 = 55
    A8 = 56; B8 = 57; C8 = 58; D8 = 59; E8 = 60; F8 = 61; G8 = 62; H8 = 63


class Piece:
    """A chess piece with a type and color."""

    EMPTY = 0
    PAWN = 1
    KNIGHT = 2
    BISHOP = 3
    ROOK = 4
    QUEEN = 5
    KING = 6

    # Unicode symbols for display
    _SYMBOLS = {
        (PAWN, Color.WHITE): "P", (KNIGHT, Color.WHITE): "N",
        (BISHOP, Color.WHITE): "B", (ROOK, Color.WHITE): "R",
        (QUEEN, Color.WHITE): "Q", (KING, Color.WHITE): "K",
        (PAWN, Color.BLACK): "p", (KNIGHT, Color.BLACK): "n",
        (BISHOP, Color.BLACK): "b", (ROOK, Color.BLACK): "r",
        (QUEEN, Color.BLACK): "q", (KING, Color.BLACK): "k",
    }

    _UNICODE = {
        (PAWN, Color.WHITE): "♙", (KNIGHT, Color.WHITE): "♘",
        (BISHOP, Color.WHITE): "♗", (ROOK, Color.WHITE): "♖",
        (QUEEN, Color.WHITE): "♕", (KING, Color.WHITE): "♔",
        (PAWN, Color.BLACK): "♟", (KNIGHT, Color.BLACK): "♞",
        (BISHOP, Color.BLACK): "♝", (ROOK, Color.BLACK): "♜",
        (QUEEN, Color.BLACK): "♛", (KING, Color.BLACK): "♚",
    }

    _VALUES = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500,
               QUEEN: 900, KING: 20000}

    PIECE_NAMES = {1: "pawn", 2: "knight", 3: "bishop", 4: "rook",
                   5: "queen", 6: "king"}

    def __init__(self, piece_type: int, color: Color):
        self.piece_type = piece_type
        self.color = color

    @property
    def value(self) -> int:
        return self._VALUES.get(self.piece_type, 0)

    def symbol(self) -> str:
        return self._SYMBOLS.get((self.piece_type, self.color), ".")

    def unicode(self) -> str:
        return self._UNICODE.get((self.piece_type, self.color), ".")

    def name(self) -> str:
        return self.PIECE_NAMES.get(self.piece_type, "empty")

    def is_empty(self) -> bool:
        return self.piece_type == Piece.EMPTY

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Piece):
            return NotImplemented
        return self.piece_type == other.piece_type and self.color == other.color

    def __repr__(self) -> str:
        return f"Piece({self.name()}, {self.color})"

    def __hash__(self) -> int:
        return hash((self.piece_type, self.color))


class Move:
    """Represents a chess move."""

    def __init__(
        self,
        from_square: int,
        to_square: int,
        promotion: Optional[Piece] = None,
        is_castle: bool = False,
        is_en_passant: bool = False,
    ):
        self.from_square = from_square
        self.to_square = to_square
        self.promotion = promotion  # A Piece object for the promotion type/color
        self.is_castle = is_castle
        self.is_en_passant = is_en_passant

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return NotImplemented
        return (
            self.from_square == other.from_square
            and self.to_square == other.to_square
            and (self.promotion == other.promotion)
            and self.is_castle == other.is_castle
            and self.is_en_passant == other.is_en_passant
        )

    def __hash__(self) -> int:
        return hash((
            self.from_square, self.to_square,
            self.promotion.piece_type if self.promotion else 0,
            self.is_castle, self.is_en_passant,
        ))

    def __repr__(self) -> str:
        from chess_engine.notation import square_name
        s = f"Move({square_name(self.from_square)}-{square_name(self.to_square)}"
        if self.promotion:
            s += f"={self.promotion.symbol()}"
        if self.is_castle:
            s += ",castle"
        if self.is_en_passant:
            s += ",ep"
        s += ")"
        return s

    def uci(self) -> str:
        """Return move in UCI format like 'e2e4' or 'e7e8q'."""
        from chess_engine.notation import square_name
        s = square_name(self.from_square) + square_name(self.to_square)
        if self.promotion:
            s += self.promotion.symbol().lower()
        return s


# Knight move offsets (file, rank deltas)
KNIGHT_OFFSETS = [
    (1, 2), (2, 1), (2, -1), (1, -2),
    (-1, -2), (-2, -1), (-2, 1), (-1, 2),
]

# King move offsets (file, rank deltas)
KING_OFFSETS = [
    (1, 0), (1, 1), (0, 1), (-1, 1),
    (-1, 0), (-1, -1), (0, -1), (1, -1),
]

# Bishop sliding directions (file, rank deltas)
BISHOP_DIRS = [(1, 1), (1, -1), (-1, -1), (-1, 1)]

# Rook sliding directions
ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# Queen sliding directions
QUEEN_DIRS = BISHOP_DIRS + ROOK_DIRS


def _on_board(file: int, rank: int) -> bool:
    return 0 <= file <= 7 and 0 <= rank <= 7


class Board:
    """A chess board with full move generation and state tracking.

    Board state includes:
    - 64-square array of pieces (or None)
    - Side to move
    - Castling rights (white kingside, white queenside, black kingside, black queenside)
    - En passant target square (or -1)
    - Halfmove clock (for 50-move rule)
    - Fullmove number
    """

    STARTING_FEN = (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )

    def __init__(self) -> None:
        self.squares: List[Optional[Piece]] = [None] * 64
        self.turn: Color = Color.WHITE
        # Castling rights: WK, WQ, BK, BQ
        self.castling_rights = {
            Color.WHITE: {"K": False, "Q": False},
            Color.BLACK: {"K": False, "Q": False},
        }
        self.ep_square: int = -1  # en passant target square
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        self.history: List[dict] = []  # for undo
        self._king_squares = {
            Color.WHITE: -1,
            Color.BLACK: -1,
        }
        self._set_fen(self.STARTING_FEN)

    # --- FEN ---

    @classmethod
    def from_fen(cls, fen: str) -> "Board":
        b = cls.__new__(cls)
        b.squares = [None] * 64
        b.turn = Color.WHITE
        b.castling_rights = {
            Color.WHITE: {"K": False, "Q": False},
            Color.BLACK: {"K": False, "Q": False},
        }
        b.ep_square = -1
        b.halfmove_clock = 0
        b.fullmove_number = 1
        b.history = []
        b._king_squares = {Color.WHITE: -1, Color.BLACK: -1}
        b._set_fen(fen)
        return b

    def _set_fen(self, fen: str) -> None:
        """Parse and set the board state from a FEN string."""
        parts = fen.strip().split()
        if len(parts) < 1:
            raise ValueError(f"Invalid FEN: {fen!r}")

        # Piece placement
        ranks = parts[0].split("/")
        if len(ranks) != 8:
            raise ValueError(f"Invalid FEN board: {parts[0]!r}")
        self.squares = [None] * 64
        for rank_idx, row in enumerate(ranks):
            rank = 7 - rank_idx  # FEN starts from rank 8
            file = 0
            for ch in row:
                if ch.isdigit():
                    file += int(ch)
                else:
                    piece = _char_to_piece(ch)
                    if piece is None:
                        raise ValueError(f"Invalid FEN char: {ch!r}")
                    sq = rank * 8 + file
                    self.squares[sq] = piece
                    if piece.piece_type == Piece.KING:
                        self._king_squares[piece.color] = sq
                    file += 1
            if file != 8:
                raise ValueError(f"Invalid FEN rank: {row!r}")

        # Side to move
        self.turn = Color.WHITE if parts[1] == "w" else Color.BLACK

        # Castling rights
        self.castling_rights = {
            Color.WHITE: {"K": False, "Q": False},
            Color.BLACK: {"K": False, "Q": False},
        }
        if len(parts) > 2 and parts[2] != "-":
            for ch in parts[2]:
                if ch == "K":
                    self.castling_rights[Color.WHITE]["K"] = True
                elif ch == "Q":
                    self.castling_rights[Color.WHITE]["Q"] = True
                elif ch == "k":
                    self.castling_rights[Color.BLACK]["K"] = True
                elif ch == "q":
                    self.castling_rights[Color.BLACK]["Q"] = True

        # En passant target
        self.ep_square = -1
        if len(parts) > 3 and parts[3] != "-":
            from chess_engine.notation import parse_square
            self.ep_square = parse_square(parts[3])

        # Halfmove clock
        self.halfmove_clock = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove_number = int(parts[5]) if len(parts) > 5 else 1

    def fen(self) -> str:
        """Return the current position as a FEN string."""
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty = 0
            for file in range(8):
                sq = rank * 8 + file
                p = self.squares[sq]
                if p is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += p.symbol()
            if empty:
                row += str(empty)
            rows.append(row)
        placement = "/".join(rows)

        turn = "w" if self.turn == Color.WHITE else "b"

        castling = ""
        if self.castling_rights[Color.WHITE]["K"]:
            castling += "K"
        if self.castling_rights[Color.WHITE]["Q"]:
            castling += "Q"
        if self.castling_rights[Color.BLACK]["K"]:
            castling += "k"
        if self.castling_rights[Color.BLACK]["Q"]:
            castling += "q"
        if not castling:
            castling = "-"

        if self.ep_square >= 0:
            from chess_engine.notation import square_name
            ep = square_name(self.ep_square)
        else:
            ep = "-"

        return f"{placement} {turn} {castling} {ep} {self.halfmove_clock} {self.fullmove_number}"

    # --- Basic board access ---

    def piece_at(self, square: int) -> Optional[Piece]:
        """Get the piece at a square index, or None."""
        return self.squares[square]

    def king_square(self, color: Color) -> int:
        """Return the square of the king for the given color."""
        return self._king_squares.get(color, -1)

    def is_empty(self, square: int) -> bool:
        return self.squares[square] is None

    # --- Move generation ---

    def _pseudo_moves(self, color: Color) -> List[Move]:
        """Generate all pseudo-legal moves (may leave king in check)."""
        moves: List[Move] = []
        for sq in range(64):
            p = self.squares[sq]
            if p is None or p.color != color:
                continue
            pt = p.piece_type
            if pt == Piece.PAWN:
                self._gen_pawn_moves(sq, p.color, moves)
            elif pt == Piece.KNIGHT:
                self._gen_knight_moves(sq, p.color, moves)
            elif pt == Piece.BISHOP:
                self._gen_slider_moves(sq, p.color, BISHOP_DIRS, moves)
            elif pt == Piece.ROOK:
                self._gen_slider_moves(sq, p.color, ROOK_DIRS, moves)
            elif pt == Piece.QUEEN:
                self._gen_slider_moves(sq, p.color, QUEEN_DIRS, moves)
            elif pt == Piece.KING:
                self._gen_king_moves(sq, p.color, moves)
        return moves

    def _gen_pawn_moves(self, sq: int, color: Color, moves: List[Move]) -> None:
        file = sq % 8
        rank = sq // 8
        direction = 1 if color == Color.WHITE else -1
        start_rank = 1 if color == Color.WHITE else 6
        promo_rank = 7 if color == Color.WHITE else 0

        # Single push
        new_rank = rank + direction
        if 0 <= new_rank <= 7:
            target = new_rank * 8 + file
            if self.squares[target] is None:
                if new_rank == promo_rank:
                    for promo_type in [Piece.QUEEN, Piece.ROOK,
                                       Piece.BISHOP, Piece.KNIGHT]:
                        moves.append(Move(sq, target,
                                          promotion=Piece(promo_type, color)))
                else:
                    moves.append(Move(sq, target))
                # Double push
                if rank == start_rank:
                    target2 = (rank + 2 * direction) * 8 + file
                    if self.squares[target2] is None:
                        moves.append(Move(sq, target2))

        # Captures
        for df in [-1, 1]:
            new_file = file + df
            new_rank = rank + direction
            if 0 <= new_file <= 7 and 0 <= new_rank <= 7:
                target = new_rank * 8 + new_file
                target_piece = self.squares[target]
                if target_piece is not None and target_piece.color != color:
                    if new_rank == promo_rank:
                        for promo_type in [Piece.QUEEN, Piece.ROOK,
                                           Piece.BISHOP, Piece.KNIGHT]:
                            moves.append(Move(sq, target,
                                              promotion=Piece(promo_type, color)))
                    else:
                        moves.append(Move(sq, target))
                # En passant
                elif target == self.ep_square and self.ep_square >= 0:
                    moves.append(Move(sq, target, is_en_passant=True))

    def _gen_knight_moves(self, sq: int, color: Color, moves: List[Move]) -> None:
        file = sq % 8
        rank = sq // 8
        for df, dr in KNIGHT_OFFSETS:
            nf, nr = file + df, rank + dr
            if _on_board(nf, nr):
                target = nr * 8 + nf
                tp = self.squares[target]
                if tp is None or tp.color != color:
                    moves.append(Move(sq, target))

    def _gen_slider_moves(self, sq: int, color: Color,
                          dirs: list, moves: List[Move]) -> None:
        file = sq % 8
        rank = sq // 8
        for df, dr in dirs:
            nf, nr = file + df, rank + dr
            while _on_board(nf, nr):
                target = nr * 8 + nf
                tp = self.squares[target]
                if tp is None:
                    moves.append(Move(sq, target))
                else:
                    if tp.color != color:
                        moves.append(Move(sq, target))
                    break
                nf += df
                nr += dr

    def _gen_king_moves(self, sq: int, color: Color, moves: List[Move]) -> None:
        file = sq % 8
        rank = sq // 8
        for df, dr in KING_OFFSETS:
            nf, nr = file + df, rank + dr
            if _on_board(nf, nr):
                target = nr * 8 + nf
                tp = self.squares[target]
                if tp is None or tp.color != color:
                    moves.append(Move(sq, target))
        # Castling
        self._gen_castle_moves(sq, color, moves)

    def _gen_castle_moves(self, sq: int, color: Color,
                          moves: List[Move]) -> None:
        rank = 0 if color == Color.WHITE else 7
        if sq != rank * 8 + 4:  # King must be on e1/e8
            return
        opp = color.opposite

        # Kingside: squares f and g must be empty, rook on h
        if self.castling_rights[color]["K"]:
            rook_sq = rank * 8 + 7
            if (self.squares[rook_sq] is not None
                    and self.squares[rook_sq].piece_type == Piece.ROOK
                    and self.squares[rook_sq].color == color):
                f_sq = rank * 8 + 5
                g_sq = rank * 8 + 6
                if (self.squares[f_sq] is None
                        and self.squares[g_sq] is None):
                    # King must not pass through attacked squares
                    if (not self._is_attacked(sq, opp)
                            and not self._is_attacked(f_sq, opp)
                            and not self._is_attacked(g_sq, opp)):
                        moves.append(Move(sq, g_sq, is_castle=True))

        # Queenside: squares b, c, d must be empty, rook on a
        if self.castling_rights[color]["Q"]:
            rook_sq = rank * 8 + 0
            if (self.squares[rook_sq] is not None
                    and self.squares[rook_sq].piece_type == Piece.ROOK
                    and self.squares[rook_sq].color == color):
                b_sq = rank * 8 + 1
                c_sq = rank * 8 + 2
                d_sq = rank * 8 + 3
                if (self.squares[b_sq] is None
                        and self.squares[c_sq] is None
                        and self.squares[d_sq] is None):
                    if (not self._is_attacked(sq, opp)
                            and not self._is_attacked(d_sq, opp)
                            and not self._is_attacked(c_sq, opp)):
                        moves.append(Move(sq, c_sq, is_castle=True))

    def _is_attacked(self, square: int, by_color: Color) -> bool:
        """Check if a square is attacked by any piece of by_color."""
        file = square % 8
        rank = square // 8

        # Pawn attacks: a pawn of by_color attacks this square if it's
        # one rank "behind" and one file to the side
        pawn_dir = 1 if by_color == Color.WHITE else -1
        for df in [-1, 1]:
            af, ar = file + df, rank - pawn_dir
            if _on_board(af, ar):
                p = self.squares[ar * 8 + af]
                if (p is not None and p.color == by_color
                        and p.piece_type == Piece.PAWN):
                    return True

        # Knight attacks
        for df, dr in KNIGHT_OFFSETS:
            nf, nr = file + df, rank + dr
            if _on_board(nf, nr):
                p = self.squares[nr * 8 + nf]
                if (p is not None and p.color == by_color
                        and p.piece_type == Piece.KNIGHT):
                    return True

        # King attacks
        for df, dr in KING_OFFSETS:
            nf, nr = file + df, rank + dr
            if _on_board(nf, nr):
                p = self.squares[nr * 8 + nf]
                if (p is not None and p.color == by_color
                        and p.piece_type == Piece.KING):
                    return True

        # Bishop/Queen diagonal attacks
        for df, dr in BISHOP_DIRS:
            nf, nr = file + df, rank + dr
            while _on_board(nf, nr):
                p = self.squares[nr * 8 + nf]
                if p is not None:
                    if (p.color == by_color
                            and p.piece_type in (Piece.BISHOP, Piece.QUEEN)):
                        return True
                    break
                nf += df
                nr += dr

        # Rook/Queen straight attacks
        for df, dr in ROOK_DIRS:
            nf, nr = file + df, rank + dr
            while _on_board(nf, nr):
                p = self.squares[nr * 8 + nf]
                if p is not None:
                    if (p.color == by_color
                            and p.piece_type in (Piece.ROOK, Piece.QUEEN)):
                        return True
                    break
                nf += df
                nr += dr

        return False

    def is_in_check(self, color: Optional[Color] = None) -> bool:
        """Check if the king of the given color is in check."""
        if color is None:
            color = self.turn
        ksq = self.king_square(color)
        if ksq < 0:
            return False
        return self._is_attacked(ksq, color.opposite)

    def is_check(self) -> bool:
        """Check if the side to move is in check."""
        return self.is_in_check(self.turn)

    def legal_moves(self) -> List[Move]:
        """Generate all fully legal moves."""
        pseudo = self._pseudo_moves(self.turn)
        legal: List[Move] = []
        for move in pseudo:
            self.push(move)
            # After push, turn has flipped. The side that just moved must
            # not be in check.
            mover = self.turn.opposite  # the side that moved
            if not self.is_in_check(mover):
                legal.append(move)
            self.pop()
        return legal

    # --- Make / unmake move ---

    def push(self, move: Move) -> None:
        """Execute a move and save state for undo."""
        # Save state for undo
        state = {
            "move": move,
            "captured": self.squares[move.to_square],
            "castling": {
                Color.WHITE: dict(self.castling_rights[Color.WHITE]),
                Color.BLACK: dict(self.castling_rights[Color.BLACK]),
            },
            "ep_square": self.ep_square,
            "halfmove_clock": self.halfmove_clock,
            "fullmove_number": self.fullmove_number,
            "king_squares": dict(self._king_squares),
            "ep_captured_piece": None,
            "ep_captured_square": -1,
        }

        piece = self.squares[move.from_square]
        assert piece is not None, f"No piece at {move.from_square}"
        is_pawn = piece.piece_type == Piece.PAWN
        is_capture = self.squares[move.to_square] is not None

        # En passant capture
        if move.is_en_passant:
            cap_sq = move.to_square + (-8 if piece.color == Color.WHITE else 8)
            state["ep_captured_piece"] = self.squares[cap_sq]
            state["ep_captured_square"] = cap_sq
            self.squares[cap_sq] = None

        # Move the piece
        self.squares[move.to_square] = piece
        self.squares[move.from_square] = None

        # Handle promotion
        if move.promotion:
            self.squares[move.to_square] = move.promotion

        # Handle castling rook move
        if move.is_castle:
            rank = move.to_square // 8
            if move.to_square % 8 == 6:  # kingside
                rook_from = rank * 8 + 7
                rook_to = rank * 8 + 5
            else:  # queenside (to file 2)
                rook_from = rank * 8 + 0
                rook_to = rank * 8 + 3
            self.squares[rook_to] = self.squares[rook_from]
            self.squares[rook_from] = None

        # Update king square
        if piece.piece_type == Piece.KING:
            self._king_squares[piece.color] = move.to_square

        # Update castling rights
        # If king moved, lose both rights
        if piece.piece_type == Piece.KING:
            self.castling_rights[piece.color]["K"] = False
            self.castling_rights[piece.color]["Q"] = False
        # If a rook moved from its home square, lose that right
        if piece.piece_type == Piece.ROOK:
            if move.from_square == 0:  # a1
                self.castling_rights[Color.WHITE]["Q"] = False
            elif move.from_square == 7:  # h1
                self.castling_rights[Color.WHITE]["K"] = False
            elif move.from_square == 56:  # a8
                self.castling_rights[Color.BLACK]["Q"] = False
            elif move.from_square == 63:  # h8
                self.castling_rights[Color.BLACK]["K"] = False
        # If a rook was captured on its home square, lose that right
        if state["captured"] is not None and state["captured"].piece_type == Piece.ROOK:
            if move.to_square == 0:
                self.castling_rights[Color.WHITE]["Q"] = False
            elif move.to_square == 7:
                self.castling_rights[Color.WHITE]["K"] = False
            elif move.to_square == 56:
                self.castling_rights[Color.BLACK]["Q"] = False
            elif move.to_square == 63:
                self.castling_rights[Color.BLACK]["K"] = False

        # Update en passant square
        if is_pawn and abs(move.to_square - move.from_square) == 16:
            self.ep_square = (move.from_square + move.to_square) // 2
        else:
            self.ep_square = -1

        # Update clocks
        if is_pawn or is_capture:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if self.turn == Color.BLACK:
            self.fullmove_number += 1

        # Switch turn
        self.turn = self.turn.opposite
        self.history.append(state)

    def pop(self) -> dict:
        """Undo the last move, restoring previous state."""
        if not self.history:
            raise IndexError("No moves to undo")
        state = self.history.pop()

        move: Move = state["move"]
        self.turn = self.turn.opposite  # switch back

        piece = self.squares[move.to_square]
        # Undo promotion: restore pawn
        if move.promotion and piece is not None:
            piece = Piece(Piece.PAWN, piece.color)

        # Move piece back
        self.squares[move.from_square] = piece
        self.squares[move.to_square] = state["captured"]

        # Undo castling rook
        if move.is_castle:
            rank = move.to_square // 8
            if move.to_square % 8 == 6:
                rook_from = rank * 8 + 7
                rook_to = rank * 8 + 5
            else:
                rook_from = rank * 8 + 0
                rook_to = rank * 8 + 3
            self.squares[rook_from] = self.squares[rook_to]
            self.squares[rook_to] = None

        # Undo en passant capture
        if move.is_en_passant:
            self.squares[move.to_square] = None  # ep target was empty
            self.squares[state["ep_captured_square"]] = state["ep_captured_piece"]

        # Restore state
        self.castling_rights = state["castling"]
        self.ep_square = state["ep_square"]
        self.halfmove_clock = state["halfmove_clock"]
        self.fullmove_number = state["fullmove_number"]
        self._king_squares = state["king_squares"]

        return state

    # --- Game state queries ---

    def is_checkmate(self) -> bool:
        return self.is_check() and len(self.legal_moves()) == 0

    def is_stalemate(self) -> bool:
        return not self.is_check() and len(self.legal_moves()) == 0

    def is_insufficient_material(self) -> bool:
        """Check for insufficient material draws."""
        pieces = [p for p in self.squares if p is not None]
        non_kings = [p for p in pieces if p.piece_type != Piece.KING]
        if len(non_kings) == 0:
            return True  # K vs K
        if len(non_kings) == 1:
            # K+minor vs K
            return non_kings[0].piece_type in (Piece.BISHOP, Piece.KNIGHT)
        # K+B vs K+B with bishops on same color (simplified)
        if len(non_kings) == 2:
            bishops = [p for p in non_kings if p.piece_type == Piece.BISHOP]
            if len(bishops) == 2:
                # Check if both bishops are on same color square
                sqs = [i for i, p in enumerate(self.squares)
                       if p and p.piece_type == Piece.BISHOP]
                if len(sqs) == 2:
                    c1 = (sqs[0] // 8 + sqs[0] % 8) % 2
                    c2 = (sqs[1] // 8 + sqs[1] % 8) % 2
                    if c1 == c2:
                        return True
        return False

    def is_fifty_move(self) -> bool:
        return self.halfmove_clock >= 100

    def is_game_over(self) -> bool:
        return (self.is_checkmate() or self.is_stalemate()
                or self.is_insufficient_material() or self.is_fifty_move())

    def result(self) -> str:
        """Return game result: '1-0', '0-1', '1/2-1/2', or '*' (ongoing)."""
        if self.is_checkmate():
            # The side to move is checkmated; the other side wins
            return "0-1" if self.turn == Color.WHITE else "1-0"
        if self.is_stalemate() or self.is_insufficient_material() or self.is_fifty_move():
            return "1/2-1/2"
        return "*"

    # --- Display ---

    def to_string(self, unicode: bool = False) -> str:
        """Return an ASCII board representation."""
        lines = []
        for rank in range(7, -1, -1):
            row = f"{rank + 1} "
            for file in range(8):
                sq = rank * 8 + file
                p = self.squares[sq]
                if p is None:
                    row += ". "
                elif unicode:
                    row += p.unicode() + " "
                else:
                    row += p.symbol() + " "
            lines.append(row)
        lines.append("  a b c d e f g h")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.to_string(unicode=True)

    def __repr__(self) -> str:
        return f"Board('{self.fen()}')"

    def copy(self) -> "Board":
        """Create a deep copy of the board."""
        new = Board.from_fen(self.fen())
        new.history = copy.deepcopy(self.history)
        return new


def _char_to_piece(ch: str) -> Optional[Piece]:
    """Convert a FEN character to a Piece object."""
    color = Color.WHITE if ch.isupper() else Color.BLACK
    lower = ch.lower()
    types = {
        "p": Piece.PAWN, "n": Piece.KNIGHT, "b": Piece.BISHOP,
        "r": Piece.ROOK, "q": Piece.QUEEN, "k": Piece.KING,
    }
    pt = types.get(lower)
    if pt is None:
        return None
    return Piece(pt, color)