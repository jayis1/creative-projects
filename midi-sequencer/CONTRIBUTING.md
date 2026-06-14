# Contributing to MIDI Step Sequencer

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Clone and install:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/midi-sequencer
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Run tests:**
   ```bash
   python -m pytest tests/ -v
   ```

3. **Try the CLI:**
   ```bash
   python -m sequencer info scales
   python -m sequencer generate euclidean --beats 5 --length 16 -o test.mid
   ```

## How to Contribute

### Adding New Features

- **New generators**: Add to `sequencer/generators.py` or create a new module
- **New scales/chords**: Add to `SCALE_INTERVALS` / `CHORD_INTERVALS` in `sequencer/scales.py`
- **New groove templates**: Add to `GROOVE_TEMPLATES` in `sequencer/grooves.py`
- **New drum patterns**: Add to `drum_pattern()` in `sequencer/generators.py` or `EXTENDED_DRUM_STYLES` in `sequencer/extended_drums.py`
- **New L-System presets**: Add to `PRESETS` in `sequencer/lsystem.py`
- **New chord progressions**: Add to `PROGRESSIONS` in `sequencer/progressions.py`
- **New preset songs**: Add to `PRESETS` in `sequencer/presets.py`

### Code Style

- Python 3.10+ compatible
- Use type hints for all function signatures
- Add docstrings with Args/Returns sections
- Keep functions focused — one responsibility per function
- Run `ruff check` before committing (if available)

### Testing

- All new features must include tests in `tests/`
- Use `unittest.TestCase` or plain `pytest` functions
- Test edge cases: empty inputs, boundary values, invalid inputs
- Run the full test suite before submitting

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Update documentation (README.md, docstrings)
6. Submit a PR with a clear description

## Project Structure

```
midi-sequencer/
├── sequencer/
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # python -m sequencer entry
│   ├── scales.py            # Music theory: scales, chords, notes
│   ├── patterns.py          # Core data structures: Step, Pattern, Track, Song
│   ├── generators.py        # Pattern generators: Euclidean, Markov, drums
│   ├── grooves.py           # Groove templates and velocity curves
│   ├── lsystem.py           # L-System pattern generation
│   ├── progressions.py      # Named chord progressions
│   ├── arrangement.py       # Multi-section song arrangement
│   ├── presets.py            # Ready-made song templates
│   ├── serialization.py      # JSON save/load
│   ├── export.py            # MIDI file export
│   ├── cli.py               # Command-line interface
│   ├── config.py            # Configuration management
│   ├── validation.py        # Input validation
│   ├── analysis.py          # Pattern/song analysis and visualization
│   ├── batch.py             # Batch composition tools
│   ├── playback.py          # MIDI playback support
│   ├── extended_drums.py    # Additional drum patterns
│   └── logging_setup.py     # Logging configuration
├── tests/
│   └── test_sequencer.py    # Comprehensive test suite
├── examples/                # Usage examples
├── pyproject.toml           # Package configuration
├── LICENSE                  # MIT license
└── README.md                # Documentation
```

## Ideas for Contributions

- [ ] Real-time MIDI input support
- [ ] MIDI file import and parsing
- [ ] Web-based UI (Flask/FastAPI)
- [ ] WAV/FLAC audio rendering via fluidsynth
- [ ] MIDI CC automation lanes
- [ ] Polyrhythmic pattern support
- [ ] Microtonal scale support
- [ ] MusicXML export
- [ ] Probability-based transition between sections
- [ ] Genetic algorithm for pattern evolution
- [ ] Neural network-based style transfer

## Questions?

Open an issue on GitHub or check the README for documentation.