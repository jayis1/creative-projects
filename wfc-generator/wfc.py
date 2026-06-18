"""Backward-compatibility shim for the original single-file ``wfc.py``.

All functionality now lives in the :mod:`wfc_generator` package.  This module
re-exports the public API so that existing code using ``from wfc import ...``
and ``python3 wfc.py <mode> ...`` continues to work unchanged.
"""

import os
import sys

# Make the sibling package importable when this file is run directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wfc_generator import (  # noqa: E402,F401
    Tile,
    TileSet,
    WFCGrid,
    OverlapModel,
    Renderer,
    GenerationStats,
    WFCConfig,
    SelectionStrategy,
    create_terrain_tileset,
    create_dungeon_tileset,
    create_city_tileset,
    create_circuit_tileset,
    create_maze_tileset,
    create_village_tileset,
    create_islands_tileset,
    __version__,
)

# Preserve the original CLI entry point behaviour.
from wfc_generator.cli import main  # noqa: E402


if __name__ == "__main__":
    main()