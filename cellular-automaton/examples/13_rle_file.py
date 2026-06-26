"""RLE file loading and saving.

Load patterns from standard RLE files (the format used by LifeWiki, Golly,
and other CA software) and save patterns back to RLE.
"""

import tempfile
import os

from cellular_automaton import (
    CellularAutomaton, GameOfLifeRule,
    get_pattern, place_pattern, save_rle_file, load_rle_file,
    render_ascii,
)

# Save the Gosper glider gun to an RLE file.
gosper = get_pattern("gosper_gun")
path = os.path.join(tempfile.gettempdir(), "gosper_gun.rle")
save_rle_file(gosper, path)
print(f"Saved Gosper gun to {path}")

# Load it back and run it.
pat = load_rle_file(path)
print(f"Loaded pattern with {len(pat)} cells")

ca = CellularAutomaton(GameOfLifeRule(), width=60, height=40)
place_pattern(ca, pat, x=5, y=5)
ca.step(100)
print(f"\nAfter 100 steps: {ca.alive_count()} alive cells")
print(render_ascii(ca.grid))