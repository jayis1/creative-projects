"""
Example: Opening book creation and usage.

Demonstrates building an opening book from self-play, saving it,
loading it, and using it to speed up opening moves.
"""

import os
import tempfile

from mcts import MCTSEngine, TicTacToe, OpeningBook

# Build an opening book from self-play
game = TicTacToe()
engine = MCTSEngine(simulation_limit=200, seed=42)

print("Building opening book from 50 self-play games...")
book = OpeningBook.build_from_selfplay(
    game, engine, num_games=50, max_depth=4, seed=42
)
print(f"Book size: {len(book)} positions")

# Save and reload
book_path = os.path.join(tempfile.gettempdir(), "tictactoe_book.json")
book.save(book_path)
print(f"Saved to: {book_path}")

loaded_book = OpeningBook.load(book_path)
print(f"Loaded book size: {len(loaded_book)}")

# Use the opening book
game = TicTacToe()
move = loaded_book.lookup(game)
if move is not None:
    print(f"\nBook recommends: {move}")
    new_game = game.apply(move)
    print(new_game.display())
else:
    print("\nNo book entry for this position")

# Clean up
os.unlink(book_path)