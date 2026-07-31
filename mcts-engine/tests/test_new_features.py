"""
Tests for new features: config, minimax, opening book, tournament, logging.
"""

import json
import os
import tempfile

import pytest

from mcts import (
    MCTSEngine, TicTacToe, Connect4, Hex, Gomoku, Reversi,
    UCTPolicy, RAVEPolicy, Player, GameMove, MCTSNode,
    MCTSConfig, GameConfig, EngineConfig,
    MinimaxEngine, MinimaxResult,
    OpeningBook,
    Tournament, PlayerSpec, TournamentResult,
)
from mcts.logging_utils import get_logger, configure_logging


# ─── Config Tests ───

class TestGameConfig:
    def test_default(self):
        cfg = GameConfig()
        game = cfg.create()
        assert isinstance(game, TicTacToe)

    def test_connect4(self):
        cfg = GameConfig(name="connect4")
        game = cfg.create()
        assert isinstance(game, Connect4)

    def test_hex_with_size(self):
        cfg = GameConfig(name="hex", size=7)
        game = cfg.create()
        assert isinstance(game, Hex)
        assert game.rows == 7

    def test_gomoku_with_size(self):
        cfg = GameConfig(name="gomoku", size=9)
        game = cfg.create()
        assert isinstance(game, Gomoku)
        assert game.rows == 9

    def test_reversi_with_size(self):
        cfg = GameConfig(name="reversi", size=6)
        game = cfg.create()
        assert isinstance(game, Reversi)
        assert game.rows == 6

    def test_unknown_game(self):
        cfg = GameConfig(name="chess")
        with pytest.raises(ValueError):
            cfg.create()


class TestEngineConfig:
    def test_default_uct(self):
        cfg = EngineConfig()
        engine = cfg.create("tictactoe")
        assert isinstance(engine.policy, UCTPolicy)
        assert engine.simulation_limit == 10000

    def test_rave(self):
        cfg = EngineConfig(policy="rave", rave_k=500)
        engine = cfg.create("tictactoe")
        assert isinstance(engine.policy, RAVEPolicy)
        assert engine.rave is True

    def test_with_heuristic(self):
        cfg = EngineConfig(heuristic=True)
        engine = cfg.create("tictactoe")
        assert engine.heuristic_fn is not None

    def test_with_rollout(self):
        cfg = EngineConfig(heuristic=True, epsilon_rollout=0.2)
        engine = cfg.create("tictactoe")
        assert engine.rollout_policy is not None


class TestMCTSConfig:
    def test_from_dict(self):
        data = {
            "game": {"name": "connect4", "size": 0},
            "engine": {"policy": "rave", "simulation_limit": 3000},
        }
        cfg = MCTSConfig.from_dict(data)
        assert cfg.game.name == "connect4"
        assert cfg.engine.policy == "rave"
        assert cfg.engine.simulation_limit == 3000

    def test_from_json_file(self, tmp_path):
        data = {
            "game": {"name": "hex", "size": 7},
            "engine": {"policy": "uct", "simulation_limit": 500, "seed": 99},
        }
        path = str(tmp_path / "config.json")
        with open(path, "w") as f:
            json.dump(data, f)
        cfg = MCTSConfig.from_file(path)
        assert cfg.game.name == "hex"
        assert cfg.game.size == 7
        assert cfg.engine.seed == 99

    def test_to_json_and_back(self, tmp_path):
        cfg = MCTSConfig()
        cfg.game.name = "gomoku"
        cfg.game.size = 9
        cfg.engine.simulation_limit = 2000
        path = str(tmp_path / "out.json")
        cfg.to_json(path)
        loaded = MCTSConfig.from_file(path)
        assert loaded.game.name == "gomoku"
        assert loaded.game.size == 9
        assert loaded.engine.simulation_limit == 2000

    def test_from_yaml_file(self, tmp_path):
        yaml_content = """
game:
  name: tictactoe
  size: 0
engine:
  policy: uct
  simulation_limit: 1000
  seed: 42
"""
        path = str(tmp_path / "config.yaml")
        with open(path, "w") as f:
            f.write(yaml_content)
        cfg = MCTSConfig.from_file(path)
        assert cfg.game.name == "tictactoe"
        assert cfg.engine.simulation_limit == 1000

    def test_auto_detect_format(self, tmp_path):
        # .json extension
        json_path = str(tmp_path / "c.json")
        with open(json_path, "w") as f:
            json.dump({"game": {"name": "connect4"}, "engine": {}}, f)
        cfg = MCTSConfig.from_file(json_path)
        assert cfg.game.name == "connect4"

    def test_create_game_and_engine(self):
        cfg = MCTSConfig()
        cfg.game.name = "tictactoe"
        cfg.engine.simulation_limit = 100
        game = cfg.game.create()
        engine = cfg.engine.create(cfg.game.name)
        result = engine.search(game)
        assert result.best_move is not None


# ─── Minimax Tests ───

class TestMinimaxEngine:
    def test_tictactoe_perfect_play(self):
        """Minimax should never lose at Tic-Tac-Toe."""
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=9)
        result = engine.search(game)
        assert result.best_move is not None
        # Opening move should be a draw with perfect play
        assert result.score == 0.0  # Tic-Tac-Toe is a draw with perfect play

    def test_tictactoe_winning_position(self):
        """Minimax should find a winning move."""
        game = TicTacToe()
        game = game.apply(GameMove(0, 0))  # X
        game = game.apply(GameMove(1, 0))  # O
        game = game.apply(GameMove(0, 1))  # X
        game = game.apply(GameMove(1, 1))  # O
        # X can win at (0, 2)
        engine = MinimaxEngine(max_depth=5)
        result = engine.search(game)
        assert result.best_move == GameMove(0, 2)
        assert result.score == 1.0  # winning

    def test_tictactoe_losing_position(self):
        """Minimax should detect a losing position."""
        game = TicTacToe()
        game = game.apply(GameMove(0, 0))  # X
        game = game.apply(GameMove(1, 0))  # O
        game = game.apply(GameMove(0, 1))  # X
        game = game.apply(GameMove(1, 1))  # O
        game = game.apply(GameMove(0, 2))  # X wins
        # Now it's O's turn but game is terminal
        assert game.is_terminal()
        engine = MinimaxEngine(max_depth=1)
        result = engine.search(game)
        assert result.best_move is None  # no moves in terminal state

    def test_depth_limit(self):
        """Depth-limited search should still return a valid move."""
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=1)
        result = engine.search(game)
        assert result.best_move is not None
        assert result.depth == 1

    def test_nodes_searched(self):
        """Should track number of nodes searched."""
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=3)
        result = engine.search(game)
        assert result.nodes_searched > 0

    def test_principal_variation(self):
        """PV should be a list of moves."""
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=3)
        result = engine.search(game)
        assert isinstance(result.principal_variation, list)

    def test_transposition_table(self):
        """Transposition table should speed up search."""
        game = TicTacToe()
        engine_with = MinimaxEngine(max_depth=6, use_transposition=True)
        engine_without = MinimaxEngine(max_depth=6, use_transposition=False)
        r1 = engine_with.search(game)
        r2 = engine_without.search(game)
        # Both should find the same score
        assert r1.score == r2.score
        # With transposition should search fewer or equal nodes
        assert engine_with._nodes <= engine_without._nodes

    def test_connect4_shallow(self):
        """Minimax should work on Connect4 with shallow depth."""
        game = Connect4(rows=4, cols=4)
        engine = MinimaxEngine(max_depth=4)
        result = engine.search(game)
        assert result.best_move is not None

    def test_move_ordering(self):
        """Move ordering should prefer center moves."""
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=1)
        moves = engine._order_moves(game.legal_moves(), game)
        # Center (1,1) should be first
        assert moves[0] == GameMove(1, 1)

    def test_reset(self):
        """Reset should clear transposition table."""
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=5, use_transposition=True)
        engine.search(game)
        assert len(engine._transposition) > 0
        engine.reset()
        assert len(engine._transposition) == 0

    def test_full_tictactoe_game(self):
        """Play a full Tic-Tac-Toe game with minimax — should draw."""
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=9)
        current = game
        while not current.is_terminal():
            result = engine.search(current)
            if result.best_move is None:
                break
            current = current.apply(result.best_move)
        assert current.is_terminal()
        # Perfect play → draw
        assert current.winner() == Player.NONE

    def test_minimax_beats_random(self):
        """Minimax should beat random play in Tic-Tac-Toe."""
        import random
        rng = random.Random(42)
        game = TicTacToe()
        engine = MinimaxEngine(max_depth=9)
        current = game
        while not current.is_terminal():
            player = current.current_player()
            if player == Player.ONE:
                result = engine.search(current)
                move = result.best_move
            else:
                legal = current.legal_moves()
                move = rng.choice(legal)
            if move is None:
                break
            current = current.apply(move)
        # Minimax (Player ONE) should win or draw
        assert current.winner() in (Player.ONE, Player.NONE)


# ─── Opening Book Tests ───

class TestOpeningBook:
    def test_add_and_lookup(self):
        game = TicTacToe()
        book = OpeningBook()
        book.add(game, GameMove(1, 1), weight=1.0)
        move = book.lookup(game)
        assert move is not None
        assert move == GameMove(1, 1)

    def test_weighted_selection(self):
        game = TicTacToe()
        book = OpeningBook()
        # Add two moves with different weights
        book.add(game, GameMove(0, 0), weight=0.01)
        book.add(game, GameMove(1, 1), weight=0.99)
        # The center move should be selected most of the time
        counts = {GameMove(0, 0): 0, GameMove(1, 1): 0}
        for _ in range(1000):
            move = book.lookup(game)
            if move is not None:
                counts[move] = counts.get(move, 0) + 1
        # Center should be selected more often
        assert counts[GameMove(1, 1)] > counts[GameMove(0, 0)]

    def test_has(self):
        game = TicTacToe()
        book = OpeningBook()
        assert not book.has(game)
        book.add(game, GameMove(0, 0))
        assert book.has(game)

    def test_save_load(self, tmp_path):
        game = TicTacToe()
        book = OpeningBook()
        book.add(game, GameMove(1, 1), weight=1.0, depth=0)
        path = str(tmp_path / "book.json")
        book.save(path)
        loaded = OpeningBook.load(path)
        assert len(loaded) == 1
        move = loaded.lookup(game)
        assert move == GameMove(1, 1)

    def test_load_nonexistent(self, tmp_path):
        """Loading a non-existent file should return an empty book."""
        book = OpeningBook.load(str(tmp_path / "nonexistent.json"))
        assert len(book) == 0

    def test_build_from_selfplay(self):
        """Building a book from self-play should produce entries."""
        game = TicTacToe()
        engine = MCTSEngine(simulation_limit=50, seed=42)
        book = OpeningBook.build_from_selfplay(
            game, engine, num_games=10, max_depth=3, seed=42
        )
        assert len(book) > 0
        # The initial position should be in the book
        assert book.has(game)

    def test_empty_book_lookup(self):
        """Looking up in an empty book should return None."""
        book = OpeningBook()
        game = TicTacToe()
        assert book.lookup(game) is None

    def test_duplicate_move(self):
        """Adding the same move twice should update weight, not duplicate."""
        game = TicTacToe()
        book = OpeningBook()
        book.add(game, GameMove(1, 1), weight=0.5)
        book.add(game, GameMove(1, 1), weight=1.0)
        # Should have one entry with max weight
        entry = book._entries[game.hash_key()]
        assert len(entry["moves"]) == 1
        assert entry["moves"][0]["weight"] == 1.0


# ─── Tournament Tests ───

class TestTournament:
    def test_two_players(self):
        """A tournament with 2 players should run 2 games per round."""
        players = [
            PlayerSpec("A", MCTSEngine(UCTPolicy(1.4142), simulation_limit=100, seed=42)),
            PlayerSpec("B", MCTSEngine(UCTPolicy(0.5), simulation_limit=100, seed=99)),
        ]
        tourney = Tournament(players, game_factory=lambda: TicTacToe(), rounds=2)
        result = tourney.run()
        assert len(result.games) == 4  # 2 players × 2 rounds × 2 sides
        # All games should have a result
        for g in result.games:
            assert g.winner in ("A", "B", "Draw")

    def test_elo_updates(self):
        """Elo ratings should change after games."""
        players = [
            PlayerSpec("A", MCTSEngine(UCTPolicy(1.4142), simulation_limit=100, seed=42)),
            PlayerSpec("B", MCTSEngine(UCTPolicy(0.5), simulation_limit=100, seed=99)),
        ]
        tourney = Tournament(players, game_factory=lambda: TicTacToe(), rounds=2)
        result = tourney.run()
        # At least one player's Elo should have changed
        elos = list(result.elo_ratings.values())
        assert any(e != 1000.0 for e in elos)

    def test_standings(self):
        """Standings should record wins, losses, and draws."""
        players = [
            PlayerSpec("A", MCTSEngine(UCTPolicy(1.4142), simulation_limit=100, seed=42)),
            PlayerSpec("B", MCTSEngine(UCTPolicy(0.5), simulation_limit=100, seed=99)),
        ]
        tourney = Tournament(players, game_factory=lambda: TicTacToe(), rounds=2)
        result = tourney.run()
        for name in ["A", "B"]:
            s = result.standings[name]
            assert s["wins"] + s["losses"] + s["draws"] > 0

    def test_summary(self):
        """Summary should be a non-empty string."""
        players = [
            PlayerSpec("A", MCTSEngine(UCTPolicy(1.4142), simulation_limit=50, seed=42)),
            PlayerSpec("B", MCTSEngine(UCTPolicy(0.5), simulation_limit=50, seed=99)),
        ]
        tourney = Tournament(players, game_factory=lambda: TicTacToe(), rounds=1)
        result = tourney.run()
        summary = result.summary()
        assert isinstance(summary, str)
        assert "Tournament Results" in summary
        assert "A" in summary
        assert "B" in summary

    def test_three_players(self):
        """Tournament with 3 players should run 6 games per round."""
        players = [
            PlayerSpec("A", MCTSEngine(UCTPolicy(1.4142), simulation_limit=50, seed=1)),
            PlayerSpec("B", MCTSEngine(UCTPolicy(0.5), simulation_limit=50, seed=2)),
            PlayerSpec("C", MCTSEngine(RAVEPolicy(1.4142, 300), simulation_limit=50, rave=True, seed=3)),
        ]
        tourney = Tournament(players, game_factory=lambda: TicTacToe(), rounds=1)
        result = tourney.run()
        # 3 players → 3 pairs → 3 games per round × 2 (alternating sides) = 6
        assert len(result.games) == 6


# ─── Logging Tests ───

class TestLogging:
    def test_get_logger(self):
        logger = get_logger()
        assert logger.name == "mcts"

    def test_configure_logging(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        logger = configure_logging(level="DEBUG", log_file=log_path)
        logger.debug("Test debug message")
        logger.info("Test info message")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            content = f.read()
        assert "Test debug message" in content
        assert "Test info message" in content

    def test_configure_logging_level(self):
        logger = configure_logging(level="ERROR")
        import logging
        assert logger.level == logging.ERROR


# ─── CLI Tests ───

class TestCLI:
    def test_version(self):
        from mcts.cli import main
        assert main(["version"]) == 0

    def test_list(self):
        from mcts.cli import main
        assert main(["list"]) == 0

    def test_config_no_args(self):
        from mcts.cli import main
        assert main(["config"]) == 0

    def test_config_save(self, tmp_path):
        from mcts.cli import main
        path = str(tmp_path / "config.json")
        assert main(["config", "--save", path]) == 0
        assert os.path.exists(path)
        # Verify it's valid JSON
        with open(path) as f:
            data = json.load(f)
        assert "game" in data
        assert "engine" in data

    def test_config_load(self, tmp_path):
        from mcts.cli import main
        path = str(tmp_path / "config.json")
        data = {"game": {"name": "hex", "size": 5}, "engine": {"simulation_limit": 100}}
        with open(path, "w") as f:
            json.dump(data, f)
        assert main(["config", path]) == 0

    def test_minimax(self):
        from mcts.cli import main
        assert main(["minimax", "--game", "tictactoe", "--depth", "3"]) == 0

    def test_tournament(self):
        from mcts.cli import main
        assert main(["tournament", "--game", "tictactoe", "--sims", "50", "--rounds", "1"]) == 0

    def test_no_command(self):
        from mcts.cli import main
        assert main([]) == 1  # should print help and return 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])