# generative-poetry

Procedural poetry generator for five classic forms — haiku, limerick, free verse, acrostic, and sonnet.
Built entirely from scratch: syllable counting, phonetic rhyme detection, themed vocabularies, and a
flexible engine with a clean CLI. No external NLP libraries required.

Author: jayis1

---

## Features

- **Five forms**: haiku (5-7-5), limerick (AABBA), free verse, acrostic, Shakespearean sonnet (14 lines)
- **Five themes**: nature, city, space, autumn, sea — each with unique noun/verb/adjective/adverb pools
- **Syllable counting**: heuristic CMU-style counting (silent-e, vowel groups, compound)
- **Rhyme detection**: phonetic tail matching for slant and exact rhymes
- **Reproducible output**: optional random seed
- **CLI**: generate single poems, collections, pipe into scripts
- **52 tests**: syllables, rhymes, vocabulary, all five forms, engine, CLI

---

## Quick start

```
cd generative-poetry
python3 cli.py haiku --theme nature
python3 cli.py limerick --theme city --seed 42
python3 cli.py free_verse --theme space --lines 8
python3 cli.py acrostic --keyword OCEAN --theme sea
python3 cli.py sonnet --theme autumn
python3 cli.py random --count 3
```

List themes:

```
python3 cli.py --themes
```

---

## CLI reference

```
usage: poetry [-h] [-t THEME] [-k KEYWORD] [-n N] [-l L] [-s SEED] [--themes]
              [{haiku,limerick,free_verse,acrostic,sonnet,random}]

positional arguments:
  form          Poem form (default: random)

options:
  -t, --theme   Vocabulary theme (nature|city|space|autumn|sea)
  -k, --keyword Keyword for acrostic poems
  -n, --count   Number of poems to generate (default: 1)
  -l, --lines   Number of lines for free verse (default: random 6-12)
  -s, --seed    Random seed for reproducibility
  --themes      List available themes and exit
```

---

## Python API

```python
from poetry_gen import PoetryEngine

engine = PoetryEngine(theme="space", seed=7)

print(engine.haiku())
print(engine.free_verse(n_lines=6))
print(engine.acrostic(keyword="STAR"))
print(engine.sonnet())

# Generate a random collection
for poem in engine.collection(n=5):
    print(poem)
    print()
```

---

## Project layout

```
generative-poetry/
  poetry_gen/
    __init__.py          # Public API
    engine.py            # PoetryEngine + Poem dataclass
    vocabulary.py        # Vocabulary class + 5 built-in themes
    syllables.py         # Heuristic syllable counter
    rhyme.py             # Phonetic rhyme detection
    forms/
      __init__.py
      haiku.py           # 5-7-5 syllable generator
      limerick.py        # AABBA form
      free_verse.py      # Image-driven open form
      acrostic.py        # Keyword initial-letter form
      sonnet.py          # 14-line Shakespearean form
  tests/
    test_poetry.py       # 52 pytest tests
  cli.py                 # argparse CLI
  pyproject.toml
  README.md
```

---

## Running tests

```
cd generative-poetry
python3 -m pytest tests/ -v
```

---

## Extending

Add a new theme by appending an entry to `_THEMES` in `vocabulary.py` — each theme needs
`nouns`, `verbs`, `adjectives`, and `adverbs` lists.

Add a new form by creating a module under `poetry_gen/forms/` with a `generate(vocab)` function,
then register it in `forms/__init__.py` and `engine.py`.
