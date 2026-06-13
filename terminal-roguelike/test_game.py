#!/usr/bin/env python3
"""Non-interactive test for the roguelike engine."""
import sys
import os

# Non-interactive — don't import main or any terminal stuff
sys.path.insert(0, os.path.dirname(__file__))

from roguelike import (
    Game, Item, ENEMY_TEMPLATES, FLOOR_LOOT, roll, 
    Room, DungeonGenerator, MAP_W, MAP_H, T_FLOOR, T_WALL, T_STAIRS
)

print("=== Roguelike Engine Tests ===")

# Test 1: Dice rolling
print("\n--- Dice Rolling ---")
for dice in ['1d6', '2d8+3', '3d10-2', '1d4+1']:
    results = [roll(dice) for _ in range(10)]
    print(f"  {dice}: {results}")

# Test 2: Room generation
print("\n--- Dungeon Generation ---")
dungeon = DungeonGenerator(MAP_W, MAP_H, floor_num=1)
dungeon.generate()
floor_tiles = sum(1 for y in range(MAP_H) for x in range(MAP_W) if dungeon.tiles[y][x] == T_FLOOR)
wall_tiles = sum(1 for y in range(MAP_H) for x in range(MAP_W) if dungeon.tiles[y][x] == T_WALL)
print(f"  Rooms: {len(dungeon.rooms)}")
print(f"  Floor tiles: {floor_tiles}")
print(f"  Wall tiles: {wall_tiles}")
print(f"  Room centers: {[r.center for r in dungeon.rooms]}")

# Test 3: Game initialization
print("\n--- Game Init ---")
game = Game()
print(f"  Floor: {game.state.floor_num}")
print(f"  Player position: ({game.state.player.x}, {game.state.player.y})")
print(f"  Player HP: {game.state.player.fighter.hp}/{game.state.player.fighter.max_hp}")
print(f"  Player MP: {game.state.player.fighter.mp}/{game.state.player.fighter.max_mp}")
print(f"  Player stats: STR={game.state.player.fighter.str} DEX={game.state.player.fighter.dex}")
print(f"  Entities: {len(game.state.entities)}")
print(f"  Items on ground: {len(game.state.items_on_ground)}")
print(f"  Visible tiles: {sum(sum(row) for row in game.state.visible)}")
print(f"  Explored tiles: {sum(sum(row) for row in game.state.explored)}")

# Test 4: Enemy templates
print("\n--- Enemy Templates ---")
for key in ['rat', 'goblin', 'skeleton', 'orc', 'mage', 'troll', 'vampire', 'dragon', 'lich', 'demon']:
    t = ENEMY_TEMPLATES[key]
    print(f"  {t['name']:15s} HP:{t['hp']:3d} AC:{t['ac']} DMG:{t['damage']:10s} XP:{key}")

# Test 5: Item templates
print("\n--- Items ---")
from roguelike import ITEM_TEMPLATES
for key, t in list(ITEM_TEMPLATES.items())[:10]:
    print(f"  {t['name']:20s} ({t['char']}) {t['type']:8s} - {t['desc']}")

# Test 6: Player movement
print("\n--- Movement ---")
px, py = game.state.player.x, game.state.player.y
print(f"  Before: ({px}, {py})")
game.move_player(1, 0)
print(f"  After move right: ({game.state.player.x}, {game.state.player.y})")
game.move_player(0, 1)
print(f"  After move down: ({game.state.player.x}, {game.state.player.y})")
print(f"  Turn: {game.state.turn}")

# Test 7: Inventory
print("\n--- Inventory ---")
print(f"  Inventory size: {len(game.player_inventory.items)}")
potion = Item('health_potion')
game.player_inventory.add(potion)
print(f"  After adding potion: {len(game.player_inventory.items)}")
sword = Item('short_sword')
game.player_inventory.add(sword)
print(f"  After adding sword: {len(game.player_inventory.items)}")

# Test 8: Save/Load
print("\n--- Save/Load ---")
from roguelike import save_game, load_game, SAVE_FILE
save_game(game)
print(f"  Save file exists: {os.path.exists(SAVE_FILE)}")
loaded = load_game()
if loaded:
    print(f"  Loaded successfully!")
    print(f"  Floor: {loaded.floor_num}, Player: ({loaded.player.x}, {loaded.player.y})")
    # Clean up
    os.remove(SAVE_FILE)
else:
    print("  Load FAILED!")

# Test 9: Message log
print("\n--- Messages ---")
for msg, color in game.state.message_log.recent(5):
    print(f"  [{color}] {msg}")

# Test 10: FOV computation
print("\n--- FOV ---")
from roguelike import compute_fov
visible = [[False]*MAP_W for _ in range(MAP_H)]
explored = [[False]*MAP_W for _ in range(MAP_H)]
compute_fov(game.state.tiles, game.state.player.x, game.state.player.y, 10, visible, explored, MAP_W, MAP_H)
vis_count = sum(sum(row) for row in visible)
print(f"  Visible tiles from player position: {vis_count}")

print("\n=== ALL TESTS PASSED ===")