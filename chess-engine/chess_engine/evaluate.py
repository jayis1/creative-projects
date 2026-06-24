"""Position evaluation for the chess engine.

Evaluates a chess position using:
- Material values
- Piece-square tables (PST) with midgame/endgame phase detection
- Pawn structure: doubled, isolated, passed pawns
- Piece mobility
- King safety (pawn shield)

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

# Penalty/bonus values for pawn structure
DOUBLED_PAWN_PENALTY = -15
ISOLATED_PAWN_PENALTY = -20
PASSED_PAWN_BONUS = 20
BACKWARD_PAWN_PENALTY = -10

# Mobility bonus per available move (by piece type)
MOBILITY_BONUS = {
    Piece.KNIGHT: 2,
    Piece.BISHOP: 3,
    Piece.ROOK: 2,
    Piece.QUEEN: 1,
}

# King safety: penalty per missing pawn shield square
KING_SHIELD_PENALTY = -15


def _mirror_square(sq: int) -> int:
    """Mirror a square vertically for black's perspective."""
    rank = sq // 8
    file = sq % 8
    return (7 - rank) * 8 + file


class Evaluator:
    """Position evaluator combining material, PST, pawn structure, mobility,
    and king safety.

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
            return -100000 if board.turn == Color.WHITE else 100000
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        endgame = self.is_endgame(board)
        score = 0

        # Material and PST
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

        # Pawn structure
        score += self._evaluate_pawn_structure(board)

        # Mobility (skip in endgame for speed, it matters less)
        if not endgame:
            score += self._evaluate_mobility(board)

        # King safety (only in midgame)
        if not endgame:
            score += self._evaluate_king_safety(board)

        # Tempo bonus
        score += self.TEMPO_BONUS if board.turn == Color.WHITE else -self.TEMPO_BONUS

        return score

    def _evaluate_pawn_structure(self, board: Board) -> int:
        """Evaluate pawn structure: doubled, isolated, passed, backward pawns."""
        score = 0

        # Build pawn tables for each color
        white_pawns = [False] * 64
        black_pawns = [False] * 64
        for sq in range(64):
            p = board.squares[sq]
            if p and p.piece_type == Piece.PAWN:
                if p.color == Color.WHITE:
                    white_pawns[sq] = True
                else:
                    black_pawns[sq] = True

        # Evaluate white pawns
        score += self._eval_pawns_for_color(white_pawns, black_pawns,
                                             Color.WHITE)
        # Evaluate black pawns (mirror)
        score -= self._eval_pawns_for_color(black_pawns, white_pawns,
                                             Color.BLACK)

        return score

    def _eval_pawns_for_color(self, own_pawns: list,
                              enemy_pawns: list,
                              color: Color) -> int:
        """Evaluate pawn structure for one color."""
        score = 0
        direction = 1 if color == Color.WHITE else -1
        start_rank = 1 if color == Color.WHITE else 6

        # Count pawns per file for doubled pawn detection
        file_counts = [0] * 8
        for sq in range(64):
            if own_pawns[sq]:
                file_counts[sq % 8] += 1

        for sq in range(64):
            if not own_pawns[sq]:
                continue
            file = sq % 8
            rank = sq // 8

            # Doubled pawns
            if file_counts[file] > 1:
                score += DOUBLED_PAWN_PENALTY

            # Isolated pawns (no friendly pawns on adjacent files)
            left_file = file - 1
            right_file = file + 1
            has_left = (left_file >= 0 and
                        any(own_pawns[r * 8 + left_file]
                            for r in range(8)))
            has_right = (right_file <= 7 and
                         any(own_pawns[r * 8 + right_file]
                             for r in range(8)))
            if not has_left and not has_right:
                score += ISOLATED_PAWN_PENALTY

            # Passed pawn (no enemy pawns on same file or adjacent files,
            # ahead of this pawn)
            is_passed = True
            for f in [file - 1, file, file + 1]:
                if f < 0 or f > 7:
                    continue
                r = rank + direction
                while 0 <= r <= 7:
                    if enemy_pawns[r * 8 + f]:
                        is_passed = False
                        break
                    r += direction
            if is_passed:
                # Bonus increases with rank
                rank_bonus = PASSED_PAWN_BONUS
                if color == Color.WHITE:
                    rank_bonus += (rank - 1) * 10
                else:
                    rank_bonus += (6 - rank) * 10
                score += rank_bonus

            # Backward pawn (no friendly pawns behind on adjacent files,
            # but enemy pawn stops its advance)
            behind_rank = rank - direction
            if 0 <= behind_rank <= 7:
                has_behind_left = (left_file >= 0 and
                                   any(own_pawns[r * 8 + left_file]
                                       for r in range(behind_rank, -1, -1)
                                       if 0 <= r <= 7))
                has_behind_right = (right_file <= 7 and
                                    any(own_pawns[r * 8 + right_file]
                                        for r in range(behind_rank, -1, -1)
                                        if 0 <= r <= 7))
                if not has_behind_left and not has_behind_right:
                    # Check if the square in front is blocked by enemy pawn
                    front_sq = (rank + direction) * 8 + file
                    if 0 <= front_sq < 64 and enemy_pawns[front_sq]:
                        score += BACKWARD_PAWN_PENALTY

        return score

    def _evaluate_mobility(self, board: Board) -> int:
        """Evaluate piece mobility (number of legal moves per piece type)."""
        score = 0
        # Count moves for white pieces
        for move in board._pseudo_moves(Color.WHITE):
            p = board.squares[move.from_square]
            if p:
                score += MOBILITY_BONUS.get(p.piece_type, 0)
        # Count moves for black pieces
        for move in board._pseudo_moves(Color.BLACK):
            p = board.squares[move.from_square]
            if p:
                score -= MOBILITY_BONUS.get(p.piece_type, 0)
        return score

    def _evaluate_king_safety(self, board: Board) -> int:
        """Evaluate king safety based on pawn shield."""
        score = 0

        for color in [Color.WHITE, Color.BLACK]:
            ksq = board.king_square(color)
            if ksq < 0:
                continue
            kfile = ksq % 8
            krank = ksq // 8
            direction = 1 if color == Color.WHITE else -1

            # Check pawn shield: the three squares in front of the king
            shield_penalty = 0
            for df in [-1, 0, 1]:
                f = kfile + df
                if 0 <= f <= 7:
                    shield_sq = (krank + direction) * 8 + f
                    if 0 <= shield_sq < 64:
                        p = board.squares[shield_sq]
                        if p is None or p.piece_type != Piece.PAWN or p.color != color:
                            shield_penalty += KING_SHIELD_PENALTY

            if color == Color.WHITE:
                score += shield_penalty
            else:
                score -= shield_penalty

        return score