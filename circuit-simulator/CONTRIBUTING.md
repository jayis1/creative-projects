# Contributing to Circuit Simulator

Thank you for your interest in contributing! Here are some guidelines to help you get started.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/circuit-simulator
   ```

2. Create a virtual environment and install:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   pip install -e ".[dev]"
   ```

3. Run the test suite:
   ```bash
   pytest tests/ -v
   ```

4. Try the demo:
   ```bash
   circuit-sim demo
   ```

## Project Structure

```
circuit-simulator/
├── circuit_sim/          # Main package
│   ├── __init__.py       # Package exports
│   ├── core.py           # Signal, Wire, Bus
│   ├── gates.py          # Combinational gates
│   ├── sequential.py     # Latches, flip-flops, clock
│   ├── circuit.py         # Circuit container & builders
│   ├── simulator.py      # Event-driven simulator
│   ├── cdl.py            # Circuit Description Language parser
│   ├── scope.py          # Oscilloscope & VCD export
│   ├── analyze.py        # Truth tables & statistics
│   ├── presets.py         # Pre-built circuits
│   ├── config.py         # Simulation configuration
│   ├── export.py         # JSON/DOT/ASCII export
│   ├── waveform.py       # Waveform comparison & analysis
│   └── cli.py            # Command-line interface
├── tests/                # Test suite
│   ├── test_circuit_sim.py
│   ├── test_bug_fixes.py
│   ├── test_bug_hunt.py
│   └── test_new_features.py
├── examples/             # Usage examples
├── .github/workflows/    # CI configuration
├── pyproject.toml        # Package configuration
├── LICENSE               # MIT license
└── README.md
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep lines under 100 characters

## Adding New Gates

1. Create a new gate class in `gates.py` that inherits from `Gate`
2. Implement `__init__()` and `evaluate()` methods
3. Add a convenience method in `Circuit` class (`circuit.py`)
4. Add CDL support in `cdl.py` if applicable
5. Add tests in `tests/test_circuit_sim.py`

## Adding New Sequential Elements

1. Create a new class in `sequential.py` that inherits from `Gate`
2. Implement state management and edge detection
3. Add to `Circuit` class and `__init__.py`
4. Add CDL support
5. Add tests

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_circuit_sim.py -v

# Run with coverage
pytest tests/ --cov=circuit_sim --cov-report=html
```

## Submitting Changes

1. Create a feature branch
2. Make your changes with tests
3. Ensure all tests pass: `pytest tests/ -v`
4. Push and create a pull request

## Reporting Issues

When reporting bugs, please include:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Any error messages or tracebacks