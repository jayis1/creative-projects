"""Example: Play a full game using the Game manager."""

from chess_engine import Board, Game
from chess_engine.notation import parse_algebraic

def main():
    game = Game()

    # Play a few moves manually (like a human would)
    game.play_human_move("e4")
    game.play_human_move("e5")
    game.play_human_move("Nf3")
    game.play_human_move("Nc6")
    game.play_human_move("Bb5")

    print("After 5 moves:")
    print(game.board.to_string(unicode=True))
    print(f"FEN: {game.board.fen()}")
    print(f"Moves: {' '.join(game.san_history)}")
    print()

    # Now let the engine play
    result = game.play_engine_move(depth=3)
    if result:
        move, score = result
        print(f"Engine plays: {game.san_history[-1]} (score: {score})")
        print(game.board.to_string(unicode=True))
    print()

    # Export to PGN
    print("PGN:")
    print(game.to_pgn())


if __name__ == "__main__":
    main()