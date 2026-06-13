# 🪐 Procedural Planet Generator

Generate infinite fictional worlds with detailed properties, habitability scores, hazard assessments, resource ratings, named moons, and ASCII art globe renderings. Each planet is procedurally generated from a seed — use the same seed and get the same world every time.

## Features

- **12 planet types**: Lava World, Desert World, Ice World, Ocean World, Terran World, Gas Giant, Ice Giant, Toxic World, Crystalline World, Storm World, Megastructure, Rogue Planet
- **Stellar classification**: Generates parent stars (O/B/A/F/G/K/M class) with realistic temperature and mass
- **Detailed properties**: Gravity, atmosphere, surface water, magnetic field, moons, ring systems, axial tilt, temperature, day/year length
- **Habitability scoring**: Each planet gets a 0–100 habitability score with a letter grade (A–F) based on temperature, atmosphere, gravity, water, magnetic field, life, and distance from star
- **Hazard assessment**: Planets are rated with hazard levels (Low/Moderate/High/Critical) and 2–4 specific environmental hazards
- **Resource potential**: Each planet is rated for resource richness (Low–Exceptional) with specific exploitable resources listed
- **Named moons**: Planets generate named moons with radius, orbital period, and brief descriptions (e.g., "volcanic", "subsurface ocean")
- **Life detection**: Procedural life level appropriate to planet type — from "None" to "Post-Singularity"
- **Notable features**: Each planet gets 1–3 unique features like "Cryovolcanoes", "Great Storm Vortex", "Dyson Fragments"
- **Smart descriptions**: Procedurally generated lore paragraphs with correct grammar for singular/plural features, article agreement (a/an), and special handling for Rogue Planets (no star references), "None" atmospheres, and "None" life levels
- **ASCII globe rendering**: Colored (ANSI) or plain-text globe visualization with per-planet-type character sets, ring systems, and terrain patterns
- **Seeded generation**: Same seed = same planet, every time. Share seeds with friends!
- **Batch generation**: Generate multiple planets at once
- **Planet comparison**: Side-by-side comparison table for multiple planets
- **JSON export**: Machine-readable JSON output with `--json`
- **Text export**: Save planet catalogs to text files with `--save`
- **Procedural names**: Evocative names like "Gilded Vexion-879", "Ashul-468", "Dreaming Phoros-112"

## Installation

No external dependencies — uses only the Python standard library.

```bash
# Just clone and run
git clone <repo-url>
cd procedural-planet-generator
python3 planet_gen.py
```

## Usage

```bash
# Generate a random planet
python3 planet_gen.py

# Generate with a specific seed (reproducible)
python3 planet_gen.py --seed 42
python3 planet_gen.py --seed "my-world"

# Generate multiple planets
python3 planet_gen.py --count 5

# Generate multiple planets from a seed (each gets a derived seed)
python3 planet_gen.py --seed "exploration" --count 3

# Compare multiple planets side-by-side
python3 planet_gen.py --seed "exploration" --count 3 --compare

# Disable the ASCII globe
python3 planet_gen.py --no-globe

# Disable ANSI colors (for piping or light terminals)
python3 planet_gen.py --no-color

# Hide specific sections
python3 planet_gen.py --no-moons
python3 planet_gen.py --no-hazards
python3 planet_gen.py --no-resources

# Output as JSON (great for scripting)
python3 planet_gen.py --seed 42 --json

# Save to a file
python3 planet_gen.py --seed "catalog-1" --save planets.txt

# Custom globe size (wider globe)
python3 planet_gen.py --size 60

# Show version
python3 planet_gen.py --version
```

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🪐 Ashul-468
  Seed: 42
──────────────────────────────────────────
  Type:            Gas Giant
  Star:            M-class (Red, 2,721 K, 0.23 M☉)
  Distance:        0.94 AU
  Radius:          31,533 km
  Gravity:         2.31g
  Day Length:      192.4 hours
  Year Length:     694.1 days
  Axial Tilt:      88.4°
  Mean Temp:       200°C
  Atmosphere:      Hydrogen/Helium/Methane
  Surface Water:   0.0%
  Magnetic Field:   Moderate
  Moons:           71
  Ring System:     Yes
  Life Level:      None
  Features:        Ring System
──────────────────────────────────────────
  Habitability:    ░░░░░░░░░░░░░░░░░░░░ 0  F — Lethal
  Hazard Level:     Critical
  Hazards:          Extreme Winds, Lightning Storms, Gravitational Shear
  Resources:        Moderate — Storm-sourced Compounds, Lightning Energy
──────────────────────────────────────────
  A red star illuminates the gas giant Ashul-468, where hydrogen/helium/methane fills the atmosphere. Beneath, ring system awaits discovery. Life status: no known life.
──────────────────────────────────────────
  Globe View:
                    ~
            -~~~~~~~--------~
         ---~~≈≈≈~~--------~~≈~~
        ...
──────────────────────────────────────────
  Major Moons:
    ▪ Yoax-59: 1,993 km, orbit 11.1d — volcanic
    ▪ Alar-32: 229 km, orbit 15.3d — cratered
    ▪ Alis-90: 2,040 km, orbit 65.7d — subsurface ocean
    ... and 66 more moons
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## JSON Output

Use `--json` for machine-readable output:

```bash
python3 planet_gen.py --seed 42 --json
```

Returns a JSON object with all planet properties including habitability score, hazard level, resources, and moon details.

## Planet Comparison

Use `--compare` with `--count` to see a side-by-side table:

```bash
python3 planet_gen.py --seed "exploration" --count 3 --compare --no-globe
```

Shows a compact comparison of Type, Star, Distance, Gravity, Temperature, Habitability, Hazards, Resources, and more across all generated planets.

## How It Works

1. **Seeding**: A SHA-256 hash of the seed string initializes a deterministic `random.Random` instance, ensuring reproducibility.
2. **Star generation**: A star type (O through M) is chosen using realistic frequency weights, then temperature and mass are randomly sampled within that class's ranges.
3. **Planet type**: Selected via weighted random choice from 12 types.
4. **Property derivation**: Each property (distance, radius, gravity, temperature, atmosphere, life, features) is generated contextually based on the planet type — gas giants get many moons, lava worlds get extreme temperatures, megastructures get engineered climates.
5. **Habitability scoring**: Computed from temperature, atmosphere breathability, gravity, surface water, magnetic field, life level, and distance from star. Terran worlds score highest; gas giants and lava worlds score lowest. Rogue planets receive no distance bonus.
6. **Hazard assessment**: Each planet type has a hazard pool; hazard level is determined by type and conditions, with specific hazards randomly selected.
7. **Resource rating**: Based on planet type and life level, with specific resources drawn from type-appropriate pools.
8. **Moon generation**: Planets generate named moons with radius, orbital period, and type-specific descriptors.
9. **Globe rendering**: A 2D projection maps (x, y) coordinates onto a sphere. Values are modulated by sinusoidal "terrain" functions seeded by the planet's properties. Each planet type has its own character/color palette. Gas giants show horizontal banding. Rings are rendered as horizontal lines beyond the sphere's edge.
10. **Naming**: A random prefix + suffix creates names like "Vexion", "Zoroth", "Klaara". A 30% chance adds an evocative descriptor prefix ("Gilded", "Ancient", "Dreaming").
11. **Description**: Procedurally generated lore paragraphs with grammar-aware formatting — singular/plural verb agreement for features, correct articles (a/an) for star colors, and special templates for Rogue Planets that avoid referencing stars.

## Testing

```bash
python3 test_planet_gen.py
```

Runs 74 tests covering:
- Seeded RNG determinism
- Planet generation (all types, properties, reproducibility)
- Habitability scoring (Terran ideal, Lava low, Toxic low, Megastructure, distance bonus)
- Hazard assessment (type-specific levels, correct pools)
- Resource computation (type-appropriate, potential levels)
- Globe rendering (dimensions, color modes, determinism)
- Display formatting (all fields present, section toggles)
- Export functions (text, JSON, round-trip)
- Planet comparison
- Version format
- Data table integrity (all types have atmospheres, life levels, features, hazards, resources, globe chars)
- Format helpers (atmosphere formatting, life formatting, features formatting, article selection)
- Description grammar (no raw "None" for life/atmosphere, Rogue Planets avoid star references, correct a/an articles, singular/plural verb agreement, habitability uses distance)

## Changelog

### v1.2.0 — Bug fixes and improvements

**Grammar fixes in description templates:**
- Fixed singular/plural verb agreement: replaced "X defines/define its character" and "X awaits/await discovery" with agreement-free phrasing ("its notable features include X" and "Within, X await discovery")
- Fixed "feature includes" vs "features include" for single vs multiple features
- Fixed article agreement: "an orange star" instead of "a orange star" (K-class stars)
- Fixed article agreement: "an ice world", "an ocean world", "an ice giant" instead of "a ice world" etc.
- Fixed "None" life level rendering: now displays as "no known life" instead of raw "None" in all description templates
- Fixed "None" atmosphere rendering: now displays as "no atmosphere" or "no atmosphere (detail)" instead of raw "None" in all description templates
- Fixed "where no atmosphere fills the atmosphere" → now says "where the atmosphere is absent"
- Fixed Rogue Planet descriptions: Rogue Planets now use star-less description templates instead of referencing a star they don't orbit

**Habitability scoring:**
- Added distance-from-star bonus: planets in the habitable zone (0.5–2.0 AU) get +5, moderately close/far (0.2–5.0 AU) get +2. Rogue planets receive no distance bonus.
- The `distance_au` parameter to `compute_habitability()` is now actually used in scoring (was previously unused)

**Code quality:**
- Added `_format_atmosphere()`, `_format_life()`, `_format_features()`, and `_article()` helper functions for clean, grammar-aware description generation
- Added 15 new tests covering format helpers and description grammar
- Version bumped to 1.2.0

## Extending

- Add new planet types by adding to `PLANET_TYPES`, `ATMOSPHERES`, `LIFE_LEVELS`, `FEATURES`, `HAZARDS`, `RESOURCES`, and `GLOBE_CHARS`
- Add new star types in `STAR_TYPES`
- Add naming flavors in `NAME_PREFIXES`, `NAME_SUFFIXES`, `DESCRIPTORS`
- Add moon descriptors in `MOON_NAMES_PRE`, `MOON_NAMES_SUF`

## License

MIT