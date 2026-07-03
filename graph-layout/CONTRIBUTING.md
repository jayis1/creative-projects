# Contributing to graph-layout

Thank you for your interest in contributing! This guide covers the basics.

## Getting Started

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/graph-layout
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

## Running Tests

```bash
python3 -m pytest tests/ -v
```

All tests must pass before a PR is merged. Aim for full coverage of any new
code you add.

## Code Style

- Pure Python stdlib only — no external runtime dependencies.
- Use type hints (`from __future__ import annotations` at top).
- Add docstrings to all public functions and classes.
- Keep functions focused and small.

## Adding a New Layout Algorithm

1. Create your layout class in a new module (e.g. `my_layout.py`) or add to
   `advanced_layouts.py`.
2. Subclass `LayoutAlgorithm` and implement the `layout(self, graph, **kwargs)`
   method that assigns `x`/`y` to every `Node`.
3. Accept `width`, `height`, and `seed` constructor parameters for API
   consistency.
4. Export it from `__init__.py` and add it to the CLI `ALGORITHMS` dict.
5. Write tests in `tests/`.

## Adding a New Renderer

1. Implement a class with `render(graph) -> str` and `save(graph, path)`.
2. Export from `__init__.py` and add to the CLI `_save` dispatcher.

## Adding a New Graph Algorithm

Add to `algorithms.py` with type hints and a docstring. Add tests.

## Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] New code has docstrings and type hints
- [ ] README updated if user-facing API changed
- [ ] No external dependencies added