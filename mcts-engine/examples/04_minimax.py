"""
Example: Minimax exact search on Tic-Tac-Toe.

Minimax with alpha-beta pruning plays perfectly on small games.
For Tic-Tac-Toe, it will never lose.
"""

from mcts import TicTacToe, MinimaxEngine

game = TicTacToe()
print("Tic-Tac-Toe — Minimax analysis")
print(game.display())
print()

# Full-depth minimax (Tic-Tac-Toe has at most 9 plies)
engine = MinimaxEngine(max_depth=9, verbose=True)
result = engine.search(game)

print(f"\nResult:")
print(f"  Best move: {result.best_move}")
print(f"  Score: {result.score:+.1f}")
print(f"  Nodes searched: {result.nodes_searched}")
print(f"  Time: {result.time_elapsed:.4f}s")
print(f"  Principal variation: {result.principal_variation}")

# A score of 0.0 means perfect play leads to a draw (expected for Tic-Tac-Toe)
if result.score == 0.0:
    print("\nPerfect play: Draw (as expected for Tic-Tac-Toe)")
elif result.score > 0:
    print(f"\nCurrent player can force a win!")
else:
    print(f"\nCurrent player will lose against perfect play.")

# Play a full game using minimax
print("\n--- Full self-play game with Minimax ---")
current = game
while not current.is_terminal():
    result = engine.search(current)
    if result.best_move is None:
        break
    print(f"\n{current.current_player()} plays {result.best_move}:")
    current = current.apply(result.best_move)
    print(current.display())

w = current.winner()
if w.name == "NONE":
    print("\nResult: Draw (perfect play)")
else:
    print(f"\nResult: {w} wins!")