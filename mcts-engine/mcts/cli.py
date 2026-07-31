"""
Command-line interface for the MCTS engine.

Usage:
    python -m mcts.cli play --game tictactoe --sims 5000
    python -m mcts.cli play --game connect4 --sims 10000 --rave
    python -m mcts.cli play --game hex --size 7 --sims 20000 --time-limit 5
    python -m mcts.cli selfplay --game tictactoe --sims 2000
    python -m mcts.cli benchmark --game tictactoe --sims 5000 --rounds 10
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Dict, List, Optional, Tuple

from .core import GameMove, GameState, MCTSResult, Player
from .engine import MCTSEngine
from .games import Connect4, Gomoku, Hex, Reversi, TicTacToe
from .uct import RAVEPolicy, UCTPolicy

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
            print("No legal moves! Skipping turn...")
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


def self_play(game: GameState, engine: MCTSEngine, max_moves: int = 200) -> Tuple[GameState, List[Tuple[Player, GameMove, MCTSResult]]]:
    """Engine plays both sides."""
    return play_game(game, engine, human_player=None, max_moves=max_moves)


def benchmark(game_name: str, sims: int, rounds: int, rave: bool = False) -> None:
    """Run a benchmark: UCT vs RAVE (or UCT vs UCT with different params)."""
    print(f"\nBenchmark: {game_name} ({rounds} rounds, {sims} sims/move)")

    if rave:
        eng1 = MCTSEngine(UCTPolicy(1.4142), simulation_limit=sims, verbose=False, seed=42)
        eng2 = MCTSEngine(RAVEPolicy(1.4142, 300.0), simulation_limit=sims, rave=True, verbose=False, seed=99)
        label1, label2 = "UCT", "RAVE"
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
        print(f"  Round {i+1}: {label1 if w == Player.ONE else label2 if w == Player.TWO else 'Draw'}")

    print(f"\nResults: {label1}={results[label1]}, {label2}={results[label2]}, Draw={results['Draw']}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcts",
        description="Monte Carlo Tree Search game engine",
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # Play
    p_play = sub.add_parser("play", help="Play a game (human vs AI)")
    p_play.add_argument("--game", choices=list(GAMES.keys()), default="tictactoe")
    p_play.add_argument("--sims", type=int, default=5000, help="Simulations per move")
    p_play.add_argument("--time-limit", type=float, default=0.0, help="Max seconds per move")
    p_play.add_argument("--rave", action="store_true", help="Enable RAVE")
    p_play.add_argument("--size", type=int, default=0, help="Board size (for size-configurable games)")
    p_play.add_argument("--parallel", type=int, default=0, help="Number of threads (0=single)")
    p_play.add_argument("--human", choices=["X", "O"], default="X", help="Human player")
    p_play.add_argument("--verbose", action="store_true", help="Print search stats")

    # Self-play
    p_self = sub.add_parser("selfplay", help="Engine plays both sides")
    p_self.add_argument("--game", choices=list(GAMES.keys()), default="tictactoe")
    p_self.add_argument("--sims", type=int, default=2000)
    p_self.add_argument("--rave", action="store_true")
    p_self.add_argument("--size", type=int, default=0)
    p_self.add_argument("--time-limit", type=float, default=0.0)
    p_self.add_argument("--verbose", action="store_true")

    # Benchmark
    p_bench = sub.add_parser("benchmark", help="Benchmark different MCTS configurations")
    p_bench.add_argument("--game", choices=list(GAMES.keys()), default="tictactoe")
    p_bench.add_argument("--sims", type=int, default=5000)
    p_bench.add_argument("--rounds", type=int, default=10)
    p_bench.add_argument("--rave", action="store_true", help="Compare UCT vs RAVE")

    # List games
    sub.add_parser("list", help="List available games")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "list":
        print("Available games:")
        for name, cls in GAMES.items():
            print(f"  {name:15s} - {cls.__doc__ or cls.__name__}")
        return 0

    if args.command == "benchmark":
        benchmark(args.game, args.sims, args.rounds, args.rave)
        return 0

    # Build engine
    policy = RAVEPolicy(1.4142, 300.0) if getattr(args, "rave", False) else UCTPolicy(1.4142)
    engine = MCTSEngine(
        selection_policy=policy,
        simulation_limit=args.sims,
        time_limit=args.time_limit,
        rave=getattr(args, "rave", False),
        verbose=getattr(args, "verbose", False),
        seed=42,
    )

    game = make_game(args.game, getattr(args, "size", 0))

    if args.command in ("play", "selfplay"):
        human = None
        if args.command == "play":
            human = Player.ONE if args.human == "X" else Player.TWO

        if args.parallel and args.parallel > 1:
            # Use parallel search
            print(f"Using {args.parallel} threads for parallel search")
            # For parallel mode, we wrap the search call
            original_search = engine.search

            def parallel_search(state):
                return engine.search_parallel(state, num_threads=args.parallel)

            engine.search = parallel_search  # type: ignore

        play_game(game, engine, human_player=human)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())