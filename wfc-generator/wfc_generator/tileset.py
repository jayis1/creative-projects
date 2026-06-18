"""TileSet: a collection of tiles with validation, JSON I/O, and symmetry."""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from .tile import Tile, SIDES, OPPOSITE_SIDE

logger = logging.getLogger(__name__)


class TileSet:
    """A collection of :class:`Tile` objects with adjacency constraints.

    Provides methods for validation, bidirectional symmetrization of
    constraints, loading/saving from JSON, and generating rotated/reflected
    tile variants.
    """

    def __init__(self) -> None:
        self.tiles: Dict[str, Tile] = {}

    # ------------------------------------------------------------------ #
    # Membership
    # ------------------------------------------------------------------ #
    def add_tile(self, tile: Tile) -> None:
        """Add a tile to the set (overwrites an existing tile of the same name)."""
        if tile.name in self.tiles:
            logger.warning("Overwriting existing tile %r", tile.name)
        self.tiles[tile.name] = tile

    def get_tile(self, name: str) -> Optional[Tile]:
        """Return the tile named ``name`` or ``None``."""
        return self.tiles.get(name)

    def remove_tile(self, name: str) -> Optional[Tile]:
        """Remove and return the tile named ``name`` (or ``None``)."""
        return self.tiles.pop(name, None)

    def __contains__(self, name: object) -> bool:
        return name in self.tiles

    def __len__(self) -> int:
        return len(self.tiles)

    def __iter__(self):
        return iter(self.tiles.values())

    @property
    def names(self) -> List[str]:
        """Sorted list of all tile names."""
        return sorted(self.tiles.keys())

    # ------------------------------------------------------------------ #
    # Symmetry
    # ------------------------------------------------------------------ #
    def make_symmetric(
        self, tile_name: Optional[str] = None, direction: str = "both"
    ) -> None:
        """Make adjacency constraints bidirectional.

        If tile *A* allows *B* on its ``right`` side, then *B* is made to allow
        *A* on its ``left`` side.

        Parameters
        ----------
        tile_name:
            If given, only symmetrize from this tile. If ``None``, symmetrize
            from all tiles.
        direction:
            ``'horizontal'`` (left<->right), ``'vertical'`` (top<->bottom),
            or ``'both'``.
        """
        tiles_to_process = (
            [self.tiles[tile_name]] if tile_name else list(self.tiles.values())
        )

        for tile in tiles_to_process:
            sides: List[str] = []
            if direction in ("horizontal", "both"):
                sides.extend(["right", "left"])
            if direction in ("vertical", "both"):
                sides.extend(["top", "bottom"])

            for side in sides:
                opp = OPPOSITE_SIDE[side]
                for neighbor_name in list(tile.constraints[side]):
                    neighbor = self.tiles.get(neighbor_name)
                    if neighbor:
                        neighbor.add_constraint(opp, tile.name)

    def make_all_symmetric(self) -> None:
        """Make all adjacency constraints bidirectional across all tiles."""
        self.make_symmetric(direction="both")

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self) -> List[str]:
        """Check for issues in the tile set; return a list of warning strings."""
        warnings: List[str] = []
        for name, tile in self.tiles.items():
            for side in SIDES:
                for neighbor_name in tile.constraints[side]:
                    if neighbor_name not in self.tiles:
                        warnings.append(
                            f"Tile {name!r} references unknown tile "
                            f"{neighbor_name!r} on {side}"
                        )
            total_constraints = sum(len(tile.constraints[s]) for s in SIDES)
            if total_constraints == 0:
                warnings.append(f"Tile {name!r} has no adjacency constraints (isolated)")
        total_weight = sum(t.weight for t in self.tiles.values())
        if total_weight <= 0:
            warnings.append("Total weight of all tiles is zero or negative")
        return warnings

    # ------------------------------------------------------------------ #
    # Rotation variants
    # ------------------------------------------------------------------ #
    def add_rotated_variants(
        self, base_name: str, suffixes: Optional[List[str]] = None
    ) -> None:
        """Add 90°, 180°, and 270° clockwise rotated variants of a tile.

        Rotating a tile 90° clockwise transforms the sides as
        ``top -> right -> bottom -> left -> top``.  Both the constraint sides
        and the in-constraint tile name references that point to the base tile
        (or known variants) are remapped to the corresponding rotated names.
        """
        if suffixes is None:
            suffixes = ["", "_r90", "_r180", "_r270"]

        base = self.tiles.get(base_name)
        if not base:
            return

        # original_name -> [0°, 90°, 180°, 270°] rotated names
        name_map: Dict[str, List[str]] = {}
        for suffix in suffixes:
            original = base_name + suffix
            name_map[original] = [base_name + s for s in suffixes]

        rotation_map = {
            "top": "right",
            "right": "bottom",
            "bottom": "left",
            "left": "top",
        }

        def remap_constraints(constraints, rotation_idx):
            new_constraints = {side: set() for side in SIDES}
            for side, tile_names in constraints.items():
                new_side = side
                for _ in range(1):  # one 90° rotation per step
                    new_side = rotation_map[new_side]
                for tile_name in tile_names:
                    if tile_name in name_map:
                        new_tile_name = name_map[tile_name][rotation_idx]
                        new_constraints[new_side].add(new_tile_name)
                    else:
                        new_constraints[new_side].add(tile_name)
            return new_constraints

        variants = [base]  # 0° (already exists)
        for i in range(1, 4):
            name = f"{base_name}{suffixes[i]}"
            prev_constraints = variants[i - 1].constraints
            new_constraints = remap_constraints(prev_constraints, i)
            rotated = Tile(name, weight=base.weight, color=base.color)
            rotated.constraints = new_constraints
            variants.append(rotated)
            self.add_tile(rotated)

    # ------------------------------------------------------------------ #
    # JSON I/O
    # ------------------------------------------------------------------ #
    @classmethod
    def from_json(cls, path: str) -> "TileSet":
        """Load a tile set from a JSON file.

        Expected format::

            {"tiles": [{"name": ..., "weight": ..., "color": ...,
                        "symbol": ..., "constraints": {"top": [...], ...}}, ...]}
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        ts = cls()
        for i, tile_data in enumerate(data.get("tiles", [])):
            if "name" not in tile_data:
                raise ValueError(f"Tile at index {i} is missing required 'name' field")
            weight = tile_data.get("weight", 1.0)
            if isinstance(weight, (int, float)) and weight < 0:
                raise ValueError(
                    f"Tile {tile_data['name']!r} has negative weight {weight}. "
                    f"All weights must be non-negative."
                )
            tile = Tile(
                name=tile_data["name"],
                weight=weight,
                color=tile_data.get("color", ""),
                data=tile_data.get("symbol", tile_data["name"]),
            )
            constraints = tile_data.get("constraints", {})
            for side in SIDES:
                if side in constraints:
                    tile.add_constraint(side, constraints[side])
            ts.add_tile(tile)
        return ts

    def to_json(self, path: str) -> None:
        """Save this tile set to a JSON file."""
        data = {"tiles": []}
        for name, tile in sorted(self.tiles.items()):
            tile_data = {
                "name": name,
                "weight": tile.weight,
                "color": tile.color,
                "symbol": tile.data,
                "constraints": {
                    side: sorted(list(constraints))
                    for side, constraints in tile.constraints.items()
                },
            }
            data["tiles"].append(tile_data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)