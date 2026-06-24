"""Position evaluation for the chess engine.

Evaluates a chess position using material and piece-square tables (PST).
A positive score means White is better; negative means Black is better.
"""

from __future__ import annotations

from .board import Board, Piece, Color


# Piece-square tables (from white's perspective, index 0 = a1, 63 = h8)
# Values are in centipawns. Positive = good for that piece type.

PAWN_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10,-20,-20, 10, 10,  5,
     5, -5,-10,  0,  0,-10, -5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5,  5, 10, 25, 25, 10,  5,  5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
     0,  0,  0,  0,  0,  0,  0,  0,
]

KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

ROOK_PST = [
     0,  0,  0,  5,  5,  0,  0,  0,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     5, 10, 10, 10, 10, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

QUEEN_PST = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -10,  5,  5,  5,  5,  5,  0,-10,
      0,  0,  5,  5,  5,  5,  0, -5,
     -5,  0,  5,  5,  5,  5,  0, -5,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

KING_PST_MIDGAME = [
     20, 30, 10,  0,  0, 10, 30, 20,
     20, 20,  0,  0,  0,  0, 20, 20,
    -10,-20,-20,-20,-20,-20,-20,-10,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
]

KING_PST_ENDGAME = [
    -50,-30,-30,-30,-30,-30,-30,-50,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

PST_MAP = {
    Piece.PAWN: PAWN_PST,
    Piece.KNIGHT: KNIGHT_PST,
    Piece.BISHOP: BISHOP_PST,
    Piece.ROOK: ROOK_PST,
    Piece.QUEEN: QUEEN_PST,
}


def _mirror_square(sq: int) -> int:
    """Mirror a square vertically for black's perspective."""
    rank = sq // 8
    file = sq % 8
    return (7 - rank) * 8 + file


class Evaluator:
    """Position evaluator combining material and piece-square tables.

    Supports a simple game phase detection (midgame vs endgame) based on
    total non-pawn material, and uses different king tables accordingly.
    """

    TEMPO_BONUS = 10

    def __init__(self) -> None:
        self.nodes_evaluated = 0

    def is_endgame(self, board: Board) -> bool:
        """Detect endgame: no queens, or each side has <= 1 minor piece
        besides queens with very little material."""
        total_material = 0
        for p in board.squares:
            if p is None or p.piece_type == Piece.KING or p.piece_type == Piece.PAWN:
                continue
            if p.piece_type == Piece.QUEEN:
                total_material += 900
            elif p.piece_type == Piece.ROOK:
                total_material += 500
            else:
                total_material += 320
        # Endgame threshold: less than a queen + rook worth of non-pawn material
        return total_material < 1300

    def evaluate(self, board: Board) -> int:
        """Evaluate the position from the perspective of the side to move.

        Returns a positive score if the side to move is winning.
        """
        self.nodes_evaluated += 1
        score = self._evaluate_absolute(board)
        # Return from perspective of side to move
        return score if board.turn == Color.WHITE else -score

    def _evaluate_absolute(self, board: Board) -> int:
        """Evaluate from White's perspective (positive = White better)."""
        if board.is_checkmate():
            # Side to move is checkmated
            return -100000 if board.turn == Color.WHITE else 100000
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        endgame = self.is_endgame(board)
        score = 0
        for sq in range(64):
            p = board.squares[sq]
            if p is None:
                continue
            material = p.value
            if p.piece_type == Piece.KING:
                pst = KING_PST_ENDGAME if endgame else KING_PST_MIDGAME
            else:
                pst = PST_MAP.get(p.piece_type, [0] * 64)

            if p.color == Color.WHITE:
                positional = pst[sq]
                score += material + positional
            else:
                positional = pst[_mirror_square(sq)]
                score -= material + positional

        # Tempo bonus
        score += self.TEMPO_BONUS if board.turn == Color.WHITE else -self.TEMPO_BONUS

        return score