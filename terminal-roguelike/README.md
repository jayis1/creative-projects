# Terminal Roguelike Engine

A full-featured ASCII dungeon crawler built entirely in Python — no external dependencies required. Descend through 5 floors of procedurally generated dungeons, fight 10 enemy types, collect loot, and face powerful bosses.

## Features

### Dungeon Generation
- **Procedural rooms and corridors** — every floor is unique
- **5-floor dungeon** with scaling difficulty
- **Stairs** between floors
- **Traps** scattered throughout
- **Fog of war** with ray-casting line-of-sight (explored/visible tile distinction)

### Combat System
- **Dice-based combat** — D&D-style hit rolls, AC, damage dice
- **Strength & Dexterity** modifiers for hit and damage
- **Mana-based spellcasting** for scrolls
- **10 enemy types** with unique AI behaviors:

| Enemy | HP | AC | Damage | Special |
|---|---|---|---|---|
| Giant Rat | 6 | 0 | 1d3 | Wanders randomly |
| Goblin | 12 | 2 | 1d6 | Hunts player when in range |
| Skeleton | 15 | 4 | 1d6+1 | Hunts player |
| Orc | 25 | 5 | 1d8+2 | Hunts aggressively |
| Dark Mage | 18 | 3 | 2d4 | Casts spells (fireball, blizzard, slow, drain) |
| Troll | 40 | 4 | 2d6+3 | Regenerates health |
| Vampire | 35 | 5 | 1d8+3 | Drains player HP to heal |
| Dragon | 100 | 8 | 3d6+5 | Boss — breath weapon, tail swipe |
| Lich Lord | 80 | 6 | 2d8+4 | Boss — spell rotations |
| Arch Demon | 120 | 7 | 3d8+6 | Final boss — devastating abilities |

### Items & Inventory
- **26-slot inventory** with equip/unequip
- **Equipment slots**: Weapon, Body, Offhand, Ring
- **16+ items**:
  - _Potions_: Health, Mana, Might (+STR), Agility (+DEX)
  - _Scrolls_: Fireball, Blizzard, Mapping (reveal map), Teleport
  - _Weapons_: Dagger → Short Sword → Long Sword → Battle Axe → Flame Blade
  - _Armor_: Leather → Chain → Plate → Dragon Scale
  - _Shield_, _Ring of Protection_

### UI & Controls
- **Colored ASCII rendering** with box-drawing UI elements
- **HP/MP bars** with numeric display
- **Message log** for combat and event feedback
- **Multiple screens**: Inventory, Character Sheet, Look Mode, Help
- **Movement**: Vi-keys (hjklyubn) or Numpad (84621379)
- **Actions**: Pick up (`,`), Use (u), Drop (d), Wait (.), Look (x), Help (?)

### Save & Load
- Full game state serialized to JSON
- Resume from any floor with all inventory, HP, and explored map intact

## Installation

No dependencies — just Python 3.8+:

```bash
# No install needed, just run:
python3 roguelike.py
```

## How to Play

```bash
cd ~/daily-ideas/2026-06-12-terminal-roguelike
python3 roguelike.py
```

### Controls

| Key | Action |
|---|---|
| `h/j/k/l` | Move left/down/up/right (Vi-keys) |
| `y/u/b/n` | Move diagonally (Vi-keys) |
| `Numpad` | Movement (84621379) |
| `.` | Wait a turn |
| `,` | Pick up item |
| `i` | Open inventory |
| `c` | Character sheet |
| `e` | Equipment view |
| `u` | Use item (potion/scroll) |
| `d` | Drop item |
| `x` | Look mode |
| `S` | Save game |
| `L` | Load game (from title) |
| `?` | Help screen |
| `Q` | Quit |

### Strategy Tips
- Use **Scrolls of Mapping** on new floors to reveal the layout
- Save **Fireball/Blizzard scrolls** for groups of enemies
- The **Dragon** on Floor 5 has a devastating breath weapon — carry potions and use the corridor choke points
- **Dark Mages** cast spells from range — close the distance quickly
- **Vampires** heal when they hit you — don't trade blows, use scrolls

## Architecture

```
roguelike.py (1,625 lines)
├── Dice System         — dice notation parser (1d6+2, 3d10-1, etc.)
├── Dungeon Generator   — BSP-style room placement, corridor carving
├── FOV Engine          — ray-casting with transparency checks
├── Entity System       — player, enemies, NPCs with AI behaviors
├── Combat Engine       — attack rolls, damage calculation, AC system
├── Item System         — 16+ items with use/equip/drop mechanics
├── Inventory Manager   — 26-slot inventory, equipment slots
├── AI Behaviors        — wander, hunt, spellcast, boss patterns
├── Renderer            — curses-based colored terminal rendering
├── Save/Load           — JSON serialization of full game state
└── Game Loop           — turn-based, process enemies after each move
```

## Example Output

```
╔══════════════════════════════════════════════════════════════╗
║ FLOOR 1  HP: ████████████████ 30/30  MP: ██████ 10/10      ║
║ STR:10 DEX:10 AC:10 Gold:0    Turn: 47                     ║
╠══════════════════════════════════════════════════════════════╣
║                    #                                         ║
║    #############  .##                                        ║
║    #...........#  .#                                         ║
║    #.....@.....#  .##  #####                                 ║
║    #...........#  .## #...#                                 ║
║    #.....g.....#  .# #...#                                 ║
║    #############  .# #...#                                 ║
║                    #  #####                                 ║
╠══════════════════════════════════════════════════════════════╣
║ You see: Goblin (wounded)                                    ║
║ The goblin strikes you for 4 damage!                         ║
╚══════════════════════════════════════════════════════════════╝
```

## License

MIT — built as a daily-ideas project. Have fun!