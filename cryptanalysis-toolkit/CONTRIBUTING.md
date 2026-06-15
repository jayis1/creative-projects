# Contributing to Cryptanalysis Toolkit

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the [Issues](https://github.com/jayis1/creative-projects/issues).
2. If not, open a new issue with:
   - A clear title and description
   - Steps to reproduce
   - Expected vs. actual behavior
   - Python version and OS

### Adding New Ciphers

1. Create a new file in `cryptanalysis_toolkit/ciphers/` named after the cipher (e.g., `mycipher.py`).
2. Implement the cipher class with `encrypt()` and `decrypt()` methods.
3. Add comprehensive docstrings and type hints.
4. Add the cipher to `cryptanalysis_toolkit/ciphers/__init__.py`.
5. Add the cipher to `CIPHERS` dict in `cli.py`.
6. Write tests in `tests/test_mycipher.py`.
7. Update the README.md with the new cipher.

### Adding Analysis Tools

1. Create the module in `cryptanalysis_toolkit/analysis/`.
2. Follow the same pattern as existing analysis modules.
3. Export from `analysis/__init__.py`.
4. Add tests and update docs.

### Code Style

- Use **type hints** for all function signatures.
- Follow **PEP 8** style guidelines.
- Write **comprehensive docstrings** (Google style).
- Keep functions focused — one function, one purpose.
- Add comments for complex algorithms.

### Testing

- All new code must have tests.
- Run the full test suite before submitting:
  ```bash
  pytest tests/ -v
  ```
- Aim for >90% coverage on new code:
  ```bash
  pytest tests/ --cov=cryptanalysis_toolkit
  ```

### Pull Request Process

1. Fork the repository.
2. Create a feature branch.
3. Make your changes with clear commit messages.
4. Ensure all tests pass.
5. Submit a pull request with a description of changes.

## Development Setup

```bash
cd cryptanalysis-toolkit
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -e ".[dev]"
```

## Project Structure

```
cryptanalysis_toolkit/
├── ciphers/        # Cipher implementations
├── analysis/       # Analysis tools
├── breaker.py      # Cipher breaking logic
├── pipeline.py     # Batch processing & pipeline
└── cli.py          # Command-line interface
tests/              # Test suite
examples/           # Usage examples
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.