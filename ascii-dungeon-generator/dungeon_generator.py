#!/usr/bin/env python3
"""
Procedural ASCII Dungeon Map Generator

Generates random dungeon maps with rooms, corridors, monsters,
treasures, traps, NPCs, and exits. Supports multiple themes,
difficulty levels, JSON export, and fog-of-war reveal mode.
"""

import random
import math
import argparse
import json
import sys
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Set

__version__ = "1.1.0"

# ── Tile types ──────────────────────────────────────────────────────
WALL = 0
FLOOR = 1
CORRIDOR = 2
DOOR = 3
STAIRS_DOWN = 4
STAIRS_UP = 5
WATER = 6
PILLAR = 7

TILE_CHARS = {
    WALL: "█",
    FLOOR: "·",
    CORRIDOR: "·",
    DOOR: "+",
    STAIRS_DOWN: "▼",
    STAIRS_UP: "▲",
    WATER: "~",
    PILLAR: "○",
}

TILE_NAMES = {
    WALL: "wall",
    FLOOR: "floor",
    CORRIDOR: "corridor",
    DOOR: "door",
    STAIRS_DOWN: "stairs_down",
    STAIRS_UP: "stairs_up",
    WATER: "water",
    PILLAR: "pillar",
}

# ── Entity types ────────────────────────────────────────────────────
MONSTER_CHARS = {
    "crypt":    ["z", "s", "g", "W", "V", "Z"],
    "inferno":  ["i", "d", "f", "D", "I", "F"],
    "forest":   ["w", "k", "a", "S", "T", "A"],
    "aquatic":  ["m", "e", "p", "M", "E", "P"],
    "standard": ["r", "b", "o", "R", "B", "O"],
}

MONSTER_NAMES = {
    "crypt":    {"z": "Zombie", "s": "Skeleton", "g": "Ghost",
                 "W": "Wraith", "V": "Vampire", "Z": "Lich"},
    "inferno":  {"i": "Imp", "d": "Demon", "f": "Fire Elemental",
                 "D": "Devil", "I": "Infernal", "F": "Fire Lord"},
    "forest":   {"w": "Wolf", "k": "Kobold", "a": "Arachnid",
                 "S": "Spider Queen", "T": "Treant", "A": "Arch-druid"},
    "aquatic":  {"m": "Murloc", "e": "Eel", "p": "Piranha",
                 "M": "Merfolk", "E": "Electric Eel", "P": "Kraken"},
    "standard": {"r": "Rat", "b": "Bat", "o": "Orc",
                 "R": "Rock Golem", "B": "Bear", "O": "Ogre"},
}

NPC_CHARS = ["@", "♠", "♣", "☎"]
NPC_NAMES = {
    "crypt":    ["Gravedigger", "Lost Soul", "Cultist", "Sage"],
    "inferno":  ["Blacksmith", "Firekeeper", "Hermit", "Oracle"],
    "forest":   ["Ranger", "Druid", "Woodcutter", "Fairy"],
    "aquatic":  ["Fisher", "Pearl Diver", "Lighthouse Keeper", "Merchant"],
    "standard": ["Merchant", "Innkeeper", "Guard", "Sage"],
}
NPC_DIALOGUE = {
    "crypt":    [
        "The dead walk these halls... be careful.",
        "I've seen a lich deeper in. Don't go that way.",
        "There's treasure here, but at what cost?",
        "The crypt whispers secrets to those who listen.",
    ],
    "inferno":  [
        "The heat gets worse the deeper you go.",
        "I've forged weapons that can fell a devil.",
        "Watch your step — lava flows beneath the stone.",
        "The fire reveals truth, but also burns.",
    ],
    "forest":   [
        "The trees have eyes here. Stay on the path.",
        "I know a shortcut through the western grove.",
        "The forest provides, if you know where to look.",
        "Beware the spider queen's web.",
    ],
    "aquatic":  [
        "The tides shift the corridors below.",
        "I trade pearls for gold — fair exchange.",
        "Don't drink the water. Trust me.",
        "Something stirs in the deep pools.",
    ],
    "standard": [
        "Welcome, adventurer! Mind the traps.",
        "I sell potions — could save your life down there.",
        "Heard rumors of a great treasure below.",
        "The stairs down lead to danger... and glory.",
    ],
}

TREASURE_CHARS = ["*", "♦", "✦", "♥"]
TREASURE_NAMES = {
    "*": "Gold coins",
    "♦": "Gem",
    "✦": "Magic scroll",
    "♥": "Potion",
}

TRAP_CHARS = ["^", "×", "!", "?"]
TRAP_NAMES = {
    "^": "Spike trap",
    "×": "Poison gas",
    "!": "Pit trap",
    "?": "Illusion",
}

THEME_WALL = {
    "crypt":    "█",
    "inferno":  "▓",
    "forest":   "▒",
    "aquatic":  "░",
    "standard": "█",
}

THEME_FLOOR = {
    "crypt":    "·",
    "inferno":  "≈",
    "forest":   "░",
    "aquatic":  "~",
    "standard": "·",
}

# ── Room name generation ────────────────────────────────────────────
ROOM_PREFIXES = {
    "crypt":    ["Dark", "Forgotten", "Cursed", "Silent", "Bleak", "Ancient", "Hollow"],
    "inferno":  ["Burning", "Scorched", "Molten", "Ashen", "Blazing", "Ember", "Smoke"],
    "forest":   ["Mossy", "Verdant", "Twisted", "Wild", "Overgrown", "Shaded", "Thorned"],
    "aquatic":  ["Flooded", "Damp", "Submerged", "Tidal", "Brine", "Coral", "Misty"],
    "standard": ["Grand", "Hidden", "Old", "Cold", "Twisted", "Gloomy", "Silent"],
}
ROOM_SUFFIXES = {
    "crypt":    ["Crypt", "Tomb", "Chamber", "Vault", "Sanctum", "Catacomb", "Sepulcher"],
    "inferno":  ["Forge", "Pit", "Cavern", "Chamber", "Hellgate", "Crucible", "Ashpit"],
    "forest":   ["Grove", "Den", "Hollow", "Clearing", "Thicket", "Nest", "Bower"],
    "aquatic":  ["Grotto", "Pool", "Cistern", "Basin", "Spring", "Well", "Reef"],
    "standard": ["Hall", "Room", "Chamber", "Cell", "Gallery", "Passage", "Antechamber"],
}


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int
    room_id: int = 0
    name: str = ""

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def area(self) -> int:
        return self.w * self.h


@dataclass
class Entity:
    x: int
    y: int
    char: str
    kind: str  # "monster", "treasure", "trap", "npc"
    description: str = ""
    hp: int = 0
    gold_value: int = 0
    room_id: int = -1
    dialogue: str = ""


@dataclass
class DungeonConfig:
    width: int = 60
    height: int = 30
    min_rooms: int = 5
    max_rooms: int = 12
    min_room_size: int = 3
    max_room_size: int = 8
    corridor_width: int = 1
    theme: str = "standard"
    difficulty: int = 1  # 1-5
    seed: Optional[int] = None
    add_water: bool = True
    add_pillars: bool = True
    add_traps: bool = True
    add_doors: bool = True
    add_npcs: bool = True


class DungeonGenerator:
    """Procedural ASCII dungeon map generator.

    Generates dungeons with rooms connected by corridors, populated
    with monsters, treasures, traps, NPCs, and decorative features.
    Supports multiple themes, difficulty levels, and JSON export.
    """

    def __init__(self, config: DungeonConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.grid: List[List[int]] = []
        self.rooms: List[Room] = []
        self.entities: List[Entity] = []
        self.room_id_counter = 0

    def _init_grid(self):
        """Initialize the grid with all wall tiles."""
        self.grid = [[WALL for _ in range(self.config.width)]
                     for _ in range(self.config.height)]

    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within the dungeon bounds."""
        return 0 <= x < self.config.width and 0 <= y < self.config.height

    def _carve_room(self, room: Room):
        """Carve a room's floor tiles into the grid."""
        for dy in range(room.h):
            for dx in range(room.w):
                nx, ny = room.x + dx, room.y + dy
                if self._in_bounds(nx, ny):
                    self.grid[ny][nx] = FLOOR

    def _rooms_overlap(self, room: Room, margin: int = 1) -> bool:
        """Check if a room overlaps with any existing rooms (with margin)."""
        for other in self.rooms:
            if (room.x - margin < other.x + other.w and
                room.x + room.w + margin > other.x and
                room.y - margin < other.y + other.h and
                room.h + room.y + margin > other.y):
                return True
        return False

    def _carve_corridor(self, x1: int, y1: int, x2: int, y2: int):
        """Carve an L-shaped corridor between two points."""
        x, y = x1, y1
        # L-shaped corridors: pick horizontal or vertical first
        if self.rng.random() < 0.5:
            # Horizontal first, then vertical
            while x != x2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                x += 1 if x2 > x else -1
            while y != y2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                y += 1 if y2 > y else -1
        else:
            # Vertical first, then horizontal
            while y != y2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                y += 1 if y2 > y else -1
            while x != x2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                x += 1 if x2 > x else -1
        if self._in_bounds(x2, y2) and self.grid[y2][x2] == WALL:
            self.grid[y2][x2] = CORRIDOR

    def _add_doors(self):
        """Place doors at room/corridor transitions."""
        if not self.config.add_doors:
            return
        for room in self.rooms:
            # Check each wall cell for door positions
            door_candidates = []
            for dy in range(room.h):
                for dx in range(room.w):
                    rx, ry = room.x + dx, room.y + dy
                    # Only check border cells
                    if dy == 0 or dy == room.h - 1 or dx == 0 or dx == room.w - 1:
                        # Check if adjacent to corridor
                        for nx, ny in [(rx-1,ry),(rx+1,ry),(rx,ry-1),(rx,ry+1)]:
                            if self._in_bounds(nx, ny) and self.grid[ny][nx] == CORRIDOR:
                                if self.grid[ry][rx] == FLOOR:
                                    door_candidates.append((rx, ry))
            # Place doors at some candidates
            for cx, cy in door_candidates:
                if self.rng.random() < 0.4:
                    self.grid[cy][cx] = DOOR

    def _add_water_features(self):
        """Add water puddles in some rooms."""
        if not self.config.add_water:
            return
        for i, room in enumerate(self.rooms):
            # Skip first and last room (stairs rooms) to keep them clear
            if i == 0 or i == len(self.rooms) - 1:
                continue
            if self.rng.random() < 0.3:
                cx, cy = room.center
                puddle_size = self.rng.randint(1, min(room.w, room.h) // 2)
                for dy in range(-puddle_size, puddle_size + 1):
                    for dx in range(-puddle_size, puddle_size + 1):
                        nx, ny = cx + dx, cy + dy
                        if (self._in_bounds(nx, ny) and
                            self.grid[ny][nx] == FLOOR and
                            dx*dx + dy*dy <= puddle_size*puddle_size):
                            if self.rng.random() < 0.7:
                                self.grid[ny][nx] = WATER

    def _add_pillars(self):
        """Add decorative pillars in large rooms."""
        if not self.config.add_pillars:
            return
        for room in self.rooms:
            if room.w >= 5 and room.h >= 5:
                # Add pillars in a pattern
                step_x = max(2, room.w // 3)
                step_y = max(2, room.h // 3)
                for dy in range(step_y, room.h - 1, step_y):
                    for dx in range(step_x, room.w - 1, step_x):
                        px, py = room.x + dx, room.y + dy
                        if (self._in_bounds(px, py) and
                            self.grid[py][px] == FLOOR and
                            self.rng.random() < 0.6):
                            self.grid[py][px] = PILLAR

    def _add_monsters(self):
        """Populate rooms with monsters based on theme and difficulty."""
        monsters = MONSTER_CHARS.get(self.config.theme, MONSTER_CHARS["standard"])
        names = MONSTER_NAMES.get(self.config.theme, MONSTER_NAMES["standard"])
        num_monsters = self.rng.randint(
            len(self.rooms),
            len(self.rooms) * self.config.difficulty
        )

        for _ in range(num_monsters):
            room = self.rng.choice(self.rooms)
            # Fix: skip rooms too small for entity placement (w<=2 or h<=2
            # causes randint(x+1, x+w-2) to crash when max < min)
            if room.w <= 2 or room.h <= 2:
                continue
            mx = self.rng.randint(room.x + 1, room.x + room.w - 2)
            my = self.rng.randint(room.y + 1, room.y + room.h - 2)
            # Pick monster tier based on difficulty
            tier = min(self.rng.randint(0, self.config.difficulty), len(monsters) - 1)
            char = monsters[tier]
            name = names.get(char, "Monster")
            hp = (tier + 1) * self.rng.randint(3, 8)
            if self._in_bounds(mx, my) and self.grid[my][mx] in (FLOOR, CORRIDOR):
                # Avoid stacking entities on the same tile
                if not any(e.x == mx and e.y == my for e in self.entities):
                    self.entities.append(Entity(
                        x=mx, y=my, char=char, kind="monster",
                        description=name, hp=hp, room_id=room.room_id
                    ))

    def _add_treasures(self):
        """Scatter treasure in rooms."""
        num_treasures = self.rng.randint(1, max(1, len(self.rooms) // 2))
        for _ in range(num_treasures):
            room = self.rng.choice(self.rooms)
            # Fix: skip rooms too small for entity placement (w<=2 or h<=2
            # causes randint crash when max < min)
            if room.w <= 2 or room.h <= 2:
                continue
            tx = self.rng.randint(room.x + 1, room.x + room.w - 2)
            ty = self.rng.randint(room.y + 1, room.y + room.h - 2)
            char = self.rng.choice(TREASURE_CHARS)
            gold = self.rng.randint(10, 100) * self.config.difficulty
            name = TREASURE_NAMES.get(char, "Treasure")
            if self._in_bounds(tx, ty) and self.grid[ty][tx] in (FLOOR, CORRIDOR):
                if not any(e.x == tx and e.y == ty for e in self.entities):
                    self.entities.append(Entity(
                        x=tx, y=ty, char=char, kind="treasure",
                        description=name, gold_value=gold, room_id=room.room_id
                    ))

    def _add_traps(self):
        """Place traps on corridor tiles."""
        if not self.config.add_traps:
            return
        trap_chance = 0.05 * self.config.difficulty
        for y in range(self.config.height):
            for x in range(self.config.width):
                if self.grid[y][x] == CORRIDOR and self.rng.random() < trap_chance:
                    char = self.rng.choice(TRAP_CHARS)
                    name = TRAP_NAMES.get(char, "Trap")
                    if not any(e.x == x and e.y == y for e in self.entities):
                        self.entities.append(Entity(
                            x=x, y=y, char=char, kind="trap",
                            description=name
                        ))

    def _add_npcs(self):
        """Place friendly NPCs in some rooms with themed dialogue."""
        if not self.config.add_npcs:
            return
        theme = self.config.theme
        npc_names_list = NPC_NAMES.get(theme, NPC_NAMES["standard"])
        npc_dialogue_list = NPC_DIALOGUE.get(theme, NPC_DIALOGUE["standard"])

        # Place 1-3 NPCs, avoiding the entrance and exit rooms
        num_npcs = self.rng.randint(1, min(3, len(self.rooms) - 2)) if len(self.rooms) > 3 else 0
        eligible_rooms = [r for r in self.rooms if r.room_id != 0 and r.room_id != len(self.rooms) - 1]

        for _ in range(num_npcs):
            if not eligible_rooms:
                break
            room = self.rng.choice(eligible_rooms)
            # Fix: skip rooms too small for entity placement (w<=2 or h<=2
            # causes randint crash when max < min)
            if room.w <= 2 or room.h <= 2:
                continue
            nx = self.rng.randint(room.x + 1, room.x + room.w - 2)
            ny = self.rng.randint(room.y + 1, room.y + room.h - 2)
            if self._in_bounds(nx, ny) and self.grid[ny][nx] in (FLOOR, CORRIDOR):
                if not any(e.x == nx and e.y == ny for e in self.entities):
                    char = self.rng.choice(NPC_CHARS)
                    name = self.rng.choice(npc_names_list)
                    dialogue = self.rng.choice(npc_dialogue_list)
                    self.entities.append(Entity(
                        x=nx, y=ny, char=char, kind="npc",
                        description=name, room_id=room.room_id,
                        dialogue=dialogue
                    ))

    def _add_stairs(self):
        """Place stairs up and stairs down in different rooms."""
        if len(self.rooms) < 2:
            return
        # Stairs up in the first room — find a FLOOR tile near center
        room_up = self.rooms[0]
        candidates = []
        for dy in range(room_up.h):
            for dx in range(room_up.w):
                cx, cy = room_up.x + dx, room_up.y + dy
                if self.grid[cy][cx] == FLOOR:
                    dist = abs(cx - room_up.center[0]) + abs(cy - room_up.center[1])
                    candidates.append((dist, cx, cy))
        candidates.sort()
        for _, sx, sy in candidates:
            # Check no entity already here
            if not any(e.x == sx and e.y == sy for e in self.entities):
                self.grid[sy][sx] = STAIRS_UP
                break

        # Stairs down in the last room — find a FLOOR tile near center
        room_down = self.rooms[-1]
        candidates = []
        for dy in range(room_down.h):
            for dx in range(room_down.w):
                cx, cy = room_down.x + dx, room_down.y + dy
                if self.grid[cy][cx] == FLOOR:
                    dist = abs(cx - room_down.center[0]) + abs(cy - room_down.center[1])
                    candidates.append((dist, cx, cy))
        candidates.sort()
        for _, sx, sy in candidates:
            if not any(e.x == sx and e.y == sy for e in self.entities):
                self.grid[sy][sx] = STAIRS_DOWN
                break

    def _generate_room_name(self, room: Room, index: int) -> str:
        """Generate a themed name for a room."""
        theme = self.config.theme
        prefixes = ROOM_PREFIXES.get(theme, ROOM_PREFIXES["standard"])
        suffixes = ROOM_SUFFIXES.get(theme, ROOM_SUFFIXES["standard"])

        # Entrance and exit get special names
        if index == 0:
            return "Entrance Hall"
        elif index == len(self.rooms) - 1:
            return "Descent"

        prefix = self.rng.choice(prefixes)
        suffix = self.rng.choice(suffixes)
        return f"{prefix} {suffix}"

    def _check_connectivity(self) -> bool:
        """Verify all rooms are reachable from the first room via walkable tiles."""
        if not self.rooms:
            return True

        # Find all walkable tiles
        walkable: Set[Tuple[int, int]] = set()
        for y in range(self.config.height):
            for x in range(self.config.width):
                if self.grid[y][x] != WALL:
                    walkable.add((x, y))

        if not walkable:
            return False

        # BFS from any walkable tile
        start = next(iter(walkable))
        visited = set()
        queue = deque([start])
        visited.add(start)

        while queue:
            cx, cy = queue.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in walkable and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        # All walkable tiles must be reachable
        return visited == walkable

    def generate(self) -> 'DungeonGenerator':
        """Generate the complete dungeon map.

        Creates rooms, connects them with corridors, and populates
        the map with stairs, monsters, treasures, traps, NPCs, and
        decorative features. Retries once if connectivity check fails.
        """
        for attempt in range(2):
            self._init_grid()
            self.rooms = []
            self.entities = []
            self.room_id_counter = 0

            # Generate rooms
            max_attempts = 200
            target_rooms = self.rng.randint(self.config.min_rooms, self.config.max_rooms)
            while len(self.rooms) < target_rooms and max_attempts > 0:
                max_attempts -= 1
                w = self.rng.randint(self.config.min_room_size, self.config.max_room_size)
                h = self.rng.randint(self.config.min_room_size, self.config.max_room_size)
                x = self.rng.randint(1, self.config.width - w - 1)
                y = self.rng.randint(1, self.config.height - h - 1)
                room = Room(x, y, w, h, room_id=self.room_id_counter)
                if not self._rooms_overlap(room, margin=2):
                    self._carve_room(room)
                    self.rooms.append(room)
                    self.room_id_counter += 1

            if len(self.rooms) < 2:
                # Can't build a dungeon with fewer than 2 rooms
                continue

            # Assign room names
            for i, room in enumerate(self.rooms):
                room.name = self._generate_room_name(room, i)

            # Connect rooms with corridors (MST-like with extra connections)
            connected = [0]
            unconnected = list(range(1, len(self.rooms)))

            while unconnected:
                best_dist = float('inf')
                best_pair = (connected[0], unconnected[0])
                for ci in connected:
                    for ui in unconnected:
                        r1 = self.rooms[ci]
                        r2 = self.rooms[ui]
                        dist = math.hypot(r1.center[0] - r2.center[0],
                                         r1.center[1] - r2.center[1])
                        if dist < best_dist:
                            best_dist = dist
                            best_pair = (ci, ui)
                ci, ui = best_pair
                self._carve_corridor(
                    self.rooms[ci].center[0], self.rooms[ci].center[1],
                    self.rooms[ui].center[0], self.rooms[ui].center[1]
                )
                connected.append(ui)
                unconnected.remove(ui)

            # Add a few extra corridors for loops
            for _ in range(self.rng.randint(1, max(1, len(self.rooms) // 3))):
                i = self.rng.randint(0, len(self.rooms) - 1)
                j = self.rng.randint(0, len(self.rooms) - 1)
                if i != j:
                    self._carve_corridor(
                        self.rooms[i].center[0], self.rooms[i].center[1],
                        self.rooms[j].center[0], self.rooms[j].center[1]
                    )

            # Verify connectivity before adding entities
            if not self._check_connectivity():
                continue

            # Add features
            self._add_water_features()
            self._add_pillars()
            self._add_doors()
            self._add_stairs()
            self._add_monsters()
            self._add_treasures()
            self._add_traps()
            self._add_npcs()

            return self

        # If we couldn't generate a connected dungeon after retries,
        # raise an error rather than returning a broken state silently.
        # Callers should catch this and retry with different parameters.
        raise RuntimeError(
            f"Could not generate a valid dungeon with {len(self.rooms)} rooms "
            f"(need at least 2). Try increasing map size or reducing room count."
        )

    def render(self) -> str:
        """Render the dungeon as an ASCII string."""
        theme = self.config.theme
        wall_char = THEME_WALL.get(theme, "█")
        floor_char = THEME_FLOOR.get(theme, "·")

        # Build entity lookup by position
        entity_map: Dict[Tuple[int, int], Entity] = {}
        for e in self.entities:
            entity_map[(e.x, e.y)] = e

        lines = []
        for y in range(self.config.height):
            row = []
            for x in range(self.config.width):
                if (x, y) in entity_map:
                    row.append(entity_map[(x, y)].char)
                else:
                    tile = self.grid[y][x]
                    if tile == WALL:
                        row.append(wall_char)
                    elif tile in (FLOOR, CORRIDOR):
                        row.append(floor_char)
                    else:
                        row.append(TILE_CHARS.get(tile, "?"))
            lines.append("".join(row))
        return "\n".join(lines)

    def render_legend(self) -> str:
        """Render a legend describing all symbols in the dungeon."""
        theme = self.config.theme
        wall_char = THEME_WALL.get(theme, "█")
        floor_char = THEME_FLOOR.get(theme, "·")

        # Difficulty bar
        diff_stars = "★" * self.config.difficulty + "☆" * (5 - self.config.difficulty)

        lines = [
            f"{'═' * 40}",
            f"  DUNGEON MAP — Theme: {theme.upper()}",
            f"  Difficulty: {diff_stars}",
            f"{'═' * 40}",
            f"",
            f"  LEGEND:",
            f"  {wall_char}  Wall",
            f"  {floor_char}  Floor / Corridor",
            f"  +  Door",
            f"  ▼  Stairs Down",
            f"  ▲  Stairs Up (Entrance)",
            f"  ~  Water",
            f"  ○  Pillar",
            f"",
        ]

        # Group entities by kind
        monsters = [e for e in self.entities if e.kind == "monster"]
        treasures = [e for e in self.entities if e.kind == "treasure"]
        traps = [e for e in self.entities if e.kind == "trap"]
        npcs = [e for e in self.entities if e.kind == "npc"]

        if monsters:
            lines.append(f"  MONSTERS ({len(monsters)}):")
            seen: Dict[str, str] = {}
            for m in monsters:
                if m.char not in seen:
                    seen[m.char] = m.description
            for char, name in seen.items():
                count = sum(1 for m in monsters if m.char == char)
                lines.append(f"    {char}  {name} (×{count})")
            lines.append("")

        if treasures:
            lines.append(f"  TREASURES ({len(treasures)}):")
            for t in treasures:
                lines.append(f"    {t.char}  {t.description} ({t.gold_value}gp)")
            lines.append("")

        if traps:
            lines.append(f"  TRAPS ({len(traps)}):")
            seen = {}
            for t in traps:
                if t.char not in seen:
                    seen[t.char] = t.description
            for char, name in seen.items():
                count = sum(1 for t in traps if t.char == char)
                lines.append(f"    {char}  {name} (×{count})")
            lines.append("")

        if npcs:
            lines.append(f"  NPCs ({len(npcs)}):")
            seen = {}
            for n in npcs:
                if n.char not in seen:
                    seen[n.char] = n.description
            for char, name in seen.items():
                lines.append(f"    {char}  {name}")
            lines.append("")

        # Room listing
        lines.append(f"  ROOMS ({len(self.rooms)}):")
        for room in self.rooms:
            lines.append(f"    [{room.room_id}] {room.name} "
                         f"({room.w}×{room.h} at {room.x},{room.y})")

        lines.append("")
        lines.append(f"  DIMENSIONS: {self.config.width}×{self.config.height}")
        if self.config.seed is not None:
            lines.append(f"  SEED: {self.config.seed}")
        lines.append(f"{'═' * 40}")
        return "\n".join(lines)

    def render_stats(self) -> str:
        """Render summary statistics."""
        total_floor = sum(1 for y in range(self.config.height)
                         for x in range(self.config.width)
                         if self.grid[y][x] in (FLOOR, CORRIDOR))
        total_area = self.config.width * self.config.height
        density = total_floor / max(1, total_area) * 100
        monsters = [e for e in self.entities if e.kind == "monster"]
        avg_hp = sum(m.hp for m in monsters) / max(1, len(monsters))
        total_gold = sum(t.gold_value for t in self.entities if t.kind == "treasure")
        npcs = [e for e in self.entities if e.kind == "npc"]

        return (
            f"  Floor density: {density:.1f}%\n"
            f"  Walkable tiles: {total_floor}\n"
            f"  Rooms: {len(self.rooms)}\n"
            f"  Monsters: {len(monsters)} (avg HP: {avg_hp:.0f})\n"
            f"  Treasures: {sum(1 for e in self.entities if e.kind == 'treasure')} "
            f"({total_gold}gp total)\n"
            f"  Traps: {sum(1 for e in self.entities if e.kind == 'trap')}\n"
            f"  NPCs: {len(npcs)}\n"
            f"  Connected: {'Yes' if self._check_connectivity() else 'No'}\n"
        )

    def to_json(self) -> str:
        """Export the dungeon as JSON for programmatic use."""
        data = {
            "version": __version__,
            "config": {
                "width": self.config.width,
                "height": self.config.height,
                "theme": self.config.theme,
                "difficulty": self.config.difficulty,
                "seed": self.config.seed,
            },
            "rooms": [
                {
                    "id": r.room_id,
                    "name": r.name,
                    "x": r.x,
                    "y": r.y,
                    "w": r.w,
                    "h": r.h,
                    "center": list(r.center),
                    "area": r.area,
                }
                for r in self.rooms
            ],
            "entities": [
                {
                    "x": e.x,
                    "y": e.y,
                    "char": e.char,
                    "kind": e.kind,
                    "description": e.description,
                    "hp": e.hp,
                    "gold_value": e.gold_value,
                    "room_id": e.room_id,
                    "dialogue": e.dialogue,
                }
                for e in self.entities
            ],
            "grid": [
                [TILE_NAMES.get(self.grid[y][x], "wall")
                 for x in range(self.config.width)]
                for y in range(self.config.height)
            ],
            "map": self.render(),
        }
        return json.dumps(data, indent=2)

    def render_fog_of_war(self, reveal_radius: int = 4) -> str:
        """Render the dungeon with fog of war, revealing only tiles
        within `reveal_radius` of each entity."""
        revealed: Set[Tuple[int, int]] = set()

        # Reveal around each entity
        for e in self.entities:
            for dy in range(-reveal_radius, reveal_radius + 1):
                for dx in range(-reveal_radius, reveal_radius + 1):
                    if dx*dx + dy*dy <= reveal_radius * reveal_radius:
                        nx, ny = e.x + dx, e.y + dy
                        if self._in_bounds(nx, ny):
                            revealed.add((nx, ny))

        # Also reveal around stairs
        for y in range(self.config.height):
            for x in range(self.config.width):
                if self.grid[y][x] in (STAIRS_UP, STAIRS_DOWN):
                    for dy in range(-reveal_radius, reveal_radius + 1):
                        for dx in range(-reveal_radius, reveal_radius + 1):
                            if dx*dx + dy*dy <= reveal_radius * reveal_radius:
                                nx, ny = x + dx, y + dy
                                if self._in_bounds(nx, ny):
                                    revealed.add((nx, ny))

        theme = self.config.theme
        wall_char = THEME_WALL.get(theme, "█")
        floor_char = THEME_FLOOR.get(theme, "·")
        fog_char = " "

        # Build entity lookup by position
        entity_map: Dict[Tuple[int, int], Entity] = {}
        for e in self.entities:
            entity_map[(e.x, e.y)] = e

        lines = []
        for y in range(self.config.height):
            row = []
            for x in range(self.config.width):
                if (x, y) not in revealed:
                    row.append(fog_char)
                elif (x, y) in entity_map:
                    row.append(entity_map[(x, y)].char)
                else:
                    tile = self.grid[y][x]
                    if tile == WALL:
                        row.append(wall_char)
                    elif tile in (FLOOR, CORRIDOR):
                        row.append(floor_char)
                    else:
                        row.append(TILE_CHARS.get(tile, "?"))
            lines.append("".join(row))
        return "\n".join(lines)


def validate_config(config: DungeonConfig) -> List[str]:
    """Validate dungeon configuration, returning a list of error messages."""
    errors = []
    if config.width < 10 or config.height < 10:
        errors.append(f"Dungeon dimensions too small ({config.width}×{config.height}), "
                      f"minimum is 10×10.")
    if config.width > 200 or config.height > 100:
        errors.append(f"Dungeon dimensions too large ({config.width}×{config.height}), "
                      f"maximum is 200×100.")
    if config.min_rooms < 2:
        errors.append(f"Need at least 2 rooms, got min_rooms={config.min_rooms}.")
    if config.min_rooms > config.max_rooms:
        errors.append(f"min_rooms ({config.min_rooms}) cannot exceed "
                      f"max_rooms ({config.max_rooms}).")
    if config.difficulty < 1 or config.difficulty > 5:
        errors.append(f"Difficulty must be 1-5, got {config.difficulty}.")
    if config.min_room_size < 2:
        errors.append(f"Room size too small, min_room_size={config.min_room_size}.")
    # Fix: validate theme to prevent KeyError during generation
    valid_themes = {"standard", "crypt", "inferno", "forest", "aquatic"}
    if config.theme not in valid_themes:
        errors.append(f"Invalid theme '{config.theme}', must be one of: {', '.join(sorted(valid_themes))}.")
    # Fix: validate that max_room_size can fit on the map
    max_dim = min(config.width, config.height)
    if config.max_room_size + 2 > max_dim:
        errors.append(f"Room size too large (max_room_size={config.max_room_size}) for "
                      f"a {config.width}×{config.height} map. Maximum room size for this map: {max_dim - 2}.")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Procedural ASCII Dungeon Map Generator",
        epilog="Generate random dungeons for tabletop RPGs, game dev, or just for fun!"
    )
    parser.add_argument(
        "-V", "--version", action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-W", "--width", type=int, default=60,
        help="Dungeon width (default: 60, min: 10, max: 200)"
    )
    parser.add_argument(
        "-H", "--height", type=int, default=30,
        help="Dungeon height (default: 30, min: 10, max: 100)"
    )
    parser.add_argument(
        "--min-rooms", type=int, default=5,
        help="Minimum number of rooms (default: 5, min: 2)"
    )
    parser.add_argument(
        "-r", "--max-rooms", type=int, default=12,
        help="Maximum number of rooms (default: 12)"
    )
    parser.add_argument(
        "-t", "--theme",
        choices=["standard", "crypt", "inferno", "forest", "aquatic"],
        default="standard",
        help="Dungeon theme (default: standard)"
    )
    parser.add_argument(
        "-d", "--difficulty", type=int, default=1,
        help="Difficulty 1-5 (default: 1)"
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-water", action="store_true",
        help="Disable water features"
    )
    parser.add_argument(
        "--no-pillars", action="store_true",
        help="Disable pillars"
    )
    parser.add_argument(
        "--no-traps", action="store_true",
        help="Disable traps"
    )
    parser.add_argument(
        "--no-doors", action="store_true",
        help="Disable doors"
    )
    parser.add_argument(
        "--no-npcs", action="store_true",
        help="Disable NPCs"
    )
    parser.add_argument(
        "--legend", action="store_true",
        help="Show legend and entity listing"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show dungeon statistics"
    )
    parser.add_argument(
        "--json", action="store_true",
        dest="export_json",
        help="Export dungeon as JSON to stdout"
    )
    parser.add_argument(
        "--fog", action="store_true",
        help="Render with fog of war (only areas near entities are visible)"
    )
    parser.add_argument(
        "--fog-radius", type=int, default=4,
        help="Fog of war reveal radius (default: 4)"
    )

    args = parser.parse_args()

    config = DungeonConfig(
        width=args.width,
        height=args.height,
        min_rooms=max(2, args.min_rooms),
        max_rooms=max(args.min_rooms, args.max_rooms) if args.max_rooms < args.min_rooms else args.max_rooms,
        theme=args.theme,
        difficulty=max(1, min(5, args.difficulty)),
        seed=args.seed,
        add_water=not args.no_water,
        add_pillars=not args.no_pillars,
        add_traps=not args.no_traps,
        add_doors=not args.no_doors,
        add_npcs=not args.no_npcs,
    )

    # Validate configuration
    errors = validate_config(config)
    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    generator = DungeonGenerator(config)
    try:
        generator.generate()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.export_json:
        print(generator.to_json())
        return

    print()
    if args.fog:
        print(generator.render_fog_of_war(reveal_radius=args.fog_radius))
    else:
        print(generator.render())
    print()

    if args.legend:
        print(generator.render_legend())
        print()

    if args.stats:
        print("  ── DUNGEON STATS ──")
        print(generator.render_stats())


if __name__ == "__main__":
    main()