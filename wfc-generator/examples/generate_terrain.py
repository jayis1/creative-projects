"""Generate a terrain map and render it as both plain text and SVG.

Run with:  python3 examples/generate_terrain.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wfc_generator import (
    WFCGrid, Renderer, create_terrain_tileset, SelectionStrategy,
)

def main():
    tileset = create_terrain_tileset()
    grid = WFCGrid(
        tileset, width=40, height=25, seed=42,
        selection=SelectionStrategy.MIN_ENTROPY,
    )
    if not grid.run():
        print("Generation failed!", file=sys.stderr)
        sys.exit(1)

    result = grid.get_result()
    print(Renderer.render_plain(result))
    print(f"\nStats: {grid.stats}")

    out_dir = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(out_dir, "terrain_output.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(Renderer.render_svg(result, cell_size=20, title="Terrain"))
    print(f"SVG written to {svg_path}")


if __name__ == "__main__":
    main()