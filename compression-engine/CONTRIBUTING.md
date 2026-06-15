# Contributing to Compression Engine

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/compression-engine
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or: .venv\Scripts\activate  # Windows
   ```

3. **Install for development:**
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a specific test file
python3 -m pytest tests/test_huffman.py -v

# Run with coverage
python3 -m pytest tests/ --cov=compression_engine
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Add docstrings to all public functions, classes, and modules
- Keep lines under 100 characters
- Use `from __future__ import annotations` for modern type hint syntax

## Adding a New Codec

1. Create a new file `compression_engine/your_codec.py`
2. Inherit from `Codec` base class in `base.py`
3. Implement `compress()` and `decompress()` methods
4. Add CRC32 integrity verification (use `compute_crc32` and `verify_crc32` from `base.py`)
5. Register in `CODEC_REGISTRY` in `pipeline.py`
6. Add to `__init__.py` exports
7. Add to `CODECS` dict in `cli.py`
8. Write comprehensive tests in `tests/test_your_codec.py`

### Codec Template

```python
from .base import Codec, IntegrityError, FormatError, compute_crc32, verify_crc32

class MyCodec(Codec):
    """My custom compression codec with CRC32 integrity."""

    name = "mycodec"

    def compress(self, data: bytes) -> bytes:
        checksum = compute_crc32(data)
        # ... compress data ...
        # Store original length + CRC32 in header
        return compressed

    def decompress(self, data: bytes) -> bytes:
        # Parse header (original length + CRC32)
        # ... decompress ...
        verify_crc32(result, expected_checksum, "mycodec decompression")
        return result
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Ensure all tests pass: `python3 -m pytest tests/ -v`
4. Add tests for any new features or bug fixes
5. Update documentation (README.md) if needed
6. Submit a pull request with a clear description

## Bug Reports

When filing a bug report, please include:

- Python version
- Operating system
- Minimal reproducible example
- Expected vs actual behavior
- Full error traceback

## License

By contributing, you agree that your contributions will be licensed under the MIT License.