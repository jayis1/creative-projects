#!/usr/bin/env python3
"""
Terminal Roguelike Engine — A full-featured ASCII dungeon crawler.
Procedural generation, combat, inventory, fog of war, NPCs, boss fights, save/load, and more.
"""

import random
import math
import json
import os
import sys
import copy
import time
from collections import defaultdict

# ─── Constants ───────────────────────────────────────────────────────────────

SCREEN_W = 80
SCREEN_H = 24
MAP_W = 80
MAP_H = 40
FOV_RADIUS = 10
MAX_FLOOR = 5

# Tile types
T_WALL = 0
T_FLOOR = 1
T_DOOR = 2
T_STAIRS = 3
T_WATER = 4
T_TRAP = 5

TILE_CHAR = {T_WALL: '#', T_FLOOR: '.', T_DOOR: '+', T_STAIRS: '>', T_WATER: '~', T_TRAP: '^'}
TILE_COLOR = {
    T_WALL: 'white', T_FLOOR: 'gray', T_DOOR: 'brown',
    T_STAIRS: 'cyan', T_WATER: 'blue', T_TRAP: 'red'
}
TILE_WALKABLE = {T_WALL: False, T_FLOOR: True, T_DOOR: True, T_STAIRS: True, T_WATER: True, T_TRAP: True}
TILE_TRANSPARENT = {T_WALL: False, T_FLOOR: True, T_DOOR: True, T_STAIRS: True, T_WATER: True, T_TRAP: True}

# Colors
COLOR_MAP = {
    'white': '\033[37m', 'gray': '\033[90m', 'brown': '\033[33m',
    'cyan': '\033[36m', 'blue': '\033[34m', 'red': '\033[31m',
    'green': '\033[32m', 'yellow': '\033[33m', 'magenta': '\033[35m',
    'dark_gray': '\033[2m', 'bright_white': '\033[97m',
    'bright_red': '\033[91m', 'bright_green': '\033[92m',
    'bright_blue': '\033[94m', 'bright_cyan': '\033[96m',
    'bright_yellow': '\033[93m', 'bright_magenta': '\033[95m',
}
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# ─── Dice Rolling ────────────────────────────────────────────────────────────

def roll(dice_str):
    """Parse '2d6+1' style dice strings."""
    total = 0
    sign = 1
    for part in dice_str.replace('-', '+-').split('+'):
        part = part.strip()
        if not part:
            continue
        if part.startswith('-'):
            sign = -1
            part = part[1:]
        else:
            sign = 1
        if 'd' in part:
            count, sides = part.split('d')
            count = int(count) if count else 1
            sides = int(sides)
            total += sign * sum(random.randint(1, sides) for _ in range(count))
        else:
            total += sign * int(part)
    return total

# ─── Message Log ─────────────────────────────────────────────────────────────

class MessageLog:
    def __init__(self, max_messages=200):
        self.messages = []
        self.max_messages = max_messages

    def add(self, text, color='white'):
        self.messages.append((text, color))
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def recent(self, n=3):
        return self.messages[-n:] if self.messages else []

# ─── Items ───────────────────────────────────────────────────────────────────

ITEM_TEMPLATES = {
    # Potions
    'health_potion': {'name': 'Health Potion', 'char': '!', 'color': 'bright_red', 'type': 'potion',
                       'desc': 'Restores 2d8 HP', 'effect': 'heal', 'value': '2d8'},
    'mana_potion':   {'name': 'Mana Potion', 'char': '!', 'color': 'bright_blue', 'type': 'potion',
                       'desc': 'Restores 2d6 MP', 'effect': 'mana', 'value': '2d6'},
    'str_potion':    {'name': 'Potion of Might', 'char': '!', 'color': 'bright_yellow', 'type': 'potion',
                       'desc': '+2 STR for this floor', 'effect': 'buff_str', 'value': 2},
    'dex_potion':    {'name': 'Potion of Agility', 'char': '!', 'color': 'bright_green', 'type': 'potion',
                       'desc': '+2 DEX for this floor', 'effect': 'buff_dex', 'value': 2},
    # Scrolls
    'scroll_fire':   {'name': 'Scroll of Fireball', 'char': '?', 'color': 'bright_red', 'type': 'scroll',
                       'desc': '8d6 fire damage in radius 2', 'effect': 'fireball', 'value': '8d6', 'radius': 2},
    'scroll_ice':    {'name': 'Scroll of Blizzard', 'char': '?', 'color': 'bright_cyan', 'type': 'scroll',
                       'desc': '6d6 ice damage, slows enemies', 'effect': 'blizzard', 'value': '6d6', 'radius': 3},
    'scroll_map':    {'name': 'Scroll of Mapping', 'char': '?', 'color': 'bright_white', 'type': 'scroll',
                       'desc': 'Reveals entire floor', 'effect': 'magic_map', 'value': 0},
    'scroll_tele':   {'name': 'Scroll of Teleport', 'char': '?', 'color': 'bright_magenta', 'type': 'scroll',
                       'desc': 'Teleport to random location', 'effect': 'teleport', 'value': 0},
    # Equipment
    'dagger':        {'name': 'Dagger', 'char': ')', 'color': 'gray', 'type': 'weapon',
                       'desc': '1d4 damage', 'damage': '1d4', 'slot': 'weapon', 'bonus': 0},
    'short_sword':   {'name': 'Short Sword', 'char': ')', 'color': 'white', 'type': 'weapon',
                       'desc': '1d6+1 damage', 'damage': '1d6+1', 'slot': 'weapon', 'bonus': 0},
    'long_sword':    {'name': 'Long Sword', 'char': ')', 'color': 'bright_white', 'type': 'weapon',
                       'desc': '1d8+2 damage', 'damage': '1d8+2', 'slot': 'weapon', 'bonus': 0},
    'flame_blade':   {'name': 'Flame Blade', 'char': ')', 'color': 'bright_red', 'type': 'weapon',
                       'desc': '1d8+3 + 1d6 fire', 'damage': '1d8+3', 'slot': 'weapon', 'bonus': 3, 'extra': ('1d6', 'fire')},
    'leather_armor': {'name': 'Leather Armor', 'char': '[', 'color': 'brown', 'type': 'armor',
                       'desc': 'AC +2', 'ac': 2, 'slot': 'body', 'bonus': 0},
    'chain_mail':    {'name': 'Chain Mail', 'char': '[', 'color': 'gray', 'type': 'armor',
                       'desc': 'AC +4', 'ac': 4, 'slot': 'body', 'bonus': 0},
    'plate_armor':   {'name': 'Plate Armor', 'char': '[', 'color': 'white', 'type': 'armor',
                       'desc': 'AC +6, -1 DEX', 'ac': 6, 'slot': 'body', 'bonus': 0, 'dex_penalty': 1},
    'shield':        {'name': 'Shield', 'char': ']', 'color': 'brown', 'type': 'armor',
                       'desc': 'AC +1', 'ac': 1, 'slot': 'offhand', 'bonus': 0},
    'ring_protection': {'name': 'Ring of Protection', 'char': '=', 'color': 'bright_cyan', 'type': 'ring',
                       'desc': 'AC +2', 'ac': 2, 'slot': 'ring', 'bonus': 0},
}

FLOOR_LOOT = {
    1: ['health_potion', 'dagger', 'leather_armor', 'scroll_map'],
    2: ['health_potion', 'mana_potion', 'short_sword', 'leather_armor', 'scroll_fire', 'shield'],
    3: ['health_potion', 'str_potion', 'short_sword', 'chain_mail', 'scroll_fire', 'scroll_ice', 'ring_protection'],
    4: ['mana_potion', 'dex_potion', 'long_sword', 'chain_mail', 'scroll_ice', 'scroll_tele', 'shield'],
    5: ['health_potion', 'mana_potion', 'long_sword', 'plate_armor', 'scroll_fire', 'ring_protection'],
}

class Item:
    _id_counter = 0
    def __init__(self, template_key):
        self.id = Item._id_counter
        Item._id_counter += 1
        t = ITEM_TEMPLATES[template_key]
        self.key = template_key
        self.name = t['name']
        self.char = t['char']
        self.color = t['color']
        self.item_type = t['type']
        self.desc = t['desc']
        self.template = t

    def __repr__(self):
        return f"{self.name}"

# ─── Entities ────────────────────────────────────────────────────────────────

class Fighter:
    def __init__(self, hp, max_hp, mp, max_mp, ac, str_val, dex_val, xp=0, level=1, damage='1d4'):
        self.hp = hp
        self.max_hp = max_hp
        self.mp = mp
        self.max_mp = max_mp
        self.ac = ac
        self.str = str_val
        self.dex = dex_val
        self.xp = xp
        self.level = level
        self.damage = damage
        self.buffs = []  # temporary buffs
        self.extra_damage = None  # extra damage tuple (dice, element)

    def xp_for_next_level(self):
        return self.level * 100

    def gain_xp(self, amount):
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_for_next_level():
            self.xp -= self.xp_for_next_level()
            self.level += 1
            self.max_hp += random.randint(4, 8)
            self.hp = min(self.hp + random.randint(4, 8), self.max_hp)
            self.max_mp += random.randint(2, 4)
            self.str += 1
            self.dex += 1
            leveled = True
        return leveled

ENEMY_TEMPLATES = {
    'rat':        {'name': 'Giant Rat', 'char': 'r', 'color': 'brown', 'hp': 6, 'ac': 0,
                   'str': 4, 'dex': 8, 'damage': '1d3', 'xp': 15, 'behavior': 'wander'},
    'goblin':     {'name': 'Goblin', 'char': 'g', 'color': 'green', 'hp': 12, 'ac': 2,
                   'str': 8, 'dex': 10, 'damage': '1d6', 'xp': 25, 'behavior': 'hunt'},
    'skeleton':   {'name': 'Skeleton', 'char': 's', 'color': 'white', 'hp': 15, 'ac': 4,
                   'str': 10, 'dex': 8, 'damage': '1d6+1', 'xp': 35, 'behavior': 'hunt'},
    'orc':        {'name': 'Orc', 'char': 'o', 'color': 'dark_gray', 'hp': 25, 'ac': 5,
                   'str': 14, 'dex': 6, 'damage': '1d8+2', 'xp': 50, 'behavior': 'hunt'},
    'mage':       {'name': 'Dark Mage', 'char': 'm', 'color': 'bright_magenta', 'hp': 18, 'ac': 3,
                   'str': 6, 'dex': 12, 'damage': '2d4', 'xp': 55, 'behavior': 'cast',
                   'spells': ['fireball', 'slow']},
    'troll':      {'name': 'Troll', 'char': 'T', 'color': 'bright_green', 'hp': 40, 'ac': 4,
                   'str': 18, 'dex': 4, 'damage': '2d6+3', 'xp': 80, 'behavior': 'hunt', 'regen': 3},
    'vampire':    {'name': 'Vampire', 'char': 'V', 'color': 'bright_red', 'hp': 35, 'ac': 5,
                   'str': 14, 'dex': 14, 'damage': '1d8+3', 'xp': 90, 'behavior': 'hunt', 'drain': True},
    'dragon':     {'name': 'Dragon', 'char': 'D', 'color': 'bright_red', 'hp': 100, 'ac': 8,
                   'str': 20, 'dex': 8, 'damage': '3d6+5', 'xp': 300, 'behavior': 'boss',
                   'breath': True},
    'lich':       {'name': 'Lich Lord', 'char': 'L', 'color': 'bright_cyan', 'hp': 80, 'ac': 6,
                   'str': 10, 'dex': 14, 'damage': '2d8+4', 'xp': 400, 'behavior': 'boss',
                   'spells': ['fireball', 'blizzard', 'drain']},
    'demon':      {'name': 'Arch Demon', 'char': '&', 'color': 'bright_red', 'hp': 120, 'ac': 7,
                   'str': 22, 'dex': 12, 'damage': '3d8+6', 'xp': 500, 'behavior': 'boss',
                   'spells': ['fireball', 'drain']},
}

FLOOR_ENEMIES = {
    1: ['rat', 'rat', 'goblin'],
    2: ['goblin', 'goblin', 'skeleton'],
    3: ['skeleton', 'orc', 'mage'],
    4: ['orc', 'troll', 'vampire', 'mage'],
    5: ['troll', 'vampire'],
}

FLOOR_BOSS = {
    5: 'dragon',
}

class Entity:
    _id_counter = 0
    def __init__(self, x, y, name, char, color, blocks=True, fighter=None, ai=None, is_boss=False):
        self.id = Entity._id_counter
        Entity._id_counter += 1
        self.x = x
        self.y = y
        self.name = name
        self.char = char
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        self.ai = ai
        self.is_boss = is_boss
        self.visible = False

    @property
    def alive(self):
        return self.fighter and self.fighter.hp > 0

# ─── AI Behaviors ────────────────────────────────────────────────────────────

class BasicAI:
    def __init__(self, behavior='hunt', template=None):
        self.behavior = behavior
        self.template = template or {}
        self.cooldown = 0

    def take_turn(self, entity, game):
        if not entity.alive:
            return
        f = entity.fighter
        dx = game.state.player.x - entity.x
        dy = game.state.player.y - entity.y
        dist = abs(dx) + abs(dy)

        # Regeneration
        if self.template.get('regen') and entity.alive:
            f.hp = min(f.hp + self.template['regen'], f.max_hp)

        # Boss behaviors
        if self.behavior == 'boss':
            self._boss_turn(entity, game, dx, dy, dist)
            return

        # Mage casting
        if self.behavior == 'cast':
            if dist <= 6 and self.cooldown <= 0:
                self._cast_spell(entity, game)
                self.cooldown = 3
                return
            self.cooldown = max(0, self.cooldown - 1)

        # Move toward player
        if dist <= 1:
            game.attack_entity(entity, game.state.player)
        else:
            self._move_toward(entity, game, dx, dy)

    def _move_toward(self, entity, game, dx, dy):
        # Simple pathfinding: move in the direction that reduces distance
        moves = []
        if dx != 0:
            moves.append((1 if dx > 0 else -1, 0))
        if dy != 0:
            moves.append((0, 1 if dy > 0 else -1))
        # Prefer the axis with greater distance
        if abs(dx) > abs(dy):
            moves.sort(key=lambda m: abs(m[0]) != (1 if dx > 0 else -1) if dx != 0 else 0)
        else:
            moves.sort(key=lambda m: abs(m[1]) != (1 if dy > 0 else -1) if dy != 0 else 0)

        for mx, my in moves:
            nx, ny = entity.x + mx, entity.y + my
            if game.is_walkable(nx, ny) and not game.entity_at(nx, ny):
                entity.x = nx
                entity.y = ny
                return
        # Wander randomly if can't move toward player
        if self.behavior == 'wander' and random.random() < 0.3:
            mx, my = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
            nx, ny = entity.x + mx, entity.y + my
            if game.is_walkable(nx, ny) and not game.entity_at(nx, ny):
                entity.x = nx
                entity.y = ny

    def _boss_turn(self, entity, game, dx, dy, dist):
        # Bosses have special abilities
        if self.template.get('breath') and dist <= 5 and random.random() < 0.3:
            game.message(f"The {entity.name} breathes fire!", 'bright_red')
            dmg = roll('4d6')
            game.damage_player(dmg, "is scorched by dragonfire")
            return
        if self.template.get('spells') and dist <= 5 and random.random() < 0.4:
            spell = random.choice(self.template['spells'])
            self._cast_named(entity, game, spell)
            return
        if dist <= 1:
            game.attack_entity(entity, game.state.player)
        else:
            self._move_toward(entity, game, dx, dy)

    def _cast_spell(self, entity, game):
        if 'spells' not in self.template:
            return
        spell = random.choice(self.template['spells'])
        self._cast_named(entity, game, spell)

    def _cast_named(self, entity, game, spell):
        if spell == 'fireball':
            game.message(f"The {entity.name} casts Fireball!", 'bright_red')
            dmg = roll('3d6')
            game.damage_player(dmg, "is burned by fire")
        elif spell == 'blizzard':
            game.message(f"The {entity.name} casts Blizzard!", 'bright_cyan')
            dmg = roll('2d6')
            game.damage_player(dmg, "is frozen by ice")
        elif spell == 'slow':
            game.message(f"The {entity.name} casts Slow!", 'bright_magenta')
            # Slowness tracked via buff
            game.state.player.fighter.buffs.append(('slow', 5))
        elif spell == 'drain':
            game.message(f"The {entity.name} drains your life!", 'bright_magenta')
            dmg = roll('2d6')
            game.damage_player(dmg, "has life drained")
            entity.fighter.hp = min(entity.fighter.hp + dmg, entity.fighter.max_hp)

class NPCAI:
    def __init__(self, dialogue=None):
        self.dialogue = dialogue or ["Hello, adventurer!", "Beware the depths..."]

    def take_turn(self, entity, game):
        pass  # NPCs don't act aggressively

# ─── Dungeon Generation ─────────────────────────────────────────────────────

class Room:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
        self.w = w
        self.h = h

    @property
    def center(self):
        return (self.x1 + self.w // 2, self.y1 + self.h // 2)

    def intersects(self, other, padding=1):
        return (self.x1 - padding <= other.x2 and self.x2 + padding >= other.x1 and
                self.y1 - padding <= other.y2 and self.y2 + padding >= other.y1)

class DungeonGenerator:
    def __init__(self, width, height, floor_num=1):
        self.width = width
        self.height = height
        self.floor_num = floor_num
        self.tiles = [[T_WALL for _ in range(width)] for _ in range(height)]
        self.rooms = []
        self.explored = [[False] * width for _ in range(height)]
        self.visible = [[False] * width for _ in range(height)]

    def generate(self):
        num_rooms = random.randint(6, 10) + self.floor_num
        for _ in range(50):  # attempts
            if len(self.rooms) >= num_rooms:
                break
            w = random.randint(4, 10)
            h = random.randint(3, 8)
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)
            room = Room(x, y, w, h)
            if any(room.intersects(r) for r in self.rooms):
                continue
            self._carve_room(room)
            if self.rooms:
                self._connect_rooms(self.rooms[-1], room)
            self.rooms.append(room)

        # Place stairs in last room
        last_room = self.rooms[-1]
        cx, cy = last_room.center
        self.tiles[cy][cx] = T_STAIRS

        # Place traps
        for room in self.rooms[1:-1]:
            if random.random() < 0.15 * self.floor_num:
                tx = random.randint(room.x1 + 1, room.x2 - 1)
                ty = random.randint(room.y1 + 1, room.y2 - 1)
                if self.tiles[ty][tx] == T_FLOOR:
                    self.tiles[ty][tx] = T_TRAP

        return self

    def _carve_room(self, room):
        for y in range(room.y1, room.y2):
            for x in range(room.x1, room.x2):
                self.tiles[y][x] = T_FLOOR

    def _connect_rooms(self, room1, room2):
        x1, y1 = room1.center
        x2, y2 = room2.center
        if random.random() < 0.5:
            self._h_corridor(x1, x2, y1)
            self._v_corridor(y1, y2, x2)
        else:
            self._v_corridor(y1, y2, x1)
            self._h_corridor(x1, x2, y2)

    def _h_corridor(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                self.tiles[y][x] = T_FLOOR

    def _v_corridor(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                self.tiles[y][x] = T_FLOOR

# ─── FOV (Field of View) ────────────────────────────────────────────────────

def compute_fov(tiles, px, py, radius, visible, explored, width, height):
    """Simple ray-casting FOV."""
    for y in range(height):
        for x in range(width):
            visible[y][x] = False

    visible[py][px] = True
    explored[py][px] = True

    num_rays = 360
    for i in range(num_rays):
        angle = 2 * math.pi * i / num_rays
        dx = math.cos(angle)
        dy = math.sin(angle)
        for step in range(1, radius + 1):
            rx = px + int(round(dx * step))
            ry = py + int(round(dy * step))
            if rx < 0 or rx >= width or ry < 0 or ry >= height:
                break
            visible[ry][rx] = True
            explored[ry][rx] = True
            if not TILE_TRANSPARENT.get(tiles[ry][rx], True):
                break

# ─── Game State ──────────────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.floor_num = 1
        self.turn = 0
        self.message_log = MessageLog()
        self.entities = []
        self.items_on_ground = []  # list of (x, y, Item)
        self.player = None
        self.dungeon = None
        self.tiles = None
        self.explored = None
        self.visible = None
        self.running = True
        self.game_over = False
        self.victory = False
        self.screen_state = 'game'  # 'game', 'inventory', 'character', 'help', 'look', 'message_log'
        self.look_target = None
        self.log_scroll = 0
        self.player_inventory = None  # set by Game
        self.player_equipment = None  # set by Game

    def message(self, text, color='white'):
        self.message_log.add(text, color)

    def current_enemies(self):
        return [e for e in self.entities if e.alive and e != self.player]

    def entity_at(self, x, y):
        for e in self.entities:
            if e.x == x and e.y == y and e.alive:
                return e
        return None

    def items_at(self, x, y):
        return [(ix, iy, item) for ix, iy, item in self.items_on_ground if ix == x and iy == y]

    def is_walkable(self, x, y):
        if x < 0 or x >= MAP_W or y < 0 or y >= MAP_H:
            return False
        return TILE_WALKABLE.get(self.tiles[y][x], False)

    def is_transparent(self, x, y):
        if x < 0 or x >= MAP_W or y < 0 or y >= MAP_H:
            return False
        return TILE_TRANSPARENT.get(self.tiles[y][x], False)

    def damage_player(self, dmg, msg_text="takes damage"):
        pf = self.player.fighter
        actual_dmg = max(0, dmg - pf.ac)
        pf.hp -= actual_dmg
        self.message(f"You {msg_text} for {actual_dmg} damage!", 'bright_red')
        if pf.hp <= 0:
            pf.hp = 0
            self.game_over = True
            self.message("You have died!", 'bright_red')

    def attack_entity(self, attacker, target):
        af = attacker.fighter
        tf = target.fighter
        # Hit roll
        hit_bonus = af.dex // 2
        ac = tf.ac
        # Calculate total AC including armor
        if target == self.player:
            for slot, item in self.player_equipment.items():
                if item and 'ac' in item.template:
                    ac += item.template['ac']

        dmg = roll(af.damage)
        # Weapon bonus
        if af.extra_damage:
            dmg += roll(af.extra_damage[0])

        # Apply strength bonus for player
        if target == self.player and attacker != self.player:
            pass  # NPC attacking player
        elif attacker == self.player:
            dmg += max(0, (af.str - 10) // 2)

        actual_dmg = max(1, dmg - ac)

        # Drain life for vampires
        if attacker.ai and isinstance(attacker.ai, BasicAI) and attacker.ai.template.get('drain'):
            heal = actual_dmg // 2
            attacker.fighter.hp = min(attacker.fighter.hp + heal, attacker.fighter.max_hp)

        tf.hp -= actual_dmg
        if attacker == self.player:
            self.message(f"You hit the {target.name} for {actual_dmg} damage!", 'bright_green')
        elif target == self.player:
            self.message(f"The {attacker.name} hits you for {actual_dmg} damage!", 'bright_red')
        else:
            self.message(f"The {attacker.name} hits {target.name} for {actual_dmg} damage.", 'white')

        if tf.hp <= 0:
            tf.hp = 0
            if target != self.player:
                self.message(f"The {target.name} is destroyed!", 'bright_yellow')
                xp_gain = tf.xp if hasattr(tf, 'xp') else 10
                leveled = af.gain_xp(xp_gain)
                self.message(f"You gain {xp_gain} XP!", 'cyan')
                if leveled:
                    self.message(f"Level up! You are now level {af.level}!", 'bright_yellow')
                    self.message(f"  HP: {af.max_hp} STR: {af.str} DEX: {af.dex}", 'bright_green')
                # Drop items
                self._drop_loot(target)

    def _drop_loot(self, entity):
        if entity.is_boss:
            # Bosses always drop good loot
            loot_table = ['flame_blade', 'plate_armor', 'health_potion', 'health_potion', 'mana_potion']
            for key in random.sample(loot_table, min(2, len(loot_table))):
                item = Item(key)
                self.items_on_ground.append((entity.x, entity.y, item))
                self.message(f"The {entity.name} drops {item.name}!", 'bright_yellow')
        elif random.random() < 0.3:
            floor_loot = FLOOR_LOOT.get(self.floor_num, FLOOR_LOOT[5])
            key = random.choice(floor_loot)
            item = Item(key)
            self.items_on_ground.append((entity.x, entity.y, item))
            self.message(f"The {entity.name} drops {item.name}.", 'green')

# ─── Inventory & Equipment ───────────────────────────────────────────────────

class Inventory:
    def __init__(self, capacity=26):
        self.items = []
        self.capacity = capacity

    def add(self, item):
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item)
        return True

    def remove(self, item):
        self.items.remove(item)

    def get(self, index):
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

# ─── Save/Load ──────────────────────────────────────────────────────────────

SAVE_FILE = os.path.expanduser('~/.roguelike_save.json')

def save_game(game):
    """Serialize game state to JSON."""
    data = {
        'floor_num': game.state.floor_num,
        'turn': game.state.turn,
        'player': {
            'x': game.state.player.x, 'y': game.state.player.y,
            'hp': game.state.player.fighter.hp, 'max_hp': game.state.player.fighter.max_hp,
            'mp': game.state.player.fighter.mp, 'max_mp': game.state.player.fighter.max_mp,
            'ac': game.state.player.fighter.ac, 'str': game.state.player.fighter.str,
            'dex': game.state.player.fighter.dex, 'xp': game.state.player.fighter.xp,
            'level': game.state.player.fighter.level,
            'damage': game.state.player.fighter.damage,
        },
        'inventory': [{'key': i.key} for i in game.player_inventory.items],
        'equipment': {slot: {'key': i.key} for slot, i in game.player_equipment.items() if i},
        'messages': game.state.message_log.messages[-50:],
        'tiles': game.state.tiles,
        'explored': game.state.explored,
        'entities': [],
        'items_on_ground': [{'x': x, 'y': y, 'key': i.key} for x, y, i in game.state.items_on_ground],
    }
    for e in game.state.entities:
        if e.alive and e != game.state.player:
            data['entities'].append({
                'key': e.ai.template.get('_key', 'goblin') if isinstance(e.ai, BasicAI) else 'goblin',
                'x': e.x, 'y': e.y, 'hp': e.fighter.hp, 'max_hp': e.fighter.max_hp,
                'name': e.name
            })
    try:
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f)
        game.message("Game saved!", 'bright_green')
    except Exception as e:
        game.message(f"Save failed: {e}", 'bright_red')

def load_game():
    """Deserialize game state from JSON."""
    if not os.path.exists(SAVE_FILE):
        return None
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
        game = GameState()
        game.floor_num = data['floor_num']
        game.turn = data['turn']

        # Rebuild dungeon
        dungeon = DungeonGenerator(MAP_W, MAP_H, game.floor_num)
        dungeon.generate()
        game.tiles = dungeon.tiles
        game.explored = data.get('explored', dungeon.explored)
        game.visible = [[False]*MAP_W for _ in range(MAP_H)]

        # Create player
        pd = data['player']
        fighter = Fighter(pd['hp'], pd['max_hp'], pd['mp'], pd['max_mp'],
                         pd['ac'], pd['str'], pd['dex'], pd['xp'], pd['level'], pd['damage'])
        game.player = Entity(pd['x'], pd['y'], 'Player', '@', 'bright_white', fighter=fighter)

        # Inventory
        game.player_inventory = Inventory()
        for item_data in data.get('inventory', []):
            game.player_inventory.add(Item(item_data['key']))

        # Equipment
        game.player_equipment = {}
        for slot, item_data in data.get('equipment', {}).items():
            game.player_equipment[slot] = Item(item_data['key'])

        # Entities
        for ed in data.get('entities', []):
            key = ed.get('key', 'goblin')
            template = ENEMY_TEMPLATES.get(key, ENEMY_TEMPLATES['goblin'])
            ef = Fighter(ed['hp'], ed.get('max_hp', template['hp']), 0, 0,
                        template['ac'], template['str'], template['dex'], 0, 1, template['damage'])
            ai = BasicAI(template.get('behavior', 'hunt'), template)
            ai.template['_key'] = key
            e = Entity(ed['x'], ed['y'], template['name'], template['char'],
                       template['color'], fighter=ef, ai=ai)
            game.entities.append(e)

        # Items on ground
        for item_data in data.get('items_on_ground', []):
            game.items_on_ground.append((item_data['x'], item_data['y'], Item(item_data['key'])))

        # Messages
        for msg, color in data.get('messages', []):
            game.message_log.add(msg, color)

        game.message("Game loaded!", 'bright_green')
        return game
    except Exception as e:
        return None

# ─── Renderer ────────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self):
        self.buf = [[' ' for _ in range(SCREEN_W)] for _ in range(SCREEN_H)]
        self.color_buf = [['white' for _ in range(SCREEN_W)] for _ in range(SCREEN_H)]
        self.bold_buf = [[False for _ in range(SCREEN_W)] for _ in range(SCREEN_H)]

    def clear(self):
        for y in range(SCREEN_H):
            for x in range(SCREEN_W):
                self.buf[y][x] = ' '
                self.color_buf[y][x] = 'white'
                self.bold_buf[y][x] = False

    def put(self, x, y, ch, color='white', bold=False):
        if 0 <= x < SCREEN_W and 0 <= y < SCREEN_H:
            self.buf[y][x] = ch
            self.color_buf[y][x] = color
            self.bold_buf[y][x] = bold

    def write(self, x, y, text, color='white', bold=False):
        for i, ch in enumerate(text):
            self.put(x + i, y, ch, color, bold)

    def render(self):
        sys.stdout.write('\033[H')  # move cursor to top-left
        lines = []
        for y in range(SCREEN_H):
            line = []
            prev_color = None
            prev_bold = False
            for x in range(SCREEN_W):
                color = self.color_buf[y][x]
                bold = self.bold_buf[y][x]
                ch = self.buf[y][x]
                if color != prev_color or bold != prev_bold:
                    line.append(COLOR_MAP.get(color, '\033[37m'))
                    if bold:
                        line.append(BOLD)
                    prev_color = color
                    prev_bold = bold
                line.append(ch)
            line.append(RESET)
            lines.append(''.join(line))
        sys.stdout.write('\n'.join(lines))
        sys.stdout.flush()

    def draw_box(self, x, y, w, h, title=''):
        # Draw border
        self.put(x, y, '┌', 'white', True)
        self.put(x + w - 1, y, '┐', 'white', True)
        self.put(x, y + h - 1, '└', 'white', True)
        self.put(x + w - 1, y + h - 1, '┘', 'white', True)
        for i in range(1, w - 1):
            self.put(x + i, y, '─', 'white', True)
            self.put(x + i, y + h - 1, '─', 'white', True)
        for j in range(1, h - 1):
            self.put(x, y + j, '│', 'white', True)
            self.put(x + w - 1, y + j, '│', 'white', True)
        if title:
            self.write(x + 2, y, f' {title} ', 'bright_white', True)

# ─── Main Game ───────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.state = GameState()
        self.renderer = Renderer()
        self.player_inventory = Inventory()
        self.player_equipment = {}  # slot -> Item
        self.state.player_inventory = self.player_inventory
        self.state.player_equipment = self.player_equipment
        self.view_offset_x = 0
        self.view_offset_y = 0
        self._init_floor()

    def _init_floor(self, floor_num=None):
        if floor_num:
            self.state.floor_num = floor_num
        fn = self.state.floor_num
        dungeon = DungeonGenerator(MAP_W, MAP_H, fn)
        dungeon.generate()
        self.state.tiles = dungeon.tiles
        self.state.explored = dungeon.explored
        self.state.visible = [[False]*MAP_W for _ in range(MAP_H)]
        self.state.entities = []
        self.state.items_on_ground = []

        # Create player if not exists
        if not self.state.player:
            fighter = Fighter(hp=30, max_hp=30, mp=10, max_mp=10, ac=0, str_val=10, dex_val=10, damage='1d4')
            self.state.player = Entity(0, 0, 'Player', '@', 'bright_white', fighter=fighter)

        # Place player in first room
        px, py = dungeon.rooms[0].center
        self.state.player.x = px
        self.state.player.y = py
        self.state.entities.append(self.state.player)

        # Spawn enemies
        enemy_types = FLOOR_ENEMIES.get(fn, FLOOR_ENEMIES[5])
        num_enemies = 8 + fn * 3
        for _ in range(num_enemies):
            room = random.choice(dungeon.rooms[1:])
            ex = random.randint(room.x1 + 1, room.x2 - 1)
            ey = random.randint(room.y1 + 1, room.y2 - 1)
            etype = random.choice(enemy_types)
            template = ENEMY_TEMPLATES[etype]
            ef = Fighter(template['hp'], template['hp'], 0, 0,
                        template['ac'], template['str'], template['dex'], 0, 1, template['damage'])
            ai = BasicAI(template.get('behavior', 'hunt'), template)
            ai.template['_key'] = etype
            e = Entity(ex, ey, template['name'], template['char'], template['color'],
                       fighter=ef, ai=ai)
            self.state.entities.append(e)

        # Spawn boss
        if fn in FLOOR_BOSS:
            boss_key = FLOOR_BOSS[fn]
            template = ENEMY_TEMPLATES[boss_key]
            boss_room = dungeon.rooms[-1]
            bx, by = boss_room.center
            bf = Fighter(template['hp'], template['hp'], 30, 30,
                        template['ac'], template['str'], template['dex'], 0, 1, template['damage'])
            ai = BasicAI(template.get('behavior', 'boss'), template)
            ai.template['_key'] = boss_key
            boss = Entity(bx, by, template['name'], template['char'], template['color'],
                         fighter=bf, ai=ai, is_boss=True)
            self.state.entities.append(boss)

        # Spawn NPC in second room
        if len(dungeon.rooms) > 1 and fn <= 3:
            npc_room = dungeon.rooms[1]
            nx, ny = npc_room.center
            # Don't place on top of enemies
            nf = Fighter(1, 1, 0, 0, 0, 0, 0)
            npc_dialogue = [
                "Welcome, adventurer! Beware the depths below.",
                "I heard there's a terrible dragon on floor 5...",
                "Potions heal, scrolls do magic. Simple, right?",
                "The traps here are nasty - watch your step!",
            ]
            npc = Entity(nx, ny, "Wandering Sage", '@', 'bright_cyan', fighter=nf,
                        ai=NPCAI(npc_dialogue))
            self.state.entities.append(npc)

        # Place items on ground
        floor_loot = FLOOR_LOOT.get(fn, FLOOR_LOOT[5])
        num_items = 4 + fn
        for _ in range(num_items):
            room = random.choice(dungeon.rooms)
            ix = random.randint(room.x1 + 1, room.x2 - 1)
            iy = random.randint(room.y1 + 1, room.y2 - 1)
            item_key = random.choice(floor_loot)
            item = Item(item_key)
            self.state.items_on_ground.append((ix, iy, item))

        self.state.message(f"--- Floor {fn} ---", 'bright_yellow')
        self.compute_fov()

    def compute_fov(self):
        p = self.state.player
        compute_fov(self.state.tiles, p.x, p.y, FOV_RADIUS,
                   self.state.visible, self.state.explored, MAP_W, MAP_H)

    def message(self, text, color='white'):
        self.state.message(text, color)

    def entity_at(self, x, y):
        return self.state.entity_at(x, y)

    def items_at(self, x, y):
        return self.state.items_at(x, y)

    def is_walkable(self, x, y):
        return self.state.is_walkable(x, y)

    def damage_player(self, dmg, msg):
        self.state.damage_player(dmg, msg)

    def attack_entity(self, attacker, target):
        self.state.attack_entity(attacker, target)

    def move_player(self, dx, dy):
        if self.state.game_over:
            return
        p = self.state.player
        nx, ny = p.x + dx, p.y + dy

        # Check for entity to attack
        target = self.entity_at(nx, ny)
        if target and target.alive and target != p:
            self.attack_entity(p, target)
            self.end_turn()
            return

        if not self.is_walkable(nx, ny):
            return

        p.x = nx
        p.y = ny

        # Check for traps
        if self.state.tiles[ny][nx] == T_TRAP:
            dmg = random.randint(2, 5) + self.state.floor_num
            self.message(f"You step on a trap! {dmg} damage!", 'bright_red')
            p.fighter.hp -= dmg
            if p.fighter.hp <= 0:
                p.fighter.hp = 0
                self.state.game_over = True
                self.message("You have died!", 'bright_red')

        # Check for items on ground
        items = self.items_at(nx, ny)
        if items:
            for ix, iy, item in items:
                self.message(f"You see here: {item.name} ({item.char})", item.color)

        # Check for stairs
        if self.state.tiles[ny][nx] == T_STAIRS:
            self.message("You see stairs leading down. Press > to descend.", 'bright_cyan')

        self.end_turn()

    def descend_stairs(self):
        p = self.state.player
        if self.state.tiles[p.y][p.x] == T_STAIRS:
            if self.state.floor_num >= MAX_FLOOR:
                # Victory condition: beat the boss and reach the stairs
                boss_alive = any(e.alive and e.is_boss for e in self.state.entities)
                if boss_alive:
                    self.message("A powerful foe blocks your path! Defeat the boss first!", 'bright_red')
                    return
                self.state.victory = True
                self.state.game_over = True
                self.message("VICTORY! You have conquered the dungeon!", 'bright_yellow')
                return

            # Remove non-player entities
            self.state.entities = [self.state.player]
            self.state.floor_num += 1
            self._init_floor(self.state.floor_num)
            # Remove buff effects from previous floor
            p.fighter.buffs = []

    def pickup_item(self):
        p = self.state.player
        items = self.items_at(p.x, p.y)
        if not items:
            self.message("There's nothing to pick up here.", 'gray')
            return
        for ix, iy, item in items[:1]:  # Pick up first item
            if self.player_inventory.add(item):
                self.state.items_on_ground.remove((ix, iy, item))
                self.message(f"You pick up {item.name}.", 'bright_green')
                # Auto-equip if slot is empty
                if item.item_type in ('weapon', 'armor', 'ring'):
                    slot = item.template.get('slot', None)
                    if slot and slot not in self.player_equipment:
                        self.equip_item(item)
                self.end_turn()
                return
            else:
                self.message("Your inventory is full!", 'bright_red')
                return

    def equip_item(self, item):
        if item.item_type not in ('weapon', 'armor', 'ring'):
            self.message(f"Cannot equip {item.name}.", 'red')
            return
        slot = item.template.get('slot', 'weapon')
        if slot in self.player_equipment:
            old = self.player_equipment[slot]
            self.message(f"You unequip {old.name}.", 'yellow')
        self.player_equipment[slot] = item
        self.player_inventory.items.remove(item)
        if slot in self.player_equipment and self.player_equipment[slot] == item:
            pass  # Already equipped
        # Update player damage
        if item.item_type == 'weapon':
            self.state.player.fighter.damage = item.template.get('damage', '1d4')
            self.state.player.fighter.extra_damage = item.template.get('extra', None)
        self.message(f"You equip {item.name}.", 'bright_green')

    def unequip_item(self, item):
        for slot, equipped in list(self.player_equipment.items()):
            if equipped == item:
                del self.player_equipment[slot]
                self.player_inventory.items.append(item)
                if item.item_type == 'weapon':
                    self.state.player.fighter.damage = '1d4'
                    self.state.player.fighter.extra_damage = None
                self.message(f"You unequip {item.name}.", 'yellow')
                return

    def use_item(self, item):
        if item.item_type == 'potion':
            self._use_potion(item)
        elif item.item_type == 'scroll':
            self._use_scroll(item)
        else:
            self.message(f"Cannot use {item.name} like that.", 'red')
            return
        self.player_inventory.remove(item)
        self.end_turn()

    def _use_potion(self, item):
        t = item.template
        p = self.state.player
        if t['effect'] == 'heal':
            amount = roll(t['value'])
            p.fighter.hp = min(p.fighter.hp + amount, p.fighter.max_hp)
            self.message(f"You drink {item.name}. Restored {amount} HP!", 'bright_green')
        elif t['effect'] == 'mana':
            amount = roll(t['value'])
            p.fighter.mp = min(p.fighter.mp + amount, p.fighter.max_mp)
            self.message(f"You drink {item.name}. Restored {amount} MP!", 'bright_blue')
        elif t['effect'] == 'buff_str':
            p.fighter.buffs.append(('str', 50))
            p.fighter.str += t['value']
            self.message(f"You drink {item.name}. STR +{t['value']}!", 'bright_yellow')
        elif t['effect'] == 'buff_dex':
            p.fighter.buffs.append(('dex', 50))
            p.fighter.dex += t['value']
            self.message(f"You drink {item.name}. DEX +{t['value']}!", 'bright_green')

    def _use_scroll(self, item):
        t = item.template
        p = self.state.player
        if t['effect'] == 'magic_map':
            for y in range(MAP_H):
                for x in range(MAP_W):
                    self.state.explored[y][x] = True
            self.message("The scroll reveals the entire floor!", 'bright_cyan')
        elif t['effect'] == 'teleport':
            # Find random walkable tile
            for _ in range(100):
                x = random.randint(0, MAP_W - 1)
                y = random.randint(0, MAP_H - 1)
                if self.is_walkable(x, y) and not self.entity_at(x, y):
                    p.x = x
                    p.y = y
                    self.message("You teleport to a new location!", 'bright_magenta')
                    self.compute_fov()
                    return
            self.message("Teleportation failed!", 'red')
        elif t['effect'] in ('fireball', 'blizzard'):
            radius = t.get('radius', 2)
            dmg = roll(t['value'])
            self.message(f"You cast {item.name}! ({radius} tile radius, {dmg} damage)", 'bright_red')
            for e in self.state.entities[:]:
                if e == p or not e.alive:
                    continue
                dx = abs(e.x - p.x)
                dy = abs(e.y - p.y)
                if dx <= radius and dy <= radius:
                    actual_dmg = max(1, dmg - e.fighter.ac)
                    e.fighter.hp -= actual_dmg
                    self.message(f"The {e.name} takes {actual_dmg} damage!", 'bright_yellow')
                    if e.fighter.hp <= 0:
                        e.fighter.hp = 0
                        self.message(f"The {e.name} is destroyed!", 'bright_yellow')
                        self._drop_loot(e)
                        # Give XP
                        xp_gain = e.ai.template.get('xp', 25) if isinstance(e.ai, BasicAI) else 25
                        leveled = p.fighter.gain_xp(xp_gain)
                        self.message(f"You gain {xp_gain} XP!", 'cyan')
                        if leveled:
                            self.message(f"Level up! You are now level {p.fighter.level}!", 'bright_yellow')

    def _drop_loot(self, entity):
        self.state._drop_loot(entity)

    def end_turn(self):
        self.state.turn += 1
        # Process buffs - decrement duration
        p = self.state.player
        new_buffs = []
        for buff_name, duration in p.fighter.buffs:
            if duration > 1:
                new_buffs.append((buff_name, duration - 1))
            else:
                # Buff expired
                if buff_name == 'str':
                    p.fighter.str -= 2
                    self.message("Your strength returns to normal.", 'yellow')
                elif buff_name == 'dex':
                    p.fighter.dex -= 2
                    self.message("Your agility returns to normal.", 'yellow')
                elif buff_name == 'slow':
                    pass  # slow expired
        p.fighter.buffs = new_buffs

        # Remove dead entities
        self.state.entities = [e for e in self.state.entities if e == p or e.alive]

        # Enemy turns
        for e in self.state.entities[:]:
            if e == p or not e.alive or not e.ai:
                continue
            # Only act if visible or close
            dist = abs(e.x - p.x) + abs(e.y - p.y)
            if dist <= FOV_RADIUS + 5:
                # Slow check for player
                is_slow = any(b[0] == 'slow' for b in p.fighter.buffs)
                e.ai.take_turn(e, self)

        self.compute_fov()

    def handle_input(self, key):
        if self.state.screen_state == 'game':
            return self._handle_game_input(key)
        elif self.state.screen_state == 'inventory':
            return self._handle_inventory_input(key)
        elif self.state.screen_state == 'character':
            return self._handle_character_input(key)
        elif self.state.screen_state == 'help':
            return self._handle_help_input(key)
        elif self.state.screen_state == 'look':
            return self._handle_look_input(key)
        elif self.state.screen_state == 'message_log':
            return self._handle_log_input(key)
        return True

    def _handle_game_input(self, key):
        if self.state.game_over:
            if key in ('q', 'Q'):
                self.state.running = False
                return False
            return True

        # Movement
        move_map = {
            'h': (-1, 0), 'j': (0, 1), 'k': (0, -1), 'l': (1, 0),
            'y': (-1, -1), 'u': (1, -1), 'b': (-1, 1), 'n': (1, 1),
            '4': (-1, 0), '2': (0, 1), '8': (0, -1), '6': (1, 0),
            '7': (-1, -1), '9': (1, -1), '1': (-1, 1), '3': (1, 1),
        }
        if key in move_map:
            dx, dy = move_map[key]
            self.move_player(dx, dy)
        elif key == 'g':
            self.pickup_item()
        elif key == '.':
            # Wait a turn
            self.message("You wait...", 'gray')
            self.end_turn()
        elif key == 'i':
            self.state.screen_state = 'inventory'
        elif key == 'c':
            self.state.screen_state = 'character'
        elif key == '?':
            self.state.screen_state = 'help'
        elif key == 'x':
            self.state.look_target = [self.state.player.x, self.state.player.y]
            self.state.screen_state = 'look'
        elif key == 'm':
            self.state.screen_state = 'message_log'
            self.state.log_scroll = 0
        elif key == 'S':
            save_game(self)
        elif key == 'L':
            # Handled externally
            pass
        elif key == '>':
            self.descend_stairs()
        elif key == 'q':
            self.state.running = False
            return False
        return True

    def _handle_inventory_input(self, key):
        if key == '\x1b' or key == 'i' or key == 'q':
            self.state.screen_state = 'game'
            return True
        if key in 'abcdefghijklmnopqrstuvwxyz':
            idx = ord(key) - ord('a')
            item = self.player_inventory.get(idx)
            if item:
                self.use_item(item)
                self.state.screen_state = 'game'
            return True
        if key == 'e':
            # Enter equip mode
            idx = 0
            # Show numbered list and pick
            self.state.screen_state = 'game'
            return True
        return True

    def _handle_character_input(self, key):
        if key == '\x1b' or key == 'c' or key == 'q':
            self.state.screen_state = 'game'
        return True

    def _handle_help_input(self, key):
        if key == '\x1b' or key == '?' or key == 'q':
            self.state.screen_state = 'game'
        return True

    def _handle_look_input(self, key):
        move_map = {
            'h': (-1, 0), 'j': (0, 1), 'k': (0, -1), 'l': (1, 0),
            'y': (-1, -1), 'u': (1, -1), 'b': (-1, 1), 'n': (1, 1),
        }
        if key == '\x1b' or key == 'x' or key == 'q':
            self.state.screen_state = 'game'
        elif key in move_map:
            dx, dy = move_map[key]
            self.state.look_target[0] += dx
            self.state.look_target[1] += dy
        return True

    def _handle_log_input(self, key):
        if key == '\x1b' or key == 'm' or key == 'q':
            self.state.screen_state = 'game'
        elif key == 'j' or key == '2':
            self.state.log_scroll += 1
        elif key == 'k' or key == '8':
            self.state.log_scroll = max(0, self.state.log_scroll - 1)
        return True

    # ─── Drawing ─────────────────────────────────────────────────────────────

    def draw(self):
        self.renderer.clear()
        p = self.state.player

        # Calculate viewport offset
        vp_x = p.x - SCREEN_W // 2
        vp_y = p.y - (SCREEN_H - 6) // 2
        self.view_offset_x = vp_x
        self.view_offset_y = vp_y

        # Draw map (lines 0 to SCREEN_H-7)
        map_h = SCREEN_H - 6
        for sy in range(map_h):
            for sx in range(SCREEN_W):
                mx = vp_x + sx
                my = vp_y + sy
                if mx < 0 or mx >= MAP_W or my < 0 or my >= MAP_H:
                    self.renderer.put(sx, sy, ' ', 'dark_gray')
                    continue
                if self.state.visible[my][mx]:
                    tile = self.state.tiles[my][mx]
                    ch = TILE_CHAR.get(tile, ' ')
                    color = TILE_COLOR.get(tile, 'white')
                    # Check for entities
                    entity = self.entity_at(mx, my)
                    if entity and entity != p:
                        ch = entity.char
                        color = entity.color
                        if entity.is_boss:
                            color = color.replace('bright_', '') if random.random() > 0.3 else color
                    elif entity == p:
                        continue  # drawn separately
                    # Check for items
                    elif not entity:
                        items = self.items_at(mx, my)
                        if items:
                            item = items[0][2]
                            ch = item.char
                            color = item.color
                    self.renderer.put(sx, sy, ch, color)
                elif self.state.explored[my][mx]:
                    tile = self.state.tiles[my][mx]
                    ch = TILE_CHAR.get(tile, ' ')
                    self.renderer.put(sx, sy, ch, 'dark_gray')
                else:
                    self.renderer.put(sx, sy, ' ', 'dark_gray')

        # Draw look cursor
        if self.state.screen_state == 'look' and self.state.look_target:
            lx, ly = self.state.look_target
            sx = lx - vp_x
            sy = ly - vp_y
            if 0 <= sx < SCREEN_W and 0 <= sy < map_h:
                # Flash the cursor
                entity = self.entity_at(lx, ly)
                items = self.items_at(lx, ly)
                desc = TILE_CHAR.get(self.state.tiles[ly][lx], '?') if 0 <= lx < MAP_W and 0 <= ly < MAP_H else '?'
                if entity and entity != p:
                    desc = entity.name
                elif items:
                    desc = items[0][2].name
                self.renderer.put(sx, sy, 'X', 'bright_yellow', True)

        # Draw player
        px_screen = p.x - vp_x
        py_screen = p.y - vp_y
        if 0 <= px_screen < SCREEN_W and 0 <= py_screen < map_h:
            self.renderer.put(px_screen, py_screen, '@', 'bright_yellow', True)

        # ─── Status bar ─────────────────────────────────────────────────
        status_y = SCREEN_H - 6

        # HP bar
        hp_pct = p.fighter.hp / p.fighter.max_hp if p.fighter.max_hp > 0 else 0
        hp_color = 'bright_green' if hp_pct > 0.5 else 'bright_yellow' if hp_pct > 0.25 else 'bright_red'
        bar_len = 20
        hp_bar = '█' * int(bar_len * hp_pct) + '░' * (bar_len - int(bar_len * hp_pct))
        self.renderer.write(0, status_y, f"HP: {hp_bar} {p.fighter.hp}/{p.fighter.max_hp}", hp_color)

        # MP bar
        mp_pct = p.fighter.mp / p.fighter.max_mp if p.fighter.max_mp > 0 else 0
        mp_bar_len = 12
        mp_bar = '█' * int(mp_bar_len * mp_pct) + '░' * (mp_bar_len - int(mp_bar_len * mp_pct))
        self.renderer.write(0, status_y + 1, f"MP: {mp_bar} {p.fighter.mp}/{p.fighter.max_mp}", 'bright_blue')

        # Stats
        ac = p.fighter.ac
        for slot, item in self.player_equipment.items():
            if item and 'ac' in item.template:
                ac += item.template['ac']
        self.renderer.write(40, status_y,
            f"STR:{p.fighter.str} DEX:{p.fighter.dex} AC:{ac}", 'white')
        self.renderer.write(40, status_y + 1,
            f"Lv:{p.fighter.level} XP:{p.fighter.xp}/{p.fighter.xp_for_next_level()} Floor:{self.state.floor_num}", 'white')

        # Equipped weapon
        wpn = self.player_equipment.get('weapon', None)
        wpn_name = wpn.name if wpn else 'bare fists'
        self.renderer.write(0, status_y + 2, f"Weapon: {wpn_name}", 'white')

        # Buffs
        buff_str = ' '.join(f"[{b[0].upper()}:{b[1]}]" for b in p.fighter.buffs)
        if buff_str:
            self.renderer.write(40, status_y + 2, buff_str, 'bright_yellow')

        # Separator
        self.renderer.write(0, status_y + 3, '─' * SCREEN_W, 'dark_gray')

        # Messages
        messages = self.state.message_log.recent(2)
        for i, (msg, color) in enumerate(messages):
            self.renderer.write(0, status_y + 4 + i, msg[:SCREEN_W], color)

        # ─── Overlay screens ────────────────────────────────────────────
        if self.state.screen_state == 'inventory':
            self._draw_inventory()
        elif self.state.screen_state == 'character':
            self._draw_character()
        elif self.state.screen_state == 'help':
            self._draw_help()
        elif self.state.screen_state == 'look':
            self._draw_look_info()
        elif self.state.screen_state == 'message_log':
            self._draw_message_log()

        # Game over overlay
        if self.state.game_over:
            if self.state.victory:
                self.renderer.draw_box(15, 6, 50, 12, "VICTORY")
                self.renderer.write(18, 8, "You have conquered the dungeon!", 'bright_yellow', True)
                self.renderer.write(18, 9, f"Final Level: {p.fighter.level}", 'bright_white')
                self.renderer.write(18, 10, f"Turns: {self.state.turn}", 'white')
                self.renderer.write(18, 12, "Press Q to quit", 'gray')
            else:
                self.renderer.draw_box(15, 6, 50, 12, "GAME OVER")
                self.renderer.write(18, 8, "You have perished in the dungeon!", 'bright_red', True)
                self.renderer.write(18, 9, f"Reached Floor: {self.state.floor_num}", 'white')
                self.renderer.write(18, 10, f"Level: {p.fighter.level}  Turns: {self.state.turn}", 'white')
                self.renderer.write(18, 12, "Press Q to quit", 'gray')

        self.renderer.render()

    def _draw_inventory(self):
        self.renderer.draw_box(10, 2, 60, 18, "INVENTORY")
        inv = self.player_inventory
        y = 4
        self.renderer.write(13, y, "Items (press letter to use/equip):", 'bright_white')
        y += 2
        if not inv.items:
            self.renderer.write(13, y, "  (empty)", 'gray')
        else:
            for i, item in enumerate(inv.items):
                letter = chr(ord('a') + i)
                color = item.color
                equipped = ""
                for slot, eq in self.player_equipment.items():
                    if eq == item:
                        equipped = f" [{slot}]"
                        color = 'bright_green'
                        break
                line = f" {letter}) {item.char} {item.name}{equipped} - {item.desc}"
                self.renderer.write(13, y, line[:55], color)
                y += 1

        y += 1
        self.renderer.write(13, y, "Equipment:", 'bright_white')
        y += 1
        for slot in ['weapon', 'body', 'offhand', 'ring']:
            item = self.player_equipment.get(slot)
            if item:
                self.renderer.write(15, y, f"{slot}: {item.name} ({item.desc})", 'bright_green')
            else:
                self.renderer.write(15, y, f"{slot}: (empty)", 'gray')
            y += 1

        self.renderer.write(13, y + 1, "Press ESC or i to close", 'dark_gray')

    def _draw_character(self):
        self.renderer.draw_box(10, 2, 60, 16, "CHARACTER")
        p = self.state.player
        f = p.fighter
        y = 4
        ac = f.ac
        for slot, item in self.player_equipment.items():
            if item and 'ac' in item.template:
                ac += item.template['ac']
        lines = [
            (f"Name: Adventurer    Class: Hero    Level: {f.level}", 'bright_white'),
            (f"HP: {f.hp}/{f.max_hp}    MP: {f.mp}/{f.max_mp}    AC: {ac}", 'white'),
            (f"STR: {f.str}    DEX: {f.dex}    Damage: {f.damage}", 'white'),
            (f"XP: {f.xp}/{f.xp_for_next_level()}    Floor: {self.state.floor_num}    Turn: {self.state.turn}", 'white'),
            ("", 'white'),
            ("Equipment:", 'bright_white'),
        ]
        for slot in ['weapon', 'body', 'offhand', 'ring']:
            item = self.player_equipment.get(slot)
            if item:
                lines.append((f"  {slot}: {item.name} ({item.desc})", 'bright_green'))
            else:
                lines.append((f"  {slot}: (empty)", 'gray'))

        for i, (text, color) in enumerate(lines):
            self.renderer.write(13, y + i, text[:55], color)
        self.renderer.write(13, y + len(lines) + 1, "Press ESC or c to close", 'dark_gray')

    def _draw_help(self):
        self.renderer.draw_box(5, 1, 70, 20, "HELP")
        y = 3
        help_lines = [
            ("MOVEMENT", 'bright_white', True),
            ("h/j/k/l  - Move left/down/up/right", 'white', False),
            ("y/u/b/n  - Move diagonally", 'white', False),
            ("", 'white', False),
            ("ACTIONS", 'bright_white', True),
            ("g        - Pick up item", 'white', False),
            (">        - Descend stairs", 'white', False),
            (".        - Wait a turn", 'white', False),
            ("", 'white', False),
            ("INTERFACE", 'bright_white', True),
            ("i        - Inventory", 'white', False),
            ("c        - Character sheet", 'white', False),
            ("x        - Look mode", 'white', False),
            ("m        - Message log", 'white', False),
            ("?        - This help", 'white', False),
            ("", 'white', False),
            ("SAVE/QUIT", 'bright_white', True),
            ("S        - Save game    Q - Quit", 'white', False),
        ]
        for text, color, bold in help_lines:
            self.renderer.write(8, y, text[:63], color, bold)
            y += 1

    def _draw_look_info(self):
        if not self.state.look_target:
            return
        lx, ly = self.state.look_target
        entity = self.entity_at(lx, ly) if 0 <= lx < MAP_W and 0 <= ly < MAP_H else None
        items = self.items_at(lx, ly) if 0 <= lx < MAP_W and 0 <= ly < MAP_H else []

        y = SCREEN_H - 8
        if entity and entity != self.state.player:
            f = entity.fighter
            self.renderer.write(0, y, f"{entity.name} HP:{f.hp}/{f.max_hp} AC:{f.ac}", entity.color, True)
        elif items:
            names = ', '.join(i.name for _, _, i in items)
            self.renderer.write(0, y, f"You see: {names}", 'white')
        elif 0 <= lx < MAP_W and 0 <= ly < MAP_H:
            tile = self.state.tiles[ly][lx]
            tile_name = {T_WALL: 'Wall', T_FLOOR: 'Floor', T_DOOR: 'Door',
                        T_STAIRS: 'Stairs down', T_WATER: 'Water', T_TRAP: 'Trap'}
            name = tile_name.get(tile, 'Unknown')
            self.renderer.write(0, y, f"({lx},{ly}): {name}", 'gray')

    def _draw_message_log(self):
        self.renderer.draw_box(2, 1, 76, 20, "MESSAGE LOG")
        messages = self.state.message_log.messages
        start = max(0, len(messages) - 17 - self.state.log_scroll)
        end = max(0, len(messages) - self.state.log_scroll)
        y = 3
        for text, color in messages[start:end]:
            self.renderer.write(4, y, text[:72], color)
            y += 1
            if y >= 20:
                break
        self.renderer.write(4, 21, "j/k=scroll  ESC=close", 'dark_gray')

# ─── Input Handling ──────────────────────────────────────────────────────────

def get_key():
    """Read a single keypress without waiting for Enter."""
    import tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            # Read rest of escape sequence
            import select
            if select.select([sys.stdin], [], [], 0.05)[0]:
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    arrow_map = {'A': 'k', 'B': 'j', 'C': 'l', 'D': 'h'}
                    return arrow_map.get(ch3, '\x1b')
            return '\x1b'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# ─── Title Screen ────────────────────────────────────────────────────────────

def draw_title(renderer):
    renderer.clear()
    title_lines = [
        "████████╗███████╗██████╗ ███╗   ███╗",
        "╚══██╔══╝██╔════╝██╔══██╗████╗ ████║",
        "   ██║   █████╗  ██████╔╝██╔████╔██║",
        "   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║",
        "   ██║   ███████╗██║  ██║██║ ╚═╝ ██║",
        "   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝",
    ]
    y = 4
    for line in title_lines:
        x = (SCREEN_W - len(line)) // 2
        renderer.write(x, y, line, 'bright_cyan', True)
        y += 1

    renderer.write(15, y + 2, "A Terminal Dungeon Crawler", 'bright_white', True)
    renderer.write(20, y + 4, "Press any key to start", 'yellow')
    renderer.write(20, y + 6, "L = Load saved game", 'gray')
    renderer.write(20, y + 7, "Q = Quit", 'gray')

    # Draw some decorative walls
    for x in range(SCREEN_W):
        renderer.put(x, 0, '#', 'dark_gray')
        renderer.put(x, SCREEN_H - 1, '#', 'dark_gray')
    for y in range(SCREEN_H):
        renderer.put(0, y, '#', 'dark_gray')
        renderer.put(SCREEN_W - 1, y, '#', 'dark_gray')

    renderer.render()

# ─── Main Loop ───────────────────────────────────────────────────────────────

def main():
    # Hide cursor
    sys.stdout.write('\033[?25l')
    sys.stdout.write('\033[2J')  # Clear screen

    game = Game()

    # Title screen
    draw_title(game.renderer)
    key = get_key()
    if key == 'Q' or key == 'q':
        sys.stdout.write('\033[?25h')
        sys.stdout.write('\033[2J\033[H')
        print("Thanks for playing!")
        return
    if key == 'L' or key == 'l':
        loaded = load_game()
        if loaded:
            game.state = loaded
            # Transfer inventory and equipment from loaded state
            game.player_inventory = loaded.player_inventory if loaded.player_inventory else Inventory()
            game.player_equipment = loaded.player_equipment if loaded.player_equipment else {}
            # Sync references
            game.state.player_inventory = game.player_inventory
            game.state.player_equipment = game.player_equipment
            # Add player entity to entities list
            if game.state.player not in game.state.entities:
                game.state.entities.insert(0, game.state.player)
            game.compute_fov()
        else:
            game.message("No save file found. Starting new game.", 'bright_red')

    game.message("Welcome to the Dungeon of Shadows!", 'bright_yellow')
    game.message("Press ? for help. Survive and conquer!", 'bright_cyan')

    try:
        while game.state.running:
            game.draw()
            key = get_key()
            if key == '\x03':  # Ctrl-C
                break
            game.handle_input(key)

    finally:
        # Show cursor and clear
        sys.stdout.write('\033[?25h')
        sys.stdout.write('\033[2J\033[H')
        print("Thanks for playing Dungeon of Shadows!")
        print(f"Final stats: Floor {game.state.floor_num}, Level {game.state.player.fighter.level}, "
              f"Turn {game.state.turn}")

if __name__ == '__main__':
    main()