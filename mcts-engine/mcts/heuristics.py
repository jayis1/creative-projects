"""
Heuristic evaluation functions for MCTS games.

These can be used with progressive bias or custom rollout policies
to improve search quality.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .core import GameMove, GameState, Player
from .games import Connect4, Gomoku, Hex, Reversi, TicTacToe


def tictactoe_heuristic(state: GameState) -> float:
    """Evaluate a TicTacToe position.

    Returns a value in [0, 1] for the current player.
    Uses a simple threat count: lines where the player has 2 pieces
    and the opponent has none.
    """
    if not isinstance(state, TicTacToe):
        return 0.5
    if state.is_terminal():
        return state.reward(state.current_player())

    player = state.current_player()
    opponent = player.opponent
    board = state.board

    # All winning lines
    lines = [
        [(0, 0), (0, 1), (0, 2)],  # rows
        [(1, 0), (1, 1), (1, 2)],
        [(2, 0), (2, 1), (2, 2)],
        [(0, 0), (1, 0), (2, 0)],  # cols
        [(0, 1), (1, 1), (2, 1)],
        [(0, 2), (1, 2), (2, 2)],
        [(0, 0), (1, 1), (2, 2)],  # diagonals
        [(0, 2), (1, 1), (2, 0)],
    ]

    my_threats = 0
    opp_threats = 0
    for line in lines:
        my_count = sum(1 for r, c in line if board[r][c] == player)
        opp_count = sum(1 for r, c in line if board[r][c] == opponent)
        if opp_count == 0 and my_count == 2:
            my_threats += 1
        if my_count == 0 and opp_count == 2:
            opp_threats += 1

    # Center bonus
    center_bonus = 0.1 if board[1][1] == player else 0.0

    # Normalize to [0, 1]
    score = 0.5 + 0.15 * (my_threats - opp_threats) + center_bonus
    return max(0.0, min(1.0, score))


def connect4_heuristic(state: GameState) -> float:
    """Evaluate a Connect4 position.

    Counts threats (3-in-a-row with open cell) and center column preference.
    """
    if not isinstance(state, Connect4):
        return 0.5
    if state.is_terminal():
        return state.reward(state.current_player())

    player = state.current_player()
    opponent = player.opponent
    board = state.board
    rows, cols = state.rows, state.cols

    def count_windows(length: int) -> Tuple[int, int]:
        """Count windows of `length` consecutive cells for each player."""
        my_count = 0
        opp_count = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for r in range(rows):
            for c in range(cols):
                for dr, dc in directions:
                    cells = []
                    valid = True
                    for i in range(length):
                        nr, nc = r + i * dr, c + i * dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            cells.append(board[nr][nc])
                        else:
                            valid = False
                            break
                    if valid:
                        my = sum(1 for x in cells if x == player)
                        opp = sum(1 for x in cells if x == opponent)
                        empty = sum(1 for x in cells if x == Player.NONE)
                        if opp == 0 and my == length - 1 and empty == 1:
                            my_count += 1
                        if my == 0 and opp == length - 1 and empty == 1:
                            opp_count += 1
        return my_count, opp_count

    my_3, opp_3 = count_windows(4)
    # Center column preference
    center_col = cols // 2
    my_center = sum(1 for r in range(rows) if board[r][center_col] == player)
    opp_center = sum(1 for r in range(rows) if board[r][center_col] == opponent)

    score = 0.5 + 0.08 * (my_3 - opp_3) + 0.02 * (my_center - opp_center)
    return max(0.0, min(1.0, score))


def reversi_heuristic(state: GameState) -> float:
    """Evaluate a Reversi/Othello position.

    Uses corner ownership, mobility, and piece count (phase-dependent).
    """
    if not isinstance(state, Reversi):
        return 0.5
    if state.is_terminal():
        return state.reward(state.current_player())

    player = state.current_player()
    opponent = player.opponent
    board = state.board
    size = state.rows

    # Corner values
    corners = [(0, 0), (0, size - 1), (size - 1, 0), (size - 1, size - 1)]
    my_corners = sum(1 for r, c in corners if board[r][c] == player)
    opp_corners = sum(1 for r, c in corners if board[r][c] == opponent)

    # Mobility
    my_moves = len(state.legal_moves())
    # Temporarily compute opponent mobility
    opp_moves = 0
    for r in range(size):
        for c in range(size):
            if state._get_flips(r, c, opponent):
                opp_moves += 1

    # Piece count
    my_pieces = sum(1 for r in range(size) for c in range(size) if board[r][c] == player)
    opp_pieces = sum(1 for r in range(size) for c in range(size) if board[r][c] == opponent)
    total = my_pieces + opp_pieces

    # Phase-dependent weights
    if total < 40:
        # Early game: mobility and corners matter most
        score = 0.5 + 0.1 * (my_corners - opp_corners) + 0.05 * (my_moves - opp_moves)
    else:
        # Late game: piece count matters
        score = 0.5 + 0.1 * (my_corners - opp_corners) + 0.02 * (my_pieces - opp_pieces)
    return max(0.0, min(1.0, score))


def hex_heuristic(state: GameState) -> float:
    """Evaluate a Hex position using shortest-path heuristic.

    Estimates how close each player is to connecting their sides by
    computing the shortest path through empty+own cells.
    """
    if not isinstance(state, Hex):
        return 0.5
    if state.is_terminal():
        return state.reward(state.current_player())

    player = state.current_player()
    opponent = player.opponent
    board = state.board
    size = state.rows
    INF = float("inf")

    # For Player ONE: shortest path from top to bottom through own/empty cells
    # For Player TWO: shortest path from left to right through own/empty cells

    def shortest_path(p: Player) -> float:
        """Compute shortest path cost for player p.

        Own cells cost 0, empty cells cost 1, opponent cells are impassable.
        Returns path cost (lower is better for that player).
        """
        from collections import deque
        dist = [[INF] * size for _ in range(size)]
        queue = deque()

        if p == Player.ONE:
            # Start from top row
            for c in range(size):
                if board[0][c] != opponent:
                    cost = 0 if board[0][c] == p else 1
                    dist[0][c] = cost
                    queue.append((cost, 0, c))
        else:
            # Start from left column
            for r in range(size):
                if board[r][0] != opponent:
                    cost = 0 if board[r][0] == p else 1
                    dist[r][0] = cost
                    queue.append((cost, r, 0))

        neighbors = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)]
        # Dijkstra (0-1 BFS with deque)
        while queue:
            d, r, c = queue.popleft()
            if d > dist[r][c]:
                continue
            for dr, dc in neighbors:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and board[nr][nc] != opponent:
                    cost = 0 if board[nr][nc] == p else 1
                    nd = d + cost
                    if nd < dist[nr][nc]:
                        dist[nr][nc] = nd
                        if cost == 0:
                            queue.appendleft((nd, nr, nc))
                        else:
                            queue.append((nd, nr, nc))

        # Find minimum distance to the goal side
        if p == Player.ONE:
            return min(dist[size - 1][c] for c in range(size))
        else:
            return min(dist[r][size - 1] for r in range(size))

    my_dist = shortest_path(player)
    opp_dist = shortest_path(opponent)

    if my_dist == INF:
        return 0.0  # impossible to connect
    if opp_dist == INF:
        return 1.0  # opponent can't connect

    # Lower distance is better; convert to [0, 1]
    total = my_dist + opp_dist
    if total == 0:
        return 0.5
    return opp_dist / total


def gomoku_heuristic(state: GameState) -> float:
    """Evaluate a Gomoku position using pattern matching.

    Counts open threes, fours, and other patterns.
    """
    if not isinstance(state, Gomoku):
        return 0.5
    if state.is_terminal():
        return state.reward(state.current_player())

    player = state.current_player()
    opponent = player.opponent
    board = state.board
    size = state.rows

    def count_patterns(length: int, open_ends_needed: int) -> Tuple[int, int]:
        """Count patterns of given length with specified open ends."""
        my_count = 0
        opp_count = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for r in range(size):
            for c in range(size):
                for dr, dc in directions:
                    # Check if a run of `length` starts here
                    cells = []
                    valid = True
                    for i in range(length):
                        nr, nc = r + i * dr, c + i * dc
                        if 0 <= nr < size and 0 <= nc < size:
                            cells.append(board[nr][nc])
                        else:
                            valid = False
                            break
                    if not valid:
                        continue
                    my = sum(1 for x in cells if x == player)
                    opp = sum(1 for x in cells if x == opponent)
                    empty = sum(1 for x in cells if x == Player.NONE)
                    if my == length and empty == 0:
                        my_count += 1
                    if opp == length and empty == 0:
                        opp_count += 1
        return my_count, opp_count

    my_4, opp_4 = count_patterns(4, 1)
    my_3, opp_3 = count_patterns(3, 2)
    my_2, opp_2 = count_patterns(2, 2)

    score = 0.5 + 0.2 * (my_4 - opp_4) + 0.1 * (my_3 - opp_3) + 0.03 * (my_2 - opp_2)
    return max(0.0, min(1.0, score))


# Registry of heuristic functions by game name
HEURISTICS = {
    "tictactoe": tictactoe_heuristic,
    "connect4": connect4_heuristic,
    "gomoku": gomoku_heuristic,
    "reversi": reversi_heuristic,
    "hex": hex_heuristic,
}


def get_heuristic(game_name: str):
    """Get the heuristic function for a game by name.

    Returns None if no heuristic is available for the game.
    """
    return HEURISTICS.get(game_name.lower())


def make_rollout_policy(heuristic_fn, epsilon: float = 0.1):
    """Create a rollout policy that uses a heuristic with epsilon-greedy selection.

    With probability epsilon, picks a random move.
    With probability 1-epsilon, picks the move with the best heuristic value.

    Args:
        heuristic_fn: Function taking a GameState and returning [0, 1].
        epsilon: Probability of random move.

    Returns:
        A RolloutPolicy function.
    """
    import random as _random

    def policy(state: GameState, rng: _random.Random) -> Optional[GameMove]:
        if rng.random() < epsilon:
            return None  # fall back to random
        legal = state.legal_moves()
        if not legal:
            return None
        # Evaluate each move
        best_move = None
        best_score = -1.0
        for move in legal:
            try:
                child = state.apply(move)
                score = heuristic_fn(child)
                # We want the move that's best for the current player
                # The heuristic evaluates from the perspective of the player
                # at the child state, which is the opponent, so flip
                score = 1.0 - score
                if score > best_score:
                    best_score = score
                    best_move = move
            except Exception:
                continue
        return best_move

    return policy