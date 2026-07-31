"""
Game implementations for the MCTS engine.

All games implement the GameState interface. Each is a two-player
zero-sum game with perfect information.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .core import GameMove, GameState, Player


class GridGame(GameState, ABC):
    """Base class for grid-based games (simplifies common operations)."""

    def __init__(self, rows: int, cols: int, board: Optional[List[List[Player]]] = None) -> None:
        self.rows = rows
        self.cols = cols
        if board is not None:
            self.board = board
        else:
            self.board = [[Player.NONE for _ in range(cols)] for _ in range(rows)]
        self._current: Player = Player.ONE
        self._winner: Player = Player.NONE
        self._terminal: bool = False
        self._move_count: int = 0

    def current_player(self) -> Player:
        return self._current if not self._terminal else Player.NONE

    def winner(self) -> Player:
        return self._winner

    def is_terminal(self) -> bool:
        return self._terminal

    def _check_in_bounds(self, row: int, col: int) -> None:
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise ValueError(f"Position ({row},{col}) out of bounds for {self.rows}x{self.cols} board")

    def _place_and_switch(self, row: int, col: int, player: Player) -> None:
        """Place a piece and switch turns. Called by subclass apply()."""
        self.board[row][col] = player
        self._move_count += 1
        self._current = self._current.opponent

    def _count_pieces(self) -> int:
        count = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != Player.NONE:
                    count += 1
        return count

    def display(self) -> str:
        lines = []
        # Column header
        header = "   " + " ".join(f"{i:2d}" for i in range(self.cols))
        lines.append(header)
        for r in range(self.rows):
            row_str = f"{r:2d} " + " ".join(f" {str(self.board[r][c])}" for c in range(self.cols))
            lines.append(row_str)
        return "\n".join(lines)

    def hash_key(self) -> str:
        parts = []
        for r in range(self.rows):
            for c in range(self.cols):
                parts.append(str(self.board[r][c].value))
        return f"{self.__class__.__name__}:{''.join(parts)}:{self._current.value}"

    @abstractmethod
    def _check_winner(self, last_row: int, last_col: int) -> Player:
        """Check if the last move at (last_row, last_col) created a win."""
        ...

    def reward(self, player: Player) -> float:
        if not self._terminal:
            return 0.0
        if self._winner == player:
            return 1.0
        if self._winner == Player.NONE:
            return 0.5
        return 0.0

    def legal_moves(self) -> List[GameMove]:
        if self._terminal:
            return []
        moves: List[GameMove] = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self._is_legal(r, c):
                    moves.append(GameMove(r, c))
        return moves

    @abstractmethod
    def _is_legal(self, row: int, col: int) -> bool:
        """Check if placing at (row, col) is legal (cell is playable)."""
        ...

    def apply(self, move: GameMove) -> "GridGame":
        new_board = [row[:] for row in self.board]
        new_state = self.__class__.__new__(self.__class__)
        new_state.rows = self.rows
        new_state.cols = self.cols
        new_state.board = new_board
        new_state._current = self._current
        new_state._winner = Player.NONE
        new_state._terminal = False
        new_state._move_count = self._move_count
        new_state._apply_move(move.row, move.col)
        return new_state

    def _apply_move(self, row: int, col: int) -> None:
        """Apply a move in-place on a fresh copy. Override for complex games."""
        self._check_in_bounds(row, col)
        if not self._is_legal(row, col):
            raise ValueError(f"Illegal move at ({row},{col})")
        player = self._current
        self._place_and_switch(row, col, player)
        winner = self._check_winner(row, col)
        if winner != Player.NONE:
            self._winner = winner
            self._terminal = True
        elif self._move_count >= self.rows * self.cols:
            self._terminal = True


class TicTacToe(GridGame):
    """3×3 Tic-Tac-Toe. Get 3 in a row (horizontal, vertical, or diagonal)."""

    def __init__(self, board: Optional[List[List[Player]]] = None) -> None:
        super().__init__(3, 3, board)

    def _is_legal(self, row: int, col: int) -> bool:
        return self.board[row][col] == Player.NONE

    def _check_winner(self, last_row: int, last_col: int) -> Player:
        player = self.board[last_row][last_col]
        if player == Player.NONE:
            return Player.NONE
        # Check row
        if all(self.board[last_row][c] == player for c in range(3)):
            return player
        # Check column
        if all(self.board[r][last_col] == player for r in range(3)):
            return player
        # Check diagonals
        if last_row == last_col and all(self.board[i][i] == player for i in range(3)):
            return player
        if last_row + last_col == 2 and all(self.board[i][2 - i] == player for i in range(3)):
            return player
        return Player.NONE


class Connect4(GridGame):
    """Connect Four on a 6×7 board. Get 4 in a row.

    Pieces fall to the lowest empty slot in each column.
    """

    def __init__(self, rows: int = 6, cols: int = 7, board: Optional[List[List[Player]]] = None) -> None:
        super().__init__(rows, cols, board)

    def _is_legal(self, row: int, col: int) -> bool:
        # A move is legal if the cell is empty AND it's the lowest empty cell
        # in that column (i.e., the cell below is filled or it's the bottom row).
        if self.board[row][col] != Player.NONE:
            return False
        if row == self.rows - 1:
            return True
        return self.board[row + 1][col] != Player.NONE

    def legal_moves(self) -> List[GameMove]:
        if self._terminal:
            return []
        moves: List[GameMove] = []
        for c in range(self.cols):
            for r in range(self.rows - 1, -1, -1):
                if self.board[r][c] == Player.NONE:
                    moves.append(GameMove(r, c))
                    break
        return moves

    def _check_winner(self, last_row: int, last_col: int) -> Player:
        player = self.board[last_row][last_col]
        if player == Player.NONE:
            return Player.NONE
        # Check all 4 directions
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            # Forward
            r, c = last_row + dr, last_col + dc
            while 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == player:
                count += 1
                r += dr
                c += dc
            # Backward
            r, c = last_row - dr, last_col - dc
            while 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == player:
                count += 1
                r -= dr
                c -= dc
            if count >= 4:
                return player
        return Player.NONE


class Gomoku(GridGame):
    """Gomoku (Five-in-a-Row) on an NxN board. Get 5 in a row to win.

    Default board size is 15×15.
    """

    def __init__(self, size: int = 15, board: Optional[List[List[Player]]] = None) -> None:
        super().__init__(size, size, board)
        self._win_length = 5

    def _is_legal(self, row: int, col: int) -> bool:
        return self.board[row][col] == Player.NONE

    def _check_winner(self, last_row: int, last_col: int) -> Player:
        player = self.board[last_row][last_col]
        if player == Player.NONE:
            return Player.NONE
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            r, c = last_row + dr, last_col + dc
            while 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == player:
                count += 1
                r += dr
                c += dc
            r, c = last_row - dr, last_col - dc
            while 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == player:
                count += 1
                r -= dr
                c -= dc
            if count >= self._win_length:
                return player
        return Player.NONE


class Reversi(GridGame):
    """Reversi/Othello on an 8×8 board.

    Players place pieces to outflank opponent pieces, flipping them.
    Game ends when neither player can move. Most pieces wins.
    """

    def __init__(self, size: int = 8, board: Optional[List[List[Player]]] = None) -> None:
        super().__init__(size, size, board)
        if board is None:
            # Initial Othello setup: 4 pieces in the center
            mid = size // 2
            self.board[mid - 1][mid - 1] = Player.TWO
            self.board[mid - 1][mid] = Player.ONE
            self.board[mid][mid - 1] = Player.ONE
            self.board[mid][mid] = Player.TWO
            self._move_count = 4

    def _get_flips(self, row: int, col: int, player: Player) -> List[tuple]:
        """Get all pieces that would be flipped by placing at (row, col)."""
        if self.board[row][col] != Player.NONE:
            return []
        opponent = player.opponent
        flips: List[tuple] = []
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dr, dc in directions:
            r, c = row + dr, col + dc
            to_flip: List[tuple] = []
            while 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == opponent:
                to_flip.append((r, c))
                r += dr
                c += dc
            if 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == player and to_flip:
                flips.extend(to_flip)
        return flips

    def _is_legal(self, row: int, col: int) -> bool:
        return len(self._get_flips(row, col, self._current)) > 0

    def legal_moves(self) -> List[GameMove]:
        if self._terminal:
            return []
        moves: List[GameMove] = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self._is_legal(r, c):
                    moves.append(GameMove(r, c))
        # If current player has no moves, switch to opponent
        if not moves:
            # Check if opponent has moves
            opp_moves = []
            opp = self._current.opponent
            for r in range(self.rows):
                for c in range(self.cols):
                    if len(self._get_flips(r, c, opp)) > 0:
                        opp_moves.append(GameMove(r, c))
            if not opp_moves:
                # Game over — neither player can move
                pass  # terminal handled in apply
        return moves

    def _apply_move(self, row: int, col: int) -> None:
        self._check_in_bounds(row, col)
        player = self._current
        flips = self._get_flips(row, col, player)
        if not flips:
            raise ValueError(f"Illegal move at ({row},{col}): no flips")
        self.board[row][col] = player
        self._move_count += 1
        for fr, fc in flips:
            self.board[fr][fc] = player
        self._current = self._current.opponent
        # Check if next player has any moves
        next_has_moves = any(
            len(self._get_flips(r, c, self._current)) > 0
            for r in range(self.rows)
            for c in range(self.cols)
        )
        if not next_has_moves:
            # Switch back if opponent can't move
            self._current = self._current.opponent
            curr_has_moves = any(
                len(self._get_flips(r, c, self._current)) > 0
                for r in range(self.rows)
                for c in range(self.cols)
            )
            if not curr_has_moves:
                # Game over
                self._terminal = True
                self._determine_winner()

    def _determine_winner(self) -> None:
        p1 = sum(1 for r in range(self.rows) for c in range(self.cols) if self.board[r][c] == Player.ONE)
        p2 = sum(1 for r in range(self.rows) for c in range(self.cols) if self.board[r][c] == Player.TWO)
        if p1 > p2:
            self._winner = Player.ONE
        elif p2 > p1:
            self._winner = Player.TWO
        else:
            self._winner = Player.NONE

    def _check_winner(self, last_row: int, last_col: int) -> Player:
        # Reversi winner is determined by piece count at game end, not per-move
        return Player.NONE


class Hex(GridGame):
    """Hex game on an NxN board. Connect your two sides to win.

    Player ONE (X) connects top to bottom.
    Player TWO (O) connects left to right.
    Default size is 11×11.
    """

    def __init__(self, size: int = 11, board: Optional[List[List[Player]]] = None) -> None:
        super().__init__(size, size, board)

    def _is_legal(self, row: int, col: int) -> bool:
        return self.board[row][col] == Player.NONE

    def _check_winner(self, last_row: int, last_col: int) -> Player:
        player = self.board[last_row][last_col]
        if player == Player.NONE:
            return Player.NONE
        # Use BFS/DFS to check if player has connected their sides
        if player == Player.ONE:
            # Connect top row to bottom row
            return self._check_connection(player, range(self.rows), lambda r, c: r == 0, lambda r, c: r == self.rows - 1)
        else:
            # Connect left col to right col
            return self._check_connection(player, range(self.cols), lambda r, c: c == 0, lambda r, c: c == self.cols - 1)

    def _check_connection(self, player: Player, rng, is_start, is_end) -> Player:
        """Check if player has connected their two sides via BFS."""
        from collections import deque
        visited = set()
        queue = deque()
        # Find start cells
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == player and is_start(r, c):
                    queue.append((r, c))
                    visited.add((r, c))
        # Hex neighbors (6 directions)
        neighbors = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)]
        while queue:
            r, c = queue.popleft()
            if is_end(r, c):
                return player
            for dr, dc in neighbors:
                nr, nc = r + dr, c + dc
                if (nr, nc) not in visited and 0 <= nr < self.rows and 0 <= nc < self.cols and self.board[nr][nc] == player:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return Player.NONE

    def display(self) -> str:
        """Display with hex offset for visual clarity."""
        lines = []
        header = "    " + " ".join(f"{i:2d}" for i in range(self.cols))
        lines.append(header)
        for r in range(self.rows):
            indent = "  " * r
            row_str = f"{indent}{r:2d} " + " ".join(f" {str(self.board[r][c])}" for c in range(self.cols))
            lines.append(row_str)
        lines.append(f"  Player ONE (X): connect top↔bottom")
        lines.append(f"  Player TWO (O): connect left↔right")
        return "\n".join(lines)