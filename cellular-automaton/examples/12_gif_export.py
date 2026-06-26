"""GIF animation export.

Export a Conway's Game of Life evolution as an animated GIF.
Requires Pillow: pip install pillow
"""

from cellular_automaton import (
    CellularAutomaton, GameOfLifeRule, get_pattern, place_pattern, render_gif,
)

ca = CellularAutomaton(GameOfLifeRule(), width=60, height=40)
place_pattern(ca, get_pattern("gosper_gun"), x=5, y=10)

# Render 200 steps as a GIF with 50ms per frame.
render_gif(ca, path="gosper_gun.gif", steps=200, cell_size=4, duration=50)
print("Saved gosper_gun.gif (200 frames)")
print(f"Final alive cells: {ca.alive_count()}")