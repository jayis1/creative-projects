# Contributing to BPE Tokenizer

Thank you for your interest in contributing! This document outlines the
process for contributing to the BPE Tokenizer project.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/bpe-tokenizer

# Create a virtual environment
python3 -m venv .venv
source .venv/bin activate

# Install in development mode with test dependencies
pip install -e ".[dev]"

# Optional: better Unicode regex support
pip install regex
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_improvement.py -v

# Run with coverage
pytest tests/ --cov=bpe_tokenizer --cov-report=term-missing
```

## Code Style

- **Type hints**: All public functions and methods must have type hints.
- **Docstrings**: All public classes and functions need docstrings
  (Google/numpy style, with Parameters/Attributes sections).
- **Line length**: 100 characters max.
- **Imports**: Use `from __future__ import annotations` at the top of
  each module for forward-reference type hints.
- **Testing**: Add tests for any new feature or bug fix. Aim for full
  coverage of new code paths.

## Pull Request Process

1. **Fork** the repository and create your branch from `main`.
2. **Write tests** for your changes.
3. **Run the test suite** — all tests must pass:
   ```bash
   pytest tests/ -v
   ```
4. **Update the README** if you add new features or change the API.
5. **Commit** with a clear message:
   ```
   Add <feature>: <description>
   Fix <bug>: <description>
   ```
6. **Open a pull request** describing the changes.

## Architecture

The project is organized into the following modules:

```
bpe_tokenizer/
├── tokenizer.py      # Core: BPE training, encoding, decoding
├── encoder.py        # Advanced: Unigram/Viterbi, BPE-dropout
├── wordpiece.py      # WordPiece (BERT-style) encoder
├── vocab.py          # Vocabulary data structures
├── pretokenize.py    # Pre-tokenizers (GPT-2/4/Llama-3 regex)
├── cache.py          # Thread-safe LRU encode cache
├── normalizer.py     # Text normalization (NFC, lowercase, etc.)
├── postprocess.py    # Truncation, attention masks
├── analyzer.py       # Tokenizer quality analysis
├── comparison.py     # Tokenizer comparison tool
├── config.py         # JSON/TOML config file support
├── progress.py       # Training progress callbacks
├── exceptions.py     # Custom exception hierarchy
├── logging_setup.py  # Centralized logging
└── cli.py            # 12-subcommand CLI
```

## Reporting Bugs

Please include:
- Python version
- Operating system
- Minimal code to reproduce the issue
- Expected vs actual output
- Error traceback (if any)

## License

By contributing, you agree that your contributions will be licensed under
the MIT License.