"""
Example: Basic MCTS search on Tic-Tac-Toe.

Demonstrates creating a game, running MCTS, and examining the result.
"""

from mcts import MCTSEngine, TicTacToe, UCTPolicy

# Create a fresh Tic-Tac-Toe game
game = TicTacToe()
print("Initial board:")
print(game.display())
print()

# Create an MCTS engine with UCT policy
engine = MCTSEngine(
    selection_policy=UCTPolicy(exploration=1.4142),
    simulation_limit=5000,
    seed=42,
    verbose=True,
)

# Search for the best move
result = engine.search(game)

print(f"\nBest move: {result.best_move}")
print(f"Win rate: {result.win_rate:.1%}")
print(f"Simulations: {result.simulations}")
print(f"Time: {result.time_elapsed:.3f}s")
print(f"Principal variation: {result.principal_variation}")

# Apply the move and show the new board
new_game = game.apply(result.best_move)
print(f"\nBoard after move:")
print(new_game.display())