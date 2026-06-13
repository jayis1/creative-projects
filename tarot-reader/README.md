# ✨ CLI Tarot Reader ✨

A beautifully rendered terminal tarot card reader with ASCII art cards, multiple spreads, full interpretations, and dramatic reveal animations. Pull cards from a complete 78-card Rider-Waite–style deck — all 22 Major Arcana and 56 Minor Arcana — right from your command line.

![Tarot](https://img.shields.io/badge/type-divination-9370DB) ![Python](https://img.shields.io/badge/python-3.8+-green) ![CLI](https://img.shields.io/badge/interface-CLI-blue) ![Version](https://img.shields.io/badge/version-1.2.0-blue)

## Features

- **Full 78-card deck** — All 22 Major Arcana with unique ASCII art, plus 56 Minor Arcana (Wands, Cups, Swords, Pentacles) with suit-specific art
- **5 spread types** — Single Card, Three Card (Past/Present/Future), Celtic Cross (10 cards), Relationship Spread (8 cards), Decision Spread (7 cards)
- **ASCII art card rendering** — Each Major Arcana card has hand-crafted ASCII art displayed in a bordered card frame with display-width-aware alignment
- **Reversed cards** — ~30% chance of reversal (configurable), with reversed meanings and flipped art
- **Narrative interpretations** — Every card has both keyword meanings and a poetic "story" interpretation
- **Elemental synthesis** — After a reading, the tool analyzes the elemental balance (Fire/Water/Air/Earth) and provides a synthesized interpretation
- **Astrological associations** — Major Arcana include zodiac signs, planetary rulers, and numerological meanings
- **Card browser** — Explore the full deck interactively, suit by suit
- **Card of the Day** — Quick daily draw with meaning and story
- **Dramatic animations** — Slow-print reveals and dramatic pauses for an atmospheric reading experience
- **Non-interactive mode** — Pipe-friendly quick readings for scripts and cron jobs
- **JSON output** — Machine-readable output for integrations (`--json`)
- **Save to file** — Write readings to a file (`--save FILE`)
- **Seeded RNG** — Reproducible readings with `--seed N`
- **Card lookup** — Search for any card by name with `--card NAME`

## How to Install

No external dependencies — just Python 3.8+:

```bash
# Clone and run directly
git clone <repo-url>
cd tarot-reader
python3 tarot_reader.py
```

Or make it executable:

```bash
chmod +x tarot_reader.py
./tarot_reader.py
```

## How to Run

### Interactive Mode (default)

```bash
python3 tarot_reader.py
```

This launches a full interactive session where you can:
1. Choose a spread and get a full reading with card-by-card reveals
2. Draw your Card of the Day
3. Browse the entire deck (Major Arcana + each suit)

### Quick Reading (non-interactive)

```bash
# Three-card spread
python3 tarot_reader.py --quick

# Celtic Cross spread
python3 tarot_reader.py --quick --spread cross

# Relationship spread
python3 tarot_reader.py --quick --spread relationship

# Decision spread
python3 tarot_reader.py --quick --spread decision
```

### Card of the Day (non-interactive)

```bash
python3 tarot_reader.py --daily
```

### Look Up a Card

```bash
python3 tarot_reader.py --card "Death"
python3 tarot_reader.py --card "3 of Cups"
python3 tarot_reader.py --card "fool" --json
```

### Save Readings

```bash
python3 tarot_reader.py --quick --save reading.txt
python3 tarot_reader.py --daily --save today.txt --json
```

### Reproducible Readings

```bash
# Same seed always gives the same draw
python3 tarot_reader.py --quick --seed 42
```

### Available Spreads

| Spread | Cards | Flag |
|--------|-------|------|
| Single Card | 1 | `--spread single` |
| Three Card (Past/Present/Future) | 3 | `--spread three_card` |
| Celtic Cross | 10 | `--spread cross` |
| Relationship | 8 | `--spread relationship` |
| Decision | 7 | `--spread decision` |

### All CLI Options

| Flag | Description |
|------|-------------|
| `--quick`, `-q` | Non-interactive quick reading |
| `--daily`, `-d` | Draw card of the day |
| `--spread`, `-s` | Spread type (default: `three_card`) |
| `--card`, `-c` | Look up a specific card by name |
| `--major-only` | Only draw from Major Arcana |
| `--seed` | RNG seed for reproducible readings |
| `--json`, `-j` | Output as JSON |
| `--save` | Save reading to a file |
| `--reversal-rate` | Probability of reversed cards, 0.0–1.0 (default: 0.3) |
| `--version`, `-V` | Show version |

## Usage Examples

```bash
# Quick three-card reading
$ python3 tarot_reader.py --quick --seed 42
✨ Three Card Spread ✨
Date: 2026-06-13 03:28

Past: 🏺 Temperance (Reversed)
  → Imbalance, excess, self-healing, realignment, re-evaluation
  One vessel overflows while the other runs dry...

Present: 👑 The Empress (Reversed)
  → Creative block, dependence, emptiness, smothering
  The garden withers. You give until you are empty...

Future: 💧 2 of Cups (Reversed)
  → Blocked or distorted balance in the realm of emotions...

# Daily card
$ python3 tarot_reader.py --daily --seed 42
✨ Card of the Day ✨
🏺 Temperance (Reversed)
  Keywords: Imbalance, excess, self-healing, realignment, re-evaluation
  One vessel overflows while the other runs dry...

# Card lookup
$ python3 tarot_reader.py --card "Death"
✨ 💀 Death ✨
  ┌──────────────────────────────────────────┐
  │                 Upright                  │
  ├──────────────────────────────────────────┤
  │ 💀               Death                💀 │
  ...
```

## What It Does

The tarot reader simulates a complete Rider-Waite–style tarot deck reading:

1. **Deck creation** — Builds all 78 cards (22 Major + 56 Minor Arcana) with meanings, stories, and ASCII art
2. **Card drawing** — Randomly selects cards with proper shuffling (no duplicates within a reading), with configurable reversal probability
3. **Card rendering** — Displays each card in a framed ASCII art layout with name, orientation, keywords, and narrative — all display-width-aware so emoji and wide characters don't break the frame
4. **Reading synthesis** — After drawing all cards, analyzes the spread's overall energy: upright/reversed balance, Major Arcana presence, elemental distribution (Fire/Water/Air/Earth), and astrological associations
5. **Interactive browsing** — Explore every card in the deck, view both upright and reversed meanings

The readings are for entertainment and reflection. The real magic is what you bring to the interpretation.

## Changelog

### v1.2.0 — Bug fixes

- **Fixed: Card name line overflow** — Emoji characters (🃏💀☀ etc.) take 2 terminal display columns but Python's `len()` counts them as 1, causing the card name line to overflow the ASCII frame border. Added display-width-aware alignment using `unicodedata.east_asian_width()` so all 78 cards render with perfect frame alignment in both upright and reversed orientations.
- **Fixed: Position name overflow** — Long position names (e.g., "Challenge / Obstacle") could exceed the card frame width. Now truncated with ellipsis if too long.
- **Fixed: Word-wrap padding** — The meaning and story word-wrap used `len()` for padding calculations, causing lines with emoji to have incorrect padding. Now uses display-width-aware padding.
- **Fixed: Art centering** — ASCII art centering used `str.center()` which doesn't account for emoji display width, causing visual misalignment. Now uses display-width-aware centering.
- **Fixed: Splash screen alignment** — The "You hold all the power over the cards." line was 61 characters, breaking the 60-character splash box. Both text lines and the emoji title line now have exactly 60 characters.
- **Fixed: `find_card('')` bug** — Calling `find_card` with an empty string returned "The Fool" because `"" in "The Fool"` is True. Now returns `None` for empty or whitespace-only strings.
- **Fixed: `generate_synthesis([])` misleading** — Empty readings produced "A balance of upright and reversed cards" text. Now returns a clear "No cards were drawn" message.
- **Fixed: Save path crash** — Saving to a nonexistent directory (e.g., `--save /no/such/dir/file.txt`) crashed with an unhandled `FileNotFoundError`. Now prints a graceful error message to stderr and continues.