"""Preset tile sets for common generation tasks.

Each ``create_*_tileset`` returns a fully-constrained, symmetrized
:class:`~wfc_generator.tileset.TileSet` ready to feed into
:class:`~wfc_generator.grid.WFCGrid`.
"""

from __future__ import annotations

from .tile import Tile
from .tileset import TileSet


def create_dungeon_tileset() -> TileSet:
    """Dungeon/cave tile set: floor, wall, corridor, door, pillar, stairs, treasure."""
    ts = TileSet()
    floor = Tile("floor", weight=10, color="#443322", data=".")
    wall = Tile("wall", weight=8, color="#888877", data="#")
    corridor = Tile("corridor", weight=5, color="#665544", data="=")
    door = Tile("door", weight=2, color="#ccaa44", data="D")
    pillar = Tile("pillar", weight=1, color="#888888", data="o")
    stairs = Tile("stairs", weight=1, color="#55aacc", data=">")
    treasure = Tile("treasure", weight=0.5, color="#ffcc00", data="$")

    for n in ["floor", "corridor", "door", "stairs", "treasure", "pillar"]:
        floor.add_constraint("top", n); floor.add_constraint("bottom", n)
        floor.add_constraint("left", n); floor.add_constraint("right", n)

    for n in ["wall", "floor", "corridor", "door", "pillar"]:
        wall.add_constraint("top", n); wall.add_constraint("bottom", n)
        wall.add_constraint("left", n); wall.add_constraint("right", n)

    for n in ["floor", "corridor", "door", "stairs"]:
        corridor.add_constraint("top", n); corridor.add_constraint("bottom", n)
        corridor.add_constraint("left", n); corridor.add_constraint("right", n)

    for n in ["floor", "corridor", "wall"]:
        door.add_constraint("top", n); door.add_constraint("bottom", n)
        door.add_constraint("left", n); door.add_constraint("right", n)

    for n in ["floor", "wall", "corridor"]:
        pillar.add_constraint("top", n); pillar.add_constraint("bottom", n)
        pillar.add_constraint("left", n); pillar.add_constraint("right", n)

    for n in ["floor", "corridor", "door"]:
        stairs.add_constraint("top", n); stairs.add_constraint("bottom", n)
        stairs.add_constraint("left", n); stairs.add_constraint("right", n)

    for n in ["floor", "wall"]:
        treasure.add_constraint("top", n); treasure.add_constraint("bottom", n)
        treasure.add_constraint("left", n); treasure.add_constraint("right", n)

    for tile in [floor, wall, corridor, door, pillar, stairs, treasure]:
        ts.add_tile(tile)
    ts.make_all_symmetric()
    return ts


def create_terrain_tileset() -> TileSet:
    """Terrain tile set with natural elevation transitions."""
    ts = TileSet()
    deep_water = Tile("deep_water", weight=5, color="#1a5276", data="~")
    shallow_water = Tile("shallow_water", weight=4, color="#5dade2", data="~")
    sand = Tile("sand", weight=3, color="#ccaa44", data=".")
    grass = Tile("grass", weight=12, color="#7dce6e", data="g")
    forest = Tile("forest", weight=8, color="#336622", data="T")
    hill = Tile("hill", weight=4, color="#c4a63d", data="h")
    mountain = Tile("mountain", weight=2, color="#888888", data="^")
    snow = Tile("snow", weight=1, color="#ffffff", data=" ")

    _four(deep_water, ["deep_water", "shallow_water"])
    _four(shallow_water, ["deep_water", "shallow_water", "sand"])
    _four(sand, ["shallow_water", "sand", "grass"])
    _four(grass, ["sand", "grass", "forest", "hill"])
    _four(forest, ["grass", "forest", "hill"])
    _four(hill, ["grass", "forest", "hill", "mountain"])
    _four(mountain, ["hill", "mountain", "snow"])
    _four(snow, ["mountain", "snow"])

    for tile in [deep_water, shallow_water, sand, grass, forest, hill, mountain, snow]:
        ts.add_tile(tile)
    ts.make_all_symmetric()
    return ts


def create_city_tileset() -> TileSet:
    """City/street tile set: roads, buildings, parks, sidewalks, parking."""
    ts = TileSet()
    road_h = Tile("road_h", weight=8, color="#555555", data="-")
    road_v = Tile("road_v", weight=8, color="#555555", data="|")
    intersection = Tile("intersection", weight=5, color="#666666", data="+")
    building = Tile("building", weight=10, color="#cc4444", data="B")
    park = Tile("park", weight=3, color="#66aa44", data="P")
    sidewalk = Tile("sidewalk", weight=4, color="#bbbbbb", data="s")
    parking = Tile("parking", weight=2, color="#999966", data="p")

    for n in ["road_h", "intersection", "sidewalk"]:
        road_h.add_constraint("left", n); road_h.add_constraint("right", n)
    for n in ["sidewalk", "building", "park", "parking"]:
        road_h.add_constraint("top", n); road_h.add_constraint("bottom", n)

    for n in ["road_v", "intersection", "sidewalk"]:
        road_v.add_constraint("top", n); road_v.add_constraint("bottom", n)
    for n in ["sidewalk", "building", "park", "parking"]:
        road_v.add_constraint("left", n); road_v.add_constraint("right", n)

    for n in ["road_h", "road_v", "intersection"]:
        intersection.add_constraint("top", n); intersection.add_constraint("bottom", n)
        intersection.add_constraint("left", n); intersection.add_constraint("right", n)

    for n in ["sidewalk", "building"]:
        building.add_constraint("top", n); building.add_constraint("bottom", n)
        building.add_constraint("left", n); building.add_constraint("right", n)

    for n in ["sidewalk", "park", "building"]:
        park.add_constraint("top", n); park.add_constraint("bottom", n)
        park.add_constraint("left", n); park.add_constraint("right", n)

    for n in ["sidewalk", "building", "park", "road_h", "road_v", "parking"]:
        sidewalk.add_constraint("top", n); sidewalk.add_constraint("bottom", n)
        sidewalk.add_constraint("left", n); sidewalk.add_constraint("right", n)

    for n in ["sidewalk", "parking", "road_h", "road_v"]:
        parking.add_constraint("top", n); parking.add_constraint("bottom", n)
        parking.add_constraint("left", n); parking.add_constraint("right", n)

    for tile in [road_h, road_v, intersection, building, park, sidewalk, parking]:
        ts.add_tile(tile)
    ts.make_all_symmetric()
    return ts


def create_circuit_tileset() -> TileSet:
    """Circuit-board tile set: empty, wires, corners, junctions, components, vias."""
    ts = TileSet()
    empty = Tile("empty", weight=15, color="#1a1a1a", data=" ")
    wire_h = Tile("wire_h", weight=6, color="#33cc33", data="-")
    wire_v = Tile("wire_v", weight=6, color="#33cc33", data="|")
    wire_ne = Tile("wire_ne", weight=3, color="#33cc33", data="└")
    wire_nw = Tile("wire_nw", weight=3, color="#33cc33", data="┘")
    wire_se = Tile("wire_se", weight=3, color="#33cc33", data="┌")
    wire_sw = Tile("wire_sw", weight=3, color="#33cc33", data="┐")
    junction = Tile("junction", weight=2, color="#cc3333", data="+")
    component = Tile("component", weight=4, color="#ccaa33", data="■")
    via = Tile("via", weight=1, color="#33cccc", data="⊙")

    all_tiles = ["empty", "wire_h", "wire_v", "wire_ne", "wire_nw",
                 "wire_se", "wire_sw", "junction", "component", "via"]
    for n in all_tiles:
        empty.add_constraint("top", n); empty.add_constraint("right", n)
        empty.add_constraint("bottom", n); empty.add_constraint("left", n)

    for n in ["empty", "wire_h", "wire_ne", "wire_se", "junction", "component"]:
        wire_h.add_constraint("left", n); wire_h.add_constraint("right", n)
    for n in ["empty", "wire_v", "wire_ne", "wire_nw", "via"]:
        wire_h.add_constraint("top", n); wire_h.add_constraint("bottom", n)

    for n in ["empty", "wire_v", "wire_se", "wire_sw", "junction", "component"]:
        wire_v.add_constraint("top", n); wire_v.add_constraint("bottom", n)
    for n in ["empty", "wire_h", "wire_ne", "wire_se", "via"]:
        wire_v.add_constraint("left", n); wire_v.add_constraint("right", n)

    for n in ["empty", "wire_h", "wire_ne", "wire_se", "junction"]:
        wire_ne.add_constraint("left", n)
    for n in ["empty", "wire_v", "wire_ne", "wire_nw", "junction"]:
        wire_ne.add_constraint("top", n)
    wire_ne.add_constraint("right", ["empty"]); wire_ne.add_constraint("bottom", ["empty"])

    for n in ["empty", "wire_h", "wire_nw", "wire_sw", "junction"]:
        wire_nw.add_constraint("right", n)
    for n in ["empty", "wire_v", "wire_ne", "wire_nw", "junction"]:
        wire_nw.add_constraint("top", n)
    wire_nw.add_constraint("left", ["empty"]); wire_nw.add_constraint("bottom", ["empty"])

    for n in ["empty", "wire_h", "wire_ne", "wire_se", "junction"]:
        wire_se.add_constraint("left", n)
    for n in ["empty", "wire_v", "wire_se", "wire_sw", "junction"]:
        wire_se.add_constraint("bottom", n)
    wire_se.add_constraint("right", ["empty"]); wire_se.add_constraint("top", ["empty"])

    for n in ["empty", "wire_h", "wire_nw", "wire_sw", "junction"]:
        wire_sw.add_constraint("right", n)
    for n in ["empty", "wire_v", "wire_se", "wire_sw", "junction"]:
        wire_sw.add_constraint("bottom", n)
    wire_sw.add_constraint("left", ["empty"]); wire_sw.add_constraint("top", ["empty"])

    for n in all_tiles:
        junction.add_constraint("top", n); junction.add_constraint("right", n)
        junction.add_constraint("bottom", n); junction.add_constraint("left", n)

    for n in ["empty", "wire_h", "wire_v", "component"]:
        component.add_constraint("top", n); component.add_constraint("right", n)
        component.add_constraint("bottom", n); component.add_constraint("left", n)

    for n in ["empty", "wire_h", "wire_v", "via", "junction"]:
        via.add_constraint("top", n); via.add_constraint("right", n)
        via.add_constraint("bottom", n); via.add_constraint("left", n)

    for tile in [empty, wire_h, wire_v, wire_ne, wire_nw,
                 wire_se, wire_sw, junction, component, via]:
        ts.add_tile(tile)
    ts.make_all_symmetric()
    return ts


def create_maze_tileset() -> TileSet:
    """Maze tile set: path, wall, dead_end."""
    ts = TileSet()
    path = Tile("path", weight=6, color="#443322", data=".")
    wall = Tile("wall", weight=10, color="#888877", data="#")
    dead_end = Tile("dead_end", weight=1, color="#665544", data="D")

    for n in ["path", "dead_end"]:
        path.add_constraint("top", n); path.add_constraint("right", n)
        path.add_constraint("bottom", n); path.add_constraint("left", n)
    for side in ["top", "right", "bottom", "left"]:
        path.add_constraint(side, "wall")

    for side in ["top", "right", "bottom", "left"]:
        wall.add_constraint(side, ["wall", "path", "dead_end"])

    for side in ["top", "right", "bottom", "left"]:
        dead_end.add_constraint(side, ["path", "wall", "dead_end"])

    for tile in [path, wall, dead_end]:
        ts.add_tile(tile)
    ts.make_all_symmetric()
    return ts


def create_village_tileset() -> TileSet:
    """Village tile set: grass, path, house, tree, flower, fountain, market, gate.

    A cozy medieval village generator: houses and market stalls cluster along
    winding paths, dotted with decorative trees, flowers and a central fountain.
    """
    ts = TileSet()
    grass = Tile("grass", weight=14, color="#7dce6e", data="g")
    path = Tile("path", weight=6, color="#a1887f", data=".")
    house = Tile("building", weight=4, color="#cc4444", data="B")
    tree = Tile("tree", weight=3, color="#2e7d32", data="♣")
    flower = Tile("flower", weight=2, color="#e91e63", data="✿")
    fountain = Tile("fountain", weight=1, color="#4fc3f7", data="f")
    market = Tile("market", weight=2, color="#d84315", data="M")
    gate = Tile("gate", weight=1, color="#bf8f00", data="G")

    # Grass connects to most things (open fields).
    for n in ["grass", "path", "tree", "flower", "fountain", "market", "gate"]:
        grass.add_constraint("top", n); grass.add_constraint("bottom", n)
        grass.add_constraint("left", n); grass.add_constraint("right", n)

    # Paths connect to paths, houses, market, gate, fountain, grass.
    for n in ["path", "grass", "building", "market", "fountain", "gate"]:
        path.add_constraint("top", n); path.add_constraint("bottom", n)
        path.add_constraint("left", n); path.add_constraint("right", n)

    # Houses cluster near paths and grass.
    for n in ["grass", "path", "building"]:
        house.add_constraint("top", n); house.add_constraint("bottom", n)
        house.add_constraint("left", n); house.add_constraint("right", n)

    # Trees sit in grass.
    for n in ["grass", "tree", "flower"]:
        tree.add_constraint("top", n); tree.add_constraint("bottom", n)
        tree.add_constraint("left", n); tree.add_constraint("right", n)

    # Flowers decorate grass.
    for n in ["grass", "flower", "tree"]:
        flower.add_constraint("top", n); flower.add_constraint("bottom", n)
        flower.add_constraint("left", n); flower.add_constraint("right", n)

    # Fountains sit at path/grass junctions.
    for n in ["grass", "path", "fountain"]:
        fountain.add_constraint("top", n); fountain.add_constraint("bottom", n)
        fountain.add_constraint("left", n); fountain.add_constraint("right", n)

    # Markets sit along paths.
    for n in ["grass", "path", "market"]:
        market.add_constraint("top", n); market.add_constraint("bottom", n)
        market.add_constraint("left", n); market.add_constraint("right", n)

    # Gates at path edges.
    for n in ["grass", "path", "gate"]:
        gate.add_constraint("top", n); gate.add_constraint("bottom", n)
        gate.add_constraint("left", n); gate.add_constraint("right", n)

    for tile in [grass, path, house, tree, flower, fountain, market, gate]:
        ts.add_tile(tile)
    ts.make_all_symmetric()
    return ts


def create_islands_tileset() -> TileSet:
    """Island/archipelago tile set: deep_water, shallow_water, sand, grass, tree, hill, lava, ice.

    A fantasy island generator where volcanic and frozen variants can appear.
    """
    ts = TileSet()
    deep_water = Tile("deep_water", weight=10, color="#1a5276", data="~")
    shallow_water = Tile("shallow_water", weight=6, color="#5dade2", data="~")
    sand = Tile("sand", weight=4, color="#ccaa44", data=".")
    grass = Tile("grass", weight=8, color="#7dce6e", data="g")
    tree = Tile("tree", weight=4, color="#2e7d32", data="♣")
    hill = Tile("hill", weight=3, color="#c4a63d", data="h")
    lava = Tile("lava", weight=1, color="#d84315", data="L")
    ice = Tile("ice", weight=1, color="#81d4fa", data="I")

    _four(deep_water, ["deep_water", "shallow_water"])
    _four(shallow_water, ["deep_water", "shallow_water", "sand"])
    _four(sand, ["shallow_water", "sand", "grass"])
    _four(grass, ["sand", "grass", "tree", "hill"])
    _four(tree, ["grass", "tree", "hill"])
    _four(hill, ["grass", "tree", "hill", "lava", "ice"])
    _four(lava, ["hill", "lava"])
    _four(ice, ["hill", "ice"])

    for tile in [deep_water, shallow_water, sand, grass, tree, hill, lava, ice]:
        ts.add_tile(tile)
    ts.make_all_symmetric()
    return ts


# --------------------------------------------------------------------------- #
# helper
# --------------------------------------------------------------------------- #
def _four(tile: Tile, neighbors):
    """Add ``neighbors`` to all four sides of ``tile``."""
    for side in ["top", "right", "bottom", "left"]:
        tile.add_constraint(side, neighbors)