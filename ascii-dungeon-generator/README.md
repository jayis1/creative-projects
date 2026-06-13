# 🏰 Procedural ASCII Dungeon Map Generator

Generate random dungeon maps with rooms, corridors, monsters, treasures, traps, NPCs, and stairs — all rendered in beautiful ASCII art.

```
████████████████████████████████████████████████████████████
███·······██████████████████████████████████████████████████
███·····W·██████████████████████████████████████████████████
███··○·○··█████████████████████████████········█████████████
███·s@····█████████████████████████··s·z···█████····████████
███··○·○··█████████████████████████··○·····█████·✦··████████
███···+···█████████████████████████·W·········^··zW·████████
██████·████████████·×·········?···^····○··+!·×······████████
██████·███████████··+██████████████··z·····██████·██████████
██████·███████████···██████████████··○·○·○·██████·██████████
```

## Features

- **5 dungeon themes**: standard, crypt, inferno, forest, aquatic — each with unique wall/floor characters and monster sets
- **Difficulty levels 1–5**: controls monster density, trap frequency, and monster tier
- **Procedural generation**: BSP-like room placement with L-shaped corridors and extra loops for interesting layouts
- **Rich entities**: themed monsters (6 tiers per theme), treasures with gold values, traps, water features, pillars, doors, and **NPCs with dialogue**
- **Named rooms**: each room gets a procedurally generated themed name (e.g., "Cursed Sepulcher", "Verdant Hollow")
- **Fog of war mode**: render only areas near entities for a true exploration feel
- **JSON export**: dump the entire dungeon (grid, rooms, entities, rendered map) as structured JSON
- **Reproducible seeds**: generate the same dungeon twice with `--seed`
- **Legend & stats**: optional detailed output showing all entities, room listings, and dungeon metrics
- **Connectivity verification**: ensures all rooms are reachable (auto-retries if not)
- **Input validation**: catches bad dimensions, invalid difficulty, etc.
- **`--version` and `--help` flags**

## How to Run

```bash
python3 dungeon_generator.py
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-V / --version` | — | Show version and exit |
| `-W / --width` | 60 | Map width (10–200) |
| `-H / --height` | 30 | Map height (10–100) |
| `--min-rooms` | 5 | Minimum number of rooms (min: 2) |
| `-r / --max-rooms` | 12 | Maximum number of rooms |
| `-t / --theme` | standard | Theme: `standard`, `crypt`, `inferno`, `forest`, `aquatic` |
| `-d / --difficulty` | 1 | Difficulty 1–5 |
| `-s / --seed` | random | Reproducible seed |
| `--legend` | off | Show entity legend and room listing |
| `--stats` | off | Show dungeon statistics |
| `--json` | off | Export dungeon as JSON to stdout |
| `--fog` | off | Render with fog of war |
| `--fog-radius` | 4 | Fog of war reveal radius |
| `--no-water` | off | Disable water puddles |
| `--no-pillars` | off | Disable pillars |
| `--no-traps` | off | Disable traps |
| `--no-doors` | off | Disable doors |
| `--no-npcs` | off | Disable NPCs |

### Examples

```bash
# Default dungeon
python3 dungeon_generator.py

# Spooky crypt, hard difficulty
python3 dungeon_generator.py --theme crypt --difficulty 4 --legend

# Large forest dungeon with seed for reproducibility
python3 dungeon_generator.py -W 80 -H 40 -t forest -d 3 -s 42 --legend --stats

# Minimal dungeon — no traps, no water, no NPCs
python3 dungeon_generator.py --no-traps --no-water --no-npcs

# Export as JSON for use in other programs
python3 dungeon_generator.py --seed 7 --json > dungeon.json

# Fog of war — only areas near entities are revealed
python3 dungeon_generator.py --fog --fog-radius 5 --legend

# Show version
python3 dungeon_generator.py --version

# Aquatic theme with max difficulty
python3 dungeon_generator.py -t aquatic -d 5 --legend --stats
```

## What It Does

The generator:

1. **Places rooms** randomly on a grid, ensuring no overlaps with margins, and assigns each room a procedurally generated themed name
2. **Connects rooms** via L-shaped corridors using a minimum-spanning-tree approach, then adds extra corridors for loops
3. **Verifies connectivity** — all rooms must be reachable from each other (retries if not)
4. **Decorates rooms** with water puddles, pillars, and doors at corridor transitions
5. **Places stairs** — ▲ entrance in the first room ("Entrance Hall"), ▼ descent in the last room ("Descent")
6. **Populates entities** — monsters scaled to difficulty, treasures with gold values, hidden traps in corridors, and **friendly NPCs with themed dialogue**
7. **Renders** the final map with theme-appropriate characters, plus optional legend, stats, fog-of-war, or JSON export

## Themes

Each theme changes the visual style and monster roster:

| Theme | Wall | Floor | Monsters |
|-------|------|-------|----------|
| **standard** | █ | · | Rat, Bat, Orc, Rock Golem, Bear, Ogre |
| **crypt** | █ | · | Zombie, Skeleton, Ghost, Wraith, Vampire, Lich |
| **inferno** | ▓ | ≈ | Imp, Demon, Fire Elemental, Devil, Infernal, Fire Lord |
| **forest** | ▒ | ░ | Wolf, Kobold, Arachnid, Spider Queen, Treant, Arch-druid |
| **aquatic** | ░ | ~ | Murloc, Eel, Piranha, Merfolk, Electric Eel, Kraken |

## NPCs

NPCs are placed in rooms (avoiding the entrance and exit) and come with themed dialogue:

- **crypt**: *"The dead walk these halls... be careful."*
- **inferno**: *"The heat gets worse the deeper you go."*
- **forest**: *"The trees have eyes here. Stay on the path."*
- **aquatic**: *"The tides shift the corridors below."*
- **standard**: *"Welcome, adventurer! Mind the traps."*

## JSON Export

Use `--json` to get machine-readable output:

```json
{
  "version": "1.1.0",
  "config": { "width": 60, "height": 30, "theme": "standard", "difficulty": 1, "seed": 42 },
  "rooms": [
    { "id": 0, "name": "Entrance Hall", "x": 18, "y": 8, "w": 3, "h": 8, "center": [19, 12], "area": 24 },
    ...
  ],
  "entities": [
    { "x": 5, "y": 3, "char": "r", "kind": "monster", "description": "Rat", "hp": 6, "gold_value": 0, "room_id": 2, "dialogue": "" },
    ...
  ],
  "grid": [["wall", "wall", ...], ...],
  "map": "██████████\n██·▲·█████\n..."
}
```

## Testing

```bash
python3 test_dungeon_generator.py
```

Runs 16 tests covering generation, reproducibility, connectivity, all themes, difficulty scaling, feature toggles, NPCs, JSON export, fog of war, room names, input validation, and entity overlap detection.

## Output Sample (Crypt Theme)

```
════════════════════════════════════════
  DUNGEON MAP — Theme: CRYPT
  Difficulty: ★★★☆☆
════════════════════════════════════════

  LEGEND:
  █  Wall
  ·  Floor / Corridor
  +  Door
  ▼  Stairs Down
  ▲  Stairs Up (Entrance)
  ~  Water
  ○  Pillar

  MONSTERS (12):
    g  Ghost (×2)
    W  Wraith (×4)
    z  Zombie (×3)
    s  Skeleton (×3)

  TREASURES (2):
    ♥  Potion (285gp)
    ✦  Magic scroll (36gp)

  TRAPS (16):
    ^  Spike trap (×5)
    ×  Poison gas (×5)
    ?  Illusion (×5)
    !  Pit trap (×1)

  NPCs (1):
    @  Lost Soul

  ROOMS (6):
    [0] Entrance Hall (3×8 at 18,8)
    [1] Cursed Sepulcher (4×4 at 48,4)
    [2] Hollow Crypt (8×8 at 35,3)
    [3] Hollow Sepulcher (7×6 at 3,1)
    [4] Forgotten Catacomb (8×8 at 45,18)
    [5] Descent (6×4 at 29,19)

  DIMENSIONS: 60×30
  SEED: 42
════════════════════════════════════════
```

## Fog of War

Use `--fog` to reveal only areas near entities and stairs:

```
███████                                                
     ·····██                           █         █          
    ····b·███                        █████     █████        
     ○·○··██                █       ·······   ███████       
```

Dark spaces remain hidden until explored — perfect for solo play or integration into games.

## Known Issues (Resolved)

The following bugs were found and fixed during a systematic bug hunt on 2026-06-12:

1. **CRITICAL — `ValueError` crash with `min_room_size=2`**: The `_add_monsters`, `_add_treasures`, and `_add_npcs` methods used `randint(room.x + 1, room.x + room.w - 2)` which crashes with `ValueError: empty range in randrange` when `room.w <= 2` or `room.h <= 2`. **Fix**: Added a guard to skip rooms too small for entity placement.

2. **`validate_config` didn't validate theme**: Passing an invalid theme (e.g., `"invalid"`) passed validation but caused a `KeyError` crash during generation. **Fix**: Added theme validation against the set of valid themes.

3. **`validate_config` didn't validate room size vs map size**: A 10×10 map with `max_room_size=15` passed validation but couldn't fit rooms. **Fix**: Added a check that `max_room_size + 2` doesn't exceed the smaller map dimension.

4. **`generate()` silently returned broken dungeons**: When room placement repeatedly failed, `generate()` returned `self` with fewer than 2 rooms, silently producing invalid dungeons. **Fix**: Now raises `RuntimeError` with a helpful message instead of returning silently.

5. **`crack_vigenere` returned original ciphertext for short texts**: The `<short>` marker was ambiguous and could be confused with a real decryption key. **Fix**: Changed marker to `<too-short>` for clarity.

6. **`combined_score` word matching ignored punctuation**: Words like `"mat."` wouldn't match `"mat"` in the common words set, reducing `crack_caesar` accuracy for punctuated text. **Fix**: Added `.strip('.,!?;:\'"()')` to strip punctuation before word matching.

7. **`analyze_frequency` IoC division edge case**: When `total == 1`, the IoC formula `n*(n-1)` produces `0`, making the division `0/0`. Python happened to handle this correctly (returning 0), but the edge case was not explicitly guarded. **Fix**: Made the edge case explicit with a clear `if/else` block.

## License

MIT