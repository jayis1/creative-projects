#!/usr/bin/env python3
"""Tests for the Procedural ASCII Dungeon Map Generator."""

import json
import sys
import os

# Add parent directory to path so we can import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dungeon_generator import (
    DungeonConfig, DungeonGenerator, validate_config,
    Room, Entity, WALL, FLOOR, CORRIDOR, DOOR, STAIRS_UP, STAIRS_DOWN,
    WATER, PILLAR, __version__,
)


def test_basic_generation():
    """Test that a dungeon can be generated with default config."""
    config = DungeonConfig(seed=42)
    gen = DungeonGenerator(config)
    gen.generate()

    assert len(gen.rooms) >= 2, f"Expected at least 2 rooms, got {len(gen.rooms)}"
    assert len(gen.entities) > 0, "Expected at least one entity"

    # Check grid has non-wall tiles
    has_floor = any(
        gen.grid[y][x] != WALL
        for y in range(config.height)
        for x in range(config.width)
    )
    assert has_floor, "Dungeon should have walkable tiles"

    print("✓ test_basic_generation passed")


def test_reproducibility_with_seed():
    """Test that the same seed produces identical dungeons."""
    config1 = DungeonConfig(seed=12345)
    gen1 = DungeonGenerator(config1)
    gen1.generate()
    map1 = gen1.render()

    config2 = DungeonConfig(seed=12345)
    gen2 = DungeonGenerator(config2)
    gen2.generate()
    map2 = gen2.render()

    assert map1 == map2, "Same seed should produce identical maps"

    print("✓ test_reproducibility_with_seed passed")


def test_different_seeds_produce_different_maps():
    """Test that different seeds produce different maps."""
    gen1 = DungeonGenerator(DungeonConfig(seed=1))
    gen1.generate()
    map1 = gen1.render()

    gen2 = DungeonGenerator(DungeonConfig(seed=2))
    gen2.generate()
    map2 = gen2.render()

    assert map1 != map2, "Different seeds should produce different maps"

    print("✓ test_different_seeds_produce_different_maps passed")


def test_all_themes():
    """Test that all themes generate without errors."""
    for theme in ["standard", "crypt", "inferno", "forest", "aquatic"]:
        config = DungeonConfig(theme=theme, seed=10)
        gen = DungeonGenerator(config)
        gen.generate()

        assert len(gen.rooms) >= 2, f"Theme {theme} should produce rooms"
        rendered = gen.render()
        assert len(rendered) > 0, f"Theme {theme} should render a map"
        legend = gen.render_legend()
        assert theme.upper() in legend, f"Legend should mention theme {theme}"

    print("✓ test_all_themes passed")


def test_difficulty_levels():
    """Test that higher difficulty produces more monsters."""
    configs = [
        DungeonConfig(difficulty=1, seed=99, max_rooms=10),
        DungeonConfig(difficulty=5, seed=99, max_rooms=10),
    ]
    monster_counts = []
    for config in configs:
        gen = DungeonGenerator(config)
        gen.generate()
        monsters = [e for e in gen.entities if e.kind == "monster"]
        monster_counts.append(len(monsters))

    # Higher difficulty should generally produce more or tougher monsters
    # (Same seed, so room layout is identical; difficulty scales count)
    assert monster_counts[1] >= monster_counts[0], \
        f"Higher difficulty should have at least as many monsters: " \
        f"d1={monster_counts[0]}, d5={monster_counts[1]}"

    print("✓ test_difficulty_levels passed")


def test_connectivity():
    """Test that generated dungeons are fully connected."""
    for seed in range(10):
        config = DungeonConfig(seed=seed, width=50, height=25)
        gen = DungeonGenerator(config)
        gen.generate()
        assert gen._check_connectivity(), \
            f"Dungeon with seed={seed} should be fully connected"

    print("✓ test_connectivity passed")


def test_stairs_exist():
    """Test that stairs up and down are placed."""
    config = DungeonConfig(seed=42)
    gen = DungeonGenerator(config)
    gen.generate()

    has_up = any(
        gen.grid[y][x] == STAIRS_UP
        for y in range(config.height)
        for x in range(config.width)
    )
    has_down = any(
        gen.grid[y][x] == STAIRS_DOWN
        for y in range(config.height)
        for x in range(config.width)
    )

    assert has_up, "Dungeon should have stairs up (▲)"
    assert has_down, "Dungeon should have stairs down (▼)"

    print("✓ test_stairs_exist passed")


def test_features_can_be_disabled():
    """Test that disabling features actually removes them."""
    config = DungeonConfig(
        seed=42,
        add_water=False,
        add_pillars=False,
        add_traps=False,
        add_doors=False,
        add_npcs=False,
    )
    gen = DungeonGenerator(config)
    gen.generate()

    # No water tiles
    has_water = any(
        gen.grid[y][x] == WATER
        for y in range(config.height)
        for x in range(config.width)
    )
    # No pillar tiles
    has_pillars = any(
        gen.grid[y][x] == PILLAR
        for y in range(config.height)
        for x in range(config.width)
    )
    # No doors
    has_doors = any(
        gen.grid[y][x] == DOOR
        for y in range(config.height)
        for x in range(config.width)
    )
    # No traps
    has_traps = any(e.kind == "trap" for e in gen.entities)
    # No NPCs
    has_npcs = any(e.kind == "npc" for e in gen.entities)

    assert not has_water, "Water should be disabled"
    assert not has_pillars, "Pillars should be disabled"
    assert not has_doors, "Doors should be disabled"
    assert not has_traps, "Traps should be disabled"
    assert not has_npcs, "NPCs should be disabled"

    print("✓ test_features_can_be_disabled passed")


def test_npcs_have_dialogue():
    """Test that NPCs are placed with dialogue."""
    config = DungeonConfig(seed=42, add_npcs=True)
    gen = DungeonGenerator(config)
    gen.generate()

    npcs = [e for e in gen.entities if e.kind == "npc"]
    if npcs:
        for npc in npcs:
            assert npc.dialogue, f"NPC '{npc.description}' should have dialogue"
            assert npc.description, "NPC should have a name"

    print("✓ test_npcs_have_dialogue passed")


def test_json_export():
    """Test JSON export produces valid JSON with expected structure."""
    config = DungeonConfig(seed=42)
    gen = DungeonGenerator(config)
    gen.generate()

    json_str = gen.to_json()
    data = json.loads(json_str)

    assert data["version"] == __version__, "JSON should include version"
    assert "config" in data, "JSON should include config"
    assert "rooms" in data, "JSON should include rooms"
    assert "entities" in data, "JSON should include entities"
    assert "grid" in data, "JSON should include grid"
    assert "map" in data, "JSON should include rendered map"

    assert len(data["rooms"]) == len(gen.rooms), "Room count should match"
    assert len(data["entities"]) == len(gen.entities), "Entity count should match"
    assert len(data["grid"]) == config.height, "Grid height should match"
    assert len(data["grid"][0]) == config.width, "Grid width should match"

    # Room data should have name
    for room in data["rooms"]:
        assert "name" in room, "Room should have a name"
        assert "id" in room, "Room should have an id"
        assert "center" in room, "Room should have center coords"

    print("✓ test_json_export passed")


def test_fog_of_war():
    """Test fog of war rendering hides unrevealed areas."""
    config = DungeonConfig(seed=42)
    gen = DungeonGenerator(config)
    gen.generate()

    full_map = gen.render()
    fog_map = gen.render_fog_of_war(reveal_radius=4)

    # Fog map should have more spaces (hidden areas) than full map
    fog_spaces = fog_map.count(" ")
    full_spaces = full_map.count(" ")
    assert fog_spaces > full_spaces, \
        "Fog of war should hide some areas with spaces"

    print("✓ test_fog_of_war passed")


def test_room_names():
    """Test that rooms are given themed names."""
    for theme in ["standard", "crypt", "inferno", "forest", "aquatic"]:
        config = DungeonConfig(theme=theme, seed=42)
        gen = DungeonGenerator(config)
        gen.generate()

        assert all(r.name for r in gen.rooms), \
            f"All rooms should have names (theme: {theme})"
        # First room should be "Entrance Hall", last should be "Descent"
        assert gen.rooms[0].name == "Entrance Hall", \
            "First room should be 'Entrance Hall'"
        assert gen.rooms[-1].name == "Descent", \
            "Last room should be 'Descent'"

    print("✓ test_room_names passed")


def test_validate_config():
    """Test that validate_config catches invalid configurations."""
    # Too small
    errors = validate_config(DungeonConfig(width=5, height=5))
    assert len(errors) > 0, "Should error on too-small dimensions"

    # Too large
    errors = validate_config(DungeonConfig(width=500, height=500))
    assert len(errors) > 0, "Should error on too-large dimensions"

    # Valid config
    errors = validate_config(DungeonConfig())
    assert len(errors) == 0, f"Default config should be valid, got: {errors}"

    print("✓ test_validate_config passed")


def test_render_legend_and_stats():
    """Test that legend and stats render without errors."""
    config = DungeonConfig(seed=42)
    gen = DungeonGenerator(config)
    gen.generate()

    legend = gen.render_legend()
    assert "LEGEND" in legend
    assert "ROOMS" in legend

    stats = gen.render_stats()
    assert "Floor density" in stats
    assert "Rooms" in stats

    print("✓ test_render_legend_and_stats passed")


def test_no_entity_overlap():
    """Test that no two entities occupy the same position."""
    config = DungeonConfig(seed=42)
    gen = DungeonGenerator(config)
    gen.generate()

    positions = [(e.x, e.y) for e in gen.entities]
    assert len(positions) == len(set(positions)), \
        "No two entities should occupy the same position"

    print("✓ test_no_entity_overlap passed")


def test_version_defined():
    """Test that the version constant is defined."""
    assert __version__, "Version should be defined"
    parts = __version__.split(".")
    assert len(parts) == 3, "Version should follow semver (x.y.z)"

    print("✓ test_version_defined passed")


if __name__ == "__main__":
    print("Running dungeon_generator tests...\n")
    test_basic_generation()
    test_reproducibility_with_seed()
    test_different_seeds_produce_different_maps()
    test_all_themes()
    test_difficulty_levels()
    test_connectivity()
    test_stairs_exist()
    test_features_can_be_disabled()
    test_npcs_have_dialogue()
    test_json_export()
    test_fog_of_war()
    test_room_names()
    test_validate_config()
    test_render_legend_and_stats()
    test_no_entity_overlap()
    test_version_defined()
    print("\n✅ All tests passed!")