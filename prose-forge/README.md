# Prose Forge

A procedural narrative and text generation engine: context-free-grammar story generation, Markov chain text synthesis, character/plot generators, poetry templates, and interactive fiction scene assembly — all pure Python, no dependencies.

## Features

- **Grammar engine**: weighted CFG rules, recursive expansion, variable binding, conditional rules
- **Markov synthesizer**: character/token n-gram chains trained on arbitrary text corpora
- **Story architect**: three-act structure generator with story beats, plot points, and conflict escalation
- **Character forge**: procedural characters with traits, motivations, arcs, and relationships
- **Poetry lab**: haiku, sonnet, free-verse, and limerick generators with syllable counting
- **Scene assembler**: chains generated elements into coherent multi-paragraph narrative scenes
- **Name generator**: culture-aware fantasy/sci-fi/historical name construction
- **World seed**: setting generators (biomes, settlements, weather moods, time periods)
- **CLI**: 10 subcommands for each generation mode, batch output, JSON export, seed control
- **Reproducible**: deterministic output via explicit random seeds

## Installation

```bash
pip install -e .
```

Or run directly:

```bash
python -m prose_forge --help
```

## Quick Start

```bash
# Generate a short story
python -m prose_forge story --seed 42

# Generate a character
python -m prose_forge character --seed 7

# Compose a haiku
python -m prose_forge poem --form haiku --seed 3

# Generate 5 fantasy names
python -m prose_forge names --culture fantasy --count 5

# Train a Markov chain on a text file and generate text
python -m prose_forge markov --train corpus.txt --order 2 --length 200

# Assemble a full narrative scene
python -m prose_forge scene --seed 99

# Generate a world setting
python -m prose_forge world --seed 11

# Export everything as JSON
python -m prose_forge story --seed 42 --json
```

## Architecture

```
prose_forge/
  __init__.py        — package metadata
  grammar.py         — CFG engine with weighted rules and variable binding
  markov.py          — n-gram Markov chain text synthesizer
  story.py           — three-act story architect
  character.py       — procedural character generator with arcs
  poetry.py          — syllable counter and poetry form generators
  scene.py           — narrative scene assembler
  names.py           — culture-aware name generator
  world.py           — setting and world-building generators
  cli.py             — argparse CLI with 10 subcommands
```

## License

MIT