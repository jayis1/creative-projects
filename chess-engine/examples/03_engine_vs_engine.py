"""Example: Engine vs engine self-play game."""

from chess_engine import Game
import io

def main():
    game = Game()
    output = io.StringIO()

    print("Starting engine vs engine game (depth=3, max 50 moves)...")
    result = game.play_engine_vs_engine(
        depth=3, max_moves=50, output=output,
    )

    print(output.getvalue())
    print(f"Result: {result}")
    print(f"Total moves: {len(game.move_history)}")
    print()
    print("PGN:")
    print(game.to_pgn())


if __name__ == "__main__":
    main()