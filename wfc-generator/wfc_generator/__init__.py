"""Wave Function Collapse (WFC) Procedural Generation Engine.

A modular implementation of the Wave Function Collapse algorithm for
procedural content generation. Supports tile-based and overlap-based
generation, backtracking, periodic boundaries, multiple rendering
formats, and a configuration system.

Public API (re-exports for backward compatibility)::

    from wfc_generator import (
        Tile, TileSet, WFCGrid, OverlapModel, Renderer,
        GenerationStats, WFCConfig, SelectionStrategy,
        create_terrain_tileset, create_dungeon_tileset,
        create_city_tileset, create_circuit_tileset,
        create_maze_tileset, create_village_tileset,
        create_islands_tileset,
    )
"""

from .tile import Tile
from .tileset import TileSet
from .stats import GenerationStats
from .grid import WFCGrid, SelectionStrategy
from .overlap import OverlapModel
from .renderer import Renderer
from .presets import (
    create_terrain_tileset,
    create_dungeon_tileset,
    create_city_tileset,
    create_circuit_tileset,
    create_maze_tileset,
    create_village_tileset,
    create_islands_tileset,
)
from .config import WFCConfig

__version__ = "2.0.0"

__all__ = [
    "Tile",
    "TileSet",
    "WFCGrid",
    "OverlapModel",
    "Renderer",
    "GenerationStats",
    "WFCConfig",
    "SelectionStrategy",
    "create_terrain_tileset",
    "create_dungeon_tileset",
    "create_city_tileset",
    "create_circuit_tileset",
    "create_maze_tileset",
    "create_village_tileset",
    "create_islands_tileset",
    "__version__",
]