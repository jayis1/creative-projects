# Contributing to raft-sim

Thank you for your interest in improving the Raft consensus simulator! This
document outlines how to contribute effectively.

## Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/raft-sim
   ```

2. **Set up a virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run the existing tests**:
   ```bash
   pytest tests/ -v
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_v2_features.py -v

# Run with coverage
pytest tests/ --cov=raft --cov-report=term-missing
```

### Code Style

- Use **type hints** on all function signatures (Python 3.10+ syntax).
- Add **docstrings** to all public classes and functions.
- Keep lines under **100 characters** where practical.
- Follow PEP 8 naming conventions.

### Adding a New Feature

1. **Implement** the feature in a new or existing module under `raft/`.
2. **Export** new public symbols from `raft/__init__.py`.
3. **Add tests** in `tests/` — aim for at least 3 test cases per feature
   (happy path, edge case, error case).
4. **Update the README** with usage examples for the new feature.
5. **Run all tests** to ensure nothing is broken.
6. **Commit** with a descriptive message.

### Adding a New CLI Subcommand

1. Add a `cmd_<name>` function in `raft/cli.py`.
2. Register it with `sub.add_parser()` in `main()`.
3. Add a test that invokes `main(["<name>", ...])`.
4. Document it in the README's CLI section.

## Testing Guidelines

- **Deterministic tests**: Always pass a `seed` to `Cluster` and `NetworkConfig`
  to ensure reproducibility.
- **Isolation**: Each test should create its own cluster — don't share state.
- **Timeouts**: Use generous timeouts in `run_until_leader()` — simulation
  timing can vary across environments.
- **Invariant checks**: Use `check_all(cluster)` at the end of integration
  tests to verify safety properties.

## Architecture Overview

```
raft/
├── types.py         # Data types (LogEntry, RPC messages, NodeState)
├── snapshot.py      # SnapshotStore — log compaction
├── network.py       # Simulated network (latency, loss, partition)
├── node.py          # RaftNode — core consensus state machine
├── cluster.py       # Cluster driver — orchestrates nodes + network
├── prevote.py       # PreVote RPC messages (§6 optimization)
├── persistence.py   # JSON serialization for save/restore
├── visualizer.py    # ASCII visualization
├── scenarios.py     # Pre-defined failure scenarios
├── invariants.py    # Safety property checker
├── config.py        # YAML/JSON configuration support
├── metrics.py       # Metrics collection and export
├── logging_utils.py # Logging integration
└── cli.py           # Command-line interface
```

## Pull Request Checklist

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] New features have tests
- [ ] README is updated
- [ ] Code has type hints and docstrings
- [ ] No hardcoded secrets or credentials

## Reporting Bugs

When reporting a bug, please include:

1. The exact command or code that triggers the bug.
2. The expected behavior.
3. The actual behavior (including error messages).
4. The Python version and OS.
5. A minimal reproduction case if possible.

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.