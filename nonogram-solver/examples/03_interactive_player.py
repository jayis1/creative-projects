"""
Example: Using the interactive player API.

Demonstrates how to programmatically play a nonogram puzzle,
check progress, and get hints.
"""
from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.player import Player

# Create a solved board (for the solution).
solved = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
Solver().solve(solved)

# Create a player (starts with all cells unknown).
player = Player(solved)
print("Initial board (all unknown):")
print(player.render())
print()

# Get a hint.
hint = player.hint()
if hint:
    r, c, cell = hint
    print(f"Hint: cell ({r}, {c}) should be "
          f"{'FILLED' if cell is Cell.FILLED else 'EMPTY'}")
    player.fill(r, c) if cell is Cell.FILLED else player.blank(r, c)

# Make some moves.
player.fill(2, 2)  # Center — correct!
player.fill(1, 1)  # Also correct
player.blank(0, 0)  # Correct (empty corner)

print("\nAfter some moves:")
print(player.render())
print()

# Check progress.
print(f"Check (correct so far): {player.check()}")
print(f"Won: {player.is_won()}")

# Get another hint.
hint2 = player.hint()
if hint2:
    r, c, cell = hint2
    print(f"Next hint: ({r}, {c}) = "
          f"{'FILLED' if cell is Cell.FILLED else 'EMPTY'}")

# Render with clues.
print("\nBoard with clues:")
print(player.render_with_clues())