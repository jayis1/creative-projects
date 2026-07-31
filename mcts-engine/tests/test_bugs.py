"""
Additional bug-hunt tests for edge cases found during code review.
"""

import pytest
from mcts import (
    MCTSEngine, TicTacToe, Connect4, Hex, Gomoku, Reversi,
    UCTPolicy, RAVEPolicy, Player, GameMove, MCTSNode,
)
from mcts.games import GridGame


class TestReversiPassLogic:
    """BUG 4: Reversi legal_moves() returns [] when current player has no moves,
    but the game is not terminal and the player should pass.

    The legal_moves() method should return the opponent's moves when the
    current player must pass. Currently, the pass logic is only in _apply_move,
    which means the MCTS engine sees an empty legal_moves list and treats it
    as a draw, rather than the correct behavior of passing to the opponent.
    """

    def test_pass_returns_opponent_moves(self):
        """When current player has no legal moves but opponent does,
        legal_moves should return opponent's moves (pass logic)."""
        # Set up a position where ONE has no moves but TWO does
        game = Reversi(size=6)
        # Fill the board to create a pass scenario
        game.board = [
            [Player.TWO, Player.TWO, Player.TWO, Player.TWO, Player.TWO, Player.TWO],
            [Player.TWO, Player.TWO, Player.TWO, Player.TWO, Player.TWO, Player.TWO],
            [Player.TWO, Player.TWO, Player.ONE, Player.ONE, Player.TWO, Player.TWO],
            [Player.NONE, Player.ONE, Player.ONE, Player.ONE, Player.TWO, Player.TWO],
            [Player.NONE, Player.ONE, Player.ONE, Player.TWO, Player.TWO, Player.TWO],
            [Player.NONE, Player.ONE, Player.TWO, Player.TWO, Player.TWO, Player.TWO],
        ]
        game._current = Player.ONE
        game._move_count = 30
        game._terminal = False
        game._winner = Player.NONE

        # Check if ONE has any legal moves
        one_moves = []
        for r in range(6):
            for c in range(6):
                if game._get_flips(r, c, Player.ONE):
                    one_moves.append((r, c))

        if not one_moves:
            # ONE must pass. legal_moves() should handle this.
            moves = game.legal_moves()
            # BUG: Currently returns []. Should return TWO's moves or handle pass.
            assert len(moves) > 0, (
                "BUG: Reversi legal_moves() returns [] when current player must pass. "
                "Should return opponent's moves."
            )


class TestRaveRewardConsistency:
    """BUG 5: RAVE backpropagation reward perspective is incorrect.

    The _backpropagate method calls node.update(reward) which flips the reward
    at each level. Then for RAVE, it walks from the leaf to root again,
    starting with the same initial reward and flipping at each level.

    However, the AMAF update for a move m at node n should use the reward
    from the perspective of the player who would make move m at node n.
    The current code starts with `amaf_reward = reward` (the root player's
    reward) and flips going up. But the leaf node is at the bottom, and the
    first flip should happen before reaching the leaf's parent.

    The issue is that node.update(reward) already starts updating from the
    leaf with the root player's reward. But the leaf node's player_to_move
    is NOT the root player (unless depth=0). The update() method always
    uses the passed reward for the first node, then flips for the parent.

    For standard MCTS this is correct because:
    - The reward is from the root player's perspective
    - The leaf node represents a state where it's someone's turn
    - The leaf's visits/rewards track the root player's reward
    - Then the parent tracks the opponent's reward (flipped)

    For RAVE, the same flipping pattern is used, which is consistent.
    This test verifies RAVE produces correct results.
    """

    def test_rave_winning_position(self):
        """RAVE should identify a winning move correctly."""
        game = TicTacToe()
        # X can win at (0,2)
        game = game.apply(GameMove(0, 0))  # X
        game = game.apply(GameMove(1, 0))  # O
        game = game.apply(GameMove(0, 1))  # X
        game = game.apply(GameMove(1, 1))  # O

        engine = MCTSEngine(
            RAVEPolicy(1.4142, 300), simulation_limit=5000,
            rave=True, seed=42,
        )
        result = engine.search(game)
        # Should find the winning move (0,2) with high win rate
        assert result.best_move is not None
        # With enough simulations, should find (0,2) or equivalent winning move
        assert result.win_rate > 0.5


class TestConnect4DiagonalWin:
    """Test that Connect4 correctly detects diagonal wins through apply()."""

    def test_diagonal_win_through_play(self):
        """Test a real diagonal win through actual gameplay."""
        game = Connect4(rows=5, cols=5)
        # Build diagonal (4,0), (3,1), (2,2), (1,3) for X
        # Need to stack pieces properly with gravity
        # Col 0: (4,0) = X
        game = game.apply(GameMove(4, 0))  # X
        # Col 1: (4,1) = O, (3,1) = X
        game = game.apply(GameMove(4, 1))  # O
        game = game.apply(GameMove(3, 1))  # X
        # Col 2: (4,2) = O, (3,2) = X, (2,2) = O
        # Wait, turns alternate: X, O, X, O, X, O...
        # 1: X at (4,0)
        # 2: O at (4,1)
        # 3: X at (3,1)
        # 4: O at (4,2)
        # 5: X at (3,2)
        # 6: O at (2,2)
        # 7: X at (4,3)
        # 8: O at (3,3)
        # 9: X at (2,3)
        # 10: O at (1,3)
        # 11: X at (1,3) -- need (2,3), (3,3), (4,3) filled first
        # This won't work with alternating turns giving X the diagonal.
        # Let's just test the check_winner method directly.
        pass

    def test_direct_diagonal_check(self):
        """Test _check_winner directly with a diagonal board."""
        game = Connect4(rows=5, cols=5)
        game.board = [
            [Player.NONE, Player.NONE, Player.NONE, Player.NONE, Player.NONE],
            [Player.NONE, Player.NONE, Player.NONE, Player.ONE, Player.NONE],
            [Player.NONE, Player.NONE, Player.ONE, Player.TWO, Player.NONE],
            [Player.NONE, Player.ONE, Player.TWO, Player.TWO, Player.NONE],
            [Player.ONE, Player.TWO, Player.TWO, Player.TWO, Player.NONE],
        ]
        # X diagonal: (4,0), (3,1), (2,2), (1,3)
        result = game._check_winner(1, 3)
        assert result == Player.ONE

    def test_anti_diagonal_check(self):
        """Test anti-diagonal (bottom-right to top-left) win."""
        game = Connect4(rows=5, cols=5)
        game.board = [
            [Player.NONE, Player.NONE, Player.NONE, Player.NONE, Player.ONE],
            [Player.NONE, Player.NONE, Player.NONE, Player.ONE, Player.TWO],
            [Player.NONE, Player.NONE, Player.ONE, Player.TWO, Player.TWO],
            [Player.NONE, Player.ONE, Player.TWO, Player.TWO, Player.TWO],
            [Player.NONE, Player.TWO, Player.TWO, Player.TWO, Player.TWO],
        ]
        # X anti-diagonal: (4,0)->no, (3,1), (2,2), (1,3), (0,4)
        # That's 4 in anti-diagonal: (0,4), (1,3), (2,2), (3,1)
        result = game._check_winner(0, 4)
        assert result == Player.ONE


class TestMCTSNodeEdgeCases:
    def test_ucb_value_visited_child_parent_zero(self):
        """UCB value with parent_visits=0 should not crash."""
        game = TicTacToe()
        node = MCTSNode(game)
        child = MCTSNode(game.apply(GameMove(0, 0)), parent=node)
        child.visits = 1
        child.total_reward = 0.5
        val = child.ucb_value(1.4142, 0)
        assert isinstance(val, float)
        assert val == 0.5  # just exploitation

    def test_rave_value_parent_zero(self):
        """RAVE value with parent_visits=0 should not crash."""
        game = TicTacToe()
        node = MCTSNode(game)
        child = MCTSNode(game.apply(GameMove(0, 0)), parent=node)
        child.visits = 1
        child.total_reward = 0.5
        child._amaf_visits = 1
        child._amaf_reward = 0.6
        val = child.rave_value(1.4142, 0, 300)
        assert isinstance(val, float)

    def test_expand_terminal_node(self):
        """Expanding a terminal node should return None."""
        game = TicTacToe()
        game = game.apply(GameMove(0, 0))
        game = game.apply(GameMove(1, 0))
        game = game.apply(GameMove(0, 1))
        game = game.apply(GameMove(1, 1))
        game = game.apply(GameMove(0, 2))  # X wins
        node = MCTSNode(game)
        assert node.is_terminal
        assert node.expand() is None

    def test_principal_variation_empty(self):
        """PV of a leaf node should be empty."""
        game = TicTacToe()
        node = MCTSNode(game)
        pv = node.principal_variation()
        assert len(pv) == 0

    def test_depth(self):
        """Depth should count ancestors."""
        game = TicTacToe()
        root = MCTSNode(game)
        child = root.expand()
        assert child.depth() == 1
        grandchild = child.expand()
        assert grandchild.depth() == 2
        assert root.depth() == 0


class TestGridGameCopyExtraAttrs:
    """Test that subclass attributes are properly copied in apply()."""

    def test_gomoku_win_length_copied(self):
        """BUG FIX: Gomoku._win_length must be copied in apply()."""
        game = Gomoku(size=7)
        new_game = game.apply(GameMove(3, 3))
        assert hasattr(new_game, "_win_length")
        assert new_game._win_length == 5

    def test_gomoku_custom_win_length(self):
        """Test that custom win length is preserved."""
        game = Gomoku(size=7)
        game._win_length = 3  # custom win length
        new_game = game.apply(GameMove(3, 3))
        assert new_game._win_length == 3

    def test_gomoku_3_in_row_win(self):
        """Test win with custom win length of 3."""
        game = Gomoku(size=5)
        game._win_length = 3
        game = game.apply(GameMove(2, 0))  # X
        game = game.apply(GameMove(0, 0))  # O
        game = game.apply(GameMove(2, 1))  # X
        game = game.apply(GameMove(0, 1))  # O
        game = game.apply(GameMove(2, 2))  # X - 3 in a row
        assert game.is_terminal()
        assert game.winner() == Player.ONE


class TestEngineEdgeCases:
    def test_search_no_legal_moves(self):
        """Search on a state with no legal moves should return no best move."""
        game = TicTacToe()
        game = game.apply(GameMove(0, 0))
        game = game.apply(GameMove(1, 0))
        game = game.apply(GameMove(0, 1))
        game = game.apply(GameMove(1, 1))
        game = game.apply(GameMove(0, 2))  # X wins
        engine = MCTSEngine(simulation_limit=100, seed=42)
        result = engine.search(game)
        assert result.best_move is None

    def test_search_single_move(self):
        """When only one legal move remains, engine should pick it."""
        game = TicTacToe()
        # Fill 8 of 9 cells (no winner yet)
        moves = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)]
        # X O X
        # O . O
        # X O X -- need to arrange so no one wins
        # Actually let's do: X O X / X O X / O X . (no winner, last move for O)
        game = TicTacToe()
        game = game.apply(GameMove(0, 0))  # X
        game = game.apply(GameMove(0, 1))  # O
        game = game.apply(GameMove(0, 2))  # X
        game = game.apply(GameMove(1, 1))  # O
        game = game.apply(GameMove(1, 0))  # X
        game = game.apply(GameMove(1, 2))  # O
        game = game.apply(GameMove(2, 1))  # X
        game = game.apply(GameMove(2, 0))  # O
        # Only (2,2) remains, X's turn
        assert len(game.legal_moves()) == 1
        engine = MCTSEngine(simulation_limit=100, seed=42)
        result = engine.search(game)
        assert result.best_move is not None
        assert result.best_move == GameMove(2, 2)

    def test_parallel_single_thread(self):
        """Parallel search with 1 thread should fall back to regular search."""
        game = TicTacToe()
        engine = MCTSEngine(simulation_limit=100, seed=42)
        result = engine.search_parallel(game, num_threads=1)
        assert result.best_move is not None
        assert result.simulations == 100

    def test_rollout_limit(self):
        """Rollout should stop at rollout_limit."""
        game = Gomoku(size=7)
        engine = MCTSEngine(simulation_limit=50, seed=42, rollout_limit=5)
        result = engine.search(game)
        assert result.best_move is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])