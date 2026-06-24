"""Algebraic notation conversion utilities."""

from .board import Board, Move, Piece, Color, Square, FILE_NAMES, RANK_NAMES


def square_name(sq: int) -> str:
    """Convert a square index (0..63) to algebraic name like 'e4'."""
    if not 0 <= sq <= 63:
        raise ValueError(f"Invalid square index: {sq}")
    f = sq % 8
    r = sq // 8
    return f"{FILE_NAMES[f]}{RANK_NAMES[r]}"


def parse_square(name: str) -> int:
    """Parse algebraic square name like 'e4' into index 0..63."""
    name = name.strip().lower()
    if len(name) != 2:
        raise ValueError(f"Invalid square name: {name!r}")
    f = name[0]
    r = name[1]
    if f not in FILE_NAMES or r not in RANK_NAMES:
        raise ValueError(f"Invalid square name: {name!r}")
    return RANK_NAMES.index(r) * 8 + FILE_NAMES.index(f)


def to_algebraic(move: Move, board: Board) -> str:
    """Convert a Move to Standard Algebraic Notation (SAN).

    Handles castling, captures, disambiguation, promotion, check/mate.
    """
    if move.is_castle:
        if move.to_square % 8 == 6:  # kingside
            san = "O-O"
        else:  # queenside (to file 2)
            san = "O-O-O"
    else:
        piece = board.piece_at(move.from_square)
        if piece is None:
            return "??"
        ptype = piece.piece_type
        is_capture = board.piece_at(move.to_square) is not None or move.is_en_passant

        if ptype == Piece.PAWN:
            if is_capture:
                san = FILE_NAMES[move.from_square % 8] + "x"
            else:
                san = ""
            san += square_name(move.to_square)
            if move.promotion:
                san += "=" + move.promotion.symbol()
        else:
            san = piece.symbol().upper()
            # Disambiguation
            others = []
            for m in board.legal_moves():
                if m.to_square == move.to_square and m.from_square != move.from_square:
                    p = board.piece_at(m.from_square)
                    if p and p.piece_type == ptype and p.color == piece.color:
                        others.append(m)
            if others:
                same_file = any(
                    m.from_square % 8 == move.from_square % 8 for m in others
                )
                same_rank = any(
                    m.from_square // 8 == move.from_square // 8 for m in others
                )
                if not same_file:
                    san += FILE_NAMES[move.from_square % 8]
                elif not same_rank:
                    san += RANK_NAMES[move.from_square // 8]
                else:
                    san += square_name(move.from_square)
            if is_capture:
                san += "x"
            san += square_name(move.to_square)

    # Check / checkmate suffix
    board.push(move)
    if board.is_checkmate():
        san += "#"
    elif board.is_check():
        san += "+"
    board.pop()

    return san


def parse_algebraic(san: str, board: Board) -> Move:
    """Parse a SAN string into a Move given the current board position.

    This does a reverse lookup: generate all legal moves and find the one
    whose SAN matches. This is robust but O(n) per call.
    """
    san = san.strip()
    # Strip check/mate annotations
    san_clean = san.rstrip("+#")

    for move in board.legal_moves():
        if to_algebraic(move, board).rstrip("+#") == san_clean:
            return move
    raise ValueError(f"Illegal or unparseable move: {san!r}")