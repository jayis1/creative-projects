"""
Command-line interface for the MCTS engine.

Usage:
    python -m mcts play --game tictactoe --sims 5000
    python -m mcts play --game connect4 --sims 10000 --rave
    python -m mcts play --game hex --size 7 --sims 20000 --time-limit 5
    python -m mcts selfplay --game tictactoe --sims 2000 --save game.json
    python -m mcts benchmark --game tictactoe --sims 5000 --rounds 10 --rave
    python -m mcts analyze --game tictactoe --sims 5000
    python -m mcts replay game.json
    python -m mcts tournament --game tictactoe --sims 2000 --rounds 4
    python -m mcts config --show config.yaml
    python -m mcts minimax --game tictactoe
    python -m mcts list
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Dict, List, Optional, Tuple

from .core import GameMove, GameState, MCTSResult, Player
from .engine import MCTSEngine
from .games import Connect4, Gomoku, Hex, Reversi, TicTacToe
from .heuristics import get_heuristic, make_rollout_policy
from .record import GameRecord, play_recorded_game
from .uct import RAVEPolicy, UCTPolicy
from .config import MCTSConfig, EngineConfig, GameConfig
from .minimax import MinimaxEngine
from .tournament import Tournament, PlayerSpec

GAMES = {
    "tictactoe": TicTacToe,
    "connect4": Connect4,
    "gomoku": Gomoku,
    "reversi": Reversi,
    "hex": Hex,
}


def make_game(name: str, size: int = 0) -> GameState:
    """Create a game instance by name."""
    name = name.lower()
    if name not in GAMES:
        raise ValueError(f"Unknown game: {name}. Available: {list(GAMES.keys())}")
    cls = GAMES[name]
    if name == "tictactoe":
        return TicTacToe()
    if name == "connect4":
        return Connect4()
    if name == "gomoku":
        return Gomoku(size if size > 0 else 15)
    if name == "reversi":
        return Reversi(size if size > 0 else 8)
    if name == "hex":
        return Hex(size if size > 0 else 11)
    return cls()


def build_engine(args: argparse.Namespace) -> MCTSEngine:
    """Build an MCTS engine from CLI arguments."""
    rave = getattr(args, "rave", False)
    policy = RAVEPolicy(1.4142, 300.0) if rave else UCTPolicy(1.4142)

    # Optional heuristic for progressive bias / rollout
    heuristic_fn = None
    rollout_policy = None
    progressive_bias = 0.0

    if getattr(args, "heuristic", False):
        heuristic_fn = get_heuristic(args.game)
        if heuristic_fn is not None:
            progressive_bias = 1.0
            if getattr(args, "epsilon_rollout", 0.0) > 0:
                rollout_policy = make_rollout_policy(heuristic_fn, args.epsilon_rollout)

    engine = MCTSEngine(
        selection_policy=policy,
        simulation_limit=args.sims,
        time_limit=getattr(args, "time_limit", 0.0),
        rave=rave,
        verbose=getattr(args, "verbose", False),
        seed=getattr(args, "seed", 42),
        rollout_policy=rollout_policy,
        progressive_bias=progressive_bias,
        heuristic_fn=heuristic_fn,
        tree_reuse=getattr(args, "tree_reuse", False),
    )
    return engine


def play_game(
    game: GameState,
    engine: MCTSEngine,
    human_player: Optional[Player] = None,
    max_moves: int = 200,
) -> Tuple[GameState, List[Tuple[Player, GameMove, MCTSResult]]]:
    """Play a full game, alternating between human and engine.

    Args:
        game: Initial game state.
        engine: MCTS engine for AI moves.
        human_player: Which player is human (None = both AI).
        max_moves: Safety limit.

    Returns:
        (final_state, move_history) where move_history is a list of
        (player, move, mcts_result) tuples.
    """
    history: List[Tuple[Player, GameMove, MCTSResult]] = []
    current = game
    count = 0

    while not current.is_terminal() and count < max_moves:
        player = current.current_player()
        print(f"\n{player}'s turn:")
        print(current.display())
        legal = current.legal_moves()

        if not legal:
            print("No legal moves! Game over.")
            break

        if human_player and player == human_player:
            # Human input
            while True:
                try:
                    inp = input(f"Enter move (row col), or 'q' to quit: ").strip()
                    if inp.lower() == "q":
                        print("Quitting.")
                        return current, history
                    parts = inp.split()
                    row, col = int(parts[0]), int(parts[1])
                    move = GameMove(row, col)
                    # Validate
                    if move not in legal:
                        print(f"Illegal move. Legal moves: {[(m.row, m.col) for m in legal]}")
                        continue
                    break
                except (ValueError, IndexError):
                    print("Invalid input. Format: row col (e.g., '1 2')")
        else:
            # Engine move
            result = engine.search(current)
            move = result.best_move
            if move is None:
                print("Engine found no move!")
                break
            print(f"  Engine plays: ({move.row}, {move.col}) "
                  f"[sims={result.simulations}, win_rate={result.win_rate:.1%}]")
            if result.principal_variation:
                print(f"  PV: {result.principal_variation[:5]}")
            history.append((player, move, result))

        current = current.apply(move)
        count += 1

    print(f"\nFinal position:")
    print(current.display())
    w = current.winner()
    if w == Player.NONE:
        print("Game over: Draw!")
    else:
        print(f"Game over: {w} wins!")
    return current, history


def self_play(
    game: GameState,
    engine: MCTSEngine,
    max_moves: int = 200,
    save_path: Optional[str] = None,
    game_type: str = "",
) -> Tuple[GameState, GameRecord]:
    """Engine plays both sides, optionally saving the game record."""
    final_state, record = play_recorded_game(game, engine, game_type=game_type, max_moves=max_moves)
    print(f"\nFinal board:")
    print(final_state.display())
    w = final_state.winner()
    if w == Player.NONE:
        print("Result: Draw!")
    else:
        print(f"Result: {w} wins!")
    print(f"\n{record.to_text()}")

    if save_path:
        record.save(save_path)
        print(f"\nGame saved to {save_path}")
    return final_state, record


def benchmark(game_name: str, sims: int, rounds: int, rave: bool = False, heuristic: bool = False) -> None:
    """Run a benchmark comparing different MCTS configurations."""
    print(f"\nBenchmark: {game_name} ({rounds} rounds, {sims} sims/move)")

    if rave:
        eng1 = MCTSEngine(UCTPolicy(1.4142), simulation_limit=sims, verbose=False, seed=42)
        eng2 = MCTSEngine(RAVEPolicy(1.4142, 300.0), simulation_limit=sims, rave=True, verbose=False, seed=99)
        label1, label2 = "UCT", "RAVE"
    elif heuristic:
        h = get_heuristic(game_name)
        if h is None:
            print(f"No heuristic available for {game_name}, falling back to parameter comparison")
            eng1 = MCTSEngine(UCTPolicy(1.4142), simulation_limit=sims, verbose=False, seed=42)
            eng2 = MCTSEngine(UCTPolicy(0.5), simulation_limit=sims, verbose=False, seed=99)
            label1, label2 = "UCT(c=1.41)", "UCT(c=0.5)"
        else:
            eng1 = MCTSEngine(UCTPolicy(1.4142), simulation_limit=sims, verbose=False, seed=42)
            eng2 = MCTSEngine(UCTPolicy(1.4142), simulation_limit=sims, verbose=False, seed=99,
                              progressive_bias=1.0, heuristic_fn=h)
            label1, label2 = "UCT", "UCT+PB"
    else:
        eng1 = MCTSEngine(UCTPolicy(1.4142), simulation_limit=sims, verbose=False, seed=42)
        eng2 = MCTSEngine(UCTPolicy(0.5), simulation_limit=sims, verbose=False, seed=99)
        label1, label2 = "UCT(c=1.41)", "UCT(c=0.5)"

    results = {label1: 0, label2: 0, "Draw": 0}
    for i in range(rounds):
        game = make_game(game_name)
        current = game
        count = 0
        while not current.is_terminal() and count < 200:
            player = current.current_player()
            eng = eng1 if player == Player.ONE else eng2
            result = eng.search(current)
            if result.best_move is None:
                break
            current = current.apply(result.best_move)
            count += 1
        w = current.winner()
        if w == Player.ONE:
            results[label1] += 1
        elif w == Player.TWO:
            results[label2] += 1
        else:
            results["Draw"] += 1
        winner_str = label1 if w == Player.ONE else label2 if w == Player.TWO else "Draw"
        print(f"  Round {i+1}: {winner_str}")

    print(f"\nResults: {label1}={results[label1]}, {label2}={results[label2]}, Draw={results['Draw']}")


def analyze(game: GameState, engine: MCTSEngine) -> None:
    """Analyze a position: show search results and move evaluation."""
    print(f"\nAnalyzing position:")
    print(game.display())
    print(f"\nCurrent player: {game.current_player()}")
    print(f"Legal moves: {len(game.legal_moves())}")

    result = engine.search(game)
    print(f"\nSearch results ({engine.policy.name}):")
    print(f"  Best move: {result.best_move}")
    print(f"  Win rate: {result.win_rate:.1%}")
    print(f"  Simulations: {result.simulations}")
    print(f"  Time: {result.time_elapsed:.3f}s")
    print(f"  Tree size: {result.root.tree_size()}")

    if result.root.children:
        print(f"\nMove evaluation ({len(result.root.children)} moves):")
        print(f"  {'Move':>12s}  {'Visits':>8s}  {'Win%':>6s}  {'UCB':>8s}")
        for child in sorted(result.root.children, key=lambda c: c.visits, reverse=True):
            wr = child.average_reward()
            ucb = child.ucb_value(1.4142, result.root.visits)
            print(f"  {str(child.move):>12s}  {child.visits:>8d}  {wr:>5.1%}  {ucb:>8.3f}")

    pv = result.principal_variation
    if pv:
        print(f"\nPrincipal variation: {' → '.join(str(m) for m in pv[:8])}")


def replay_game(path: str) -> None:
    """Replay a saved game from a JSON file."""
    record = GameRecord.load(path)
    print(f"Replaying: {record.game_type}, {len(record.moves)} moves")
    print(f"Winner: {record.winner}")
    print()

    # Reconstruct the game
    game = make_game(record.game_type, record.board_size)
    current = game
    print(current.display())

    for i, (move_data, stats) in enumerate(zip(record.moves, record.search_stats)):
        player = Player[move_data["player"]]
        row, col = move_data["row"], move_data["col"]
        move = GameMove(row, col)
        sims = stats.get("simulations", 0)
        wr = stats.get("win_rate", 0.0)

        print(f"\nMove {i+1}: {player} plays ({row}, {col}) "
              f"[sims={sims}, wr={wr:.1%}]")
        current = current.apply(move)
        print(current.display())

    w = current.winner()
    if w == Player.NONE:
        print("\nResult: Draw")
    else:
        print(f"\nResult: {w} wins!")


def run_tournament(
    game_name: str,
    sims: int,
    rounds: int,
    size: int = 0,
) -> None:
    """Run a round-robin tournament between different engine configs."""
    print(f"\nTournament: {game_name} ({rounds} rounds, {sims} sims/move)")
    print("=" * 50)

    factory = lambda: make_game(game_name, size)

    players = [
        PlayerSpec("UCT-c1.41", MCTSEngine(
            UCTPolicy(1.4142), simulation_limit=sims, seed=42)),
        PlayerSpec("UCT-c0.5", MCTSEngine(
            UCTPolicy(0.5), simulation_limit=sims, seed=99)),
        PlayerSpec("RAVE", MCTSEngine(
            RAVEPolicy(1.4142, 300), simulation_limit=sims, rave=True, seed=77)),
    ]

    # Add heuristic player if available
    h = get_heuristic(game_name)
    if h is not None:
        players.append(PlayerSpec("UCT+Heur", MCTSEngine(
            UCTPolicy(1.4142), simulation_limit=sims, seed=55,
            progressive_bias=1.0, heuristic_fn=h)))

    tourney = Tournament(players, factory, rounds=rounds)
    result = tourney.run()
    print()
    print(result.summary())


def run_minimax(game_name: str, size: int = 0, max_depth: int = 0) -> None:
    """Run minimax search on a game position."""
    game = make_game(game_name, size)
    print(f"\nMinimax analysis: {game_name}")
    print(game.display())
    print(f"\nCurrent player: {game.current_player()}")
    print(f"Legal moves: {len(game.legal_moves())}")

    depth = max_depth if max_depth > 0 else 9
    engine = MinimaxEngine(max_depth=depth, verbose=True)
    result = engine.search(game)

    print(f"\nResult:")
    print(f"  Best move: {result.best_move}")
    print(f"  Score: {result.score:+.1f} ({'Win' if result.score > 0 else 'Draw' if result.score == 0 else 'Loss'})")
    print(f"  Depth: {result.depth}")
    print(f"  Nodes: {result.nodes_searched}")
    print(f"  Time: {result.time_elapsed:.3f}s")
    if result.principal_variation:
        print(f"  PV: {' → '.join(str(m) for m in result.principal_variation[:8])}")


def show_config(path: Optional[str]) -> None:
    """Show or generate a configuration file."""
    if path:
        config = MCTSConfig.from_file(path)
        print("Configuration loaded from", path)
        print(json.dumps(config.to_dict(), indent=2))
    else:
        # Print a default config
        config = MCTSConfig()
        print("Default configuration:")
        print(json.dumps(config.to_dict(), indent=2))
        print("\nSave to file with: mcts config --save config.json")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcts",
        description="Monte Carlo Tree Search game engine",
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # Common game arguments
    def add_game_args(p):
        p.add_argument("--game", choices=list(GAMES.keys()), default="tictactoe")
        p.add_argument("--sims", type=int, default=5000, help="Simulations per move")
        p.add_argument("--time-limit", type=float, default=0.0, help="Max seconds per move")
        p.add_argument("--rave", action="store_true", help="Enable RAVE")
        p.add_argument("--size", type=int, default=0, help="Board size")
        p.add_argument("--verbose", action="store_true", help="Print search stats")
        p.add_argument("--heuristic", action="store_true", help="Enable heuristic-guided search")
        p.add_argument("--epsilon-rollout", type=float, default=0.0,
                       help="Epsilon for heuristic rollout policy (0=disabled)")
        p.add_argument("--tree-reuse", action="store_true", help="Reuse tree between moves")
        p.add_argument("--seed", type=int, default=42, help="Random seed")
        p.add_argument("--config", type=str, default=None,
                       help="Path to YAML/JSON config file (overrides CLI flags)")

    # Play
    p_play = sub.add_parser("play", help="Play a game (human vs AI)")
    add_game_args(p_play)
    p_play.add_argument("--parallel", type=int, default=0, help="Number of threads (0=single)")
    p_play.add_argument("--human", choices=["X", "O"], default="X", help="Human player")

    # Self-play
    p_self = sub.add_parser("selfplay", help="Engine plays both sides")
    add_game_args(p_self)
    p_self.add_argument("--save", type=str, default=None, help="Save game record to JSON file")

    # Benchmark
    p_bench = sub.add_parser("benchmark", help="Benchmark MCTS configurations")
    p_bench.add_argument("--game", choices=list(GAMES.keys()), default="tictactoe")
    p_bench.add_argument("--sims", type=int, default=5000)
    p_bench.add_argument("--rounds", type=int, default=10)
    p_bench.add_argument("--rave", action="store_true", help="Compare UCT vs RAVE")
    p_bench.add_argument("--heuristic", action="store_true", help="Compare UCT vs UCT+progressive bias")

    # Analyze
    p_analyze = sub.add_parser("analyze", help="Analyze a position")
    add_game_args(p_analyze)

    # Replay
    p_replay = sub.add_parser("replay", help="Replay a saved game")
    p_replay.add_argument("path", help="Path to saved game JSON file")

    # Tournament
    p_tourney = sub.add_parser("tournament", help="Round-robin tournament between engine configs")
    p_tourney.add_argument("--game", choices=list(GAMES.keys()), default="tictactoe")
    p_tourney.add_argument("--sims", type=int, default=2000, help="Simulations per move")
    p_tourney.add_argument("--rounds", type=int, default=2, help="Rounds (each pair plays twice per round)")
    p_tourney.add_argument("--size", type=int, default=0, help="Board size")

    # Minimax
    p_minimax = sub.add_parser("minimax", help="Minimax analysis (exact search for small games)")
    p_minimax.add_argument("--game", choices=list(GAMES.keys()), default="tictactoe")
    p_minimax.add_argument("--size", type=int, default=0, help="Board size")
    p_minimax.add_argument("--depth", type=int, default=0, help="Max search depth (0=auto)")

    # Config
    p_config = sub.add_parser("config", help="Show or generate configuration")
    p_config.add_argument("path", nargs="?", default=None, help="Config file to load")
    p_config.add_argument("--save", type=str, default=None, help="Save default config to file")

    # List games
    sub.add_parser("list", help="List available games")

    # Version
    sub.add_parser("version", help="Show version")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "version":
        from . import __version__
        print(f"mcts-engine v{__version__}")
        return 0

    if args.command == "list":
        print("Available games:")
        for name, cls in GAMES.items():
            print(f"  {name:15s} - {cls.__doc__ or cls.__name__}")
        return 0

    if args.command == "benchmark":
        benchmark(args.game, args.sims, args.rounds, args.rave, args.heuristic)
        return 0

    if args.command == "replay":
        replay_game(args.path)
        return 0

    if args.command == "analyze":
        engine = build_engine(args)
        game = make_game(args.game, getattr(args, "size", 0))
        analyze(game, engine)
        return 0

    if args.command == "tournament":
        run_tournament(args.game, args.sims, args.rounds, getattr(args, "size", 0))
        return 0

    if args.command == "minimax":
        run_minimax(args.game, getattr(args, "size", 0), getattr(args, "depth", 0))
        return 0

    if args.command == "config":
        if args.save:
            config = MCTSConfig()
            config.to_json(args.save)
            print(f"Default configuration saved to {args.save}")
        else:
            show_config(args.path)
        return 0

    # Play and selfplay — support config file override
    if getattr(args, "config", None):
        config = MCTSConfig.from_file(args.config)
        game = config.game.create()
        engine = config.engine.create(config.game.name)
        if args.command == "play":
            human = Player.ONE if args.human == "X" else Player.TWO
            play_game(game, engine, human_player=human)
        elif args.command == "selfplay":
            self_play(game, engine, save_path=getattr(args, "save", None),
                      game_type=config.game.name)
        return 0

    # Play and selfplay
    engine = build_engine(args)
    game = make_game(args.game, getattr(args, "size", 0))

    if args.command == "play":
        human = Player.ONE if args.human == "X" else Player.TWO
        if args.parallel and args.parallel > 1:
            print(f"Using {args.parallel} threads for parallel search")
            original_search = engine.search

            def parallel_search(state):
                return engine.search_parallel(state, num_threads=args.parallel)

            engine.search = parallel_search  # type: ignore
        play_game(game, engine, human_player=human)
        return 0

    if args.command == "selfplay":
        self_play(game, engine, save_path=getattr(args, "save", None), game_type=args.game)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())