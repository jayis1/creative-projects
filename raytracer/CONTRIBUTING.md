# Contributing to raytracer

Thank you for your interest in improving **raytracer**! This document describes
how to set up a development environment and the conventions for contributing.

## Development setup

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/raytracer
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
python -m pytest tests/ -v
```

All tests must pass before a pull request is merged. The test suite is
organized into:

| File                         | Scope                                                |
|------------------------------|------------------------------------------------------|
| `test_raytracer.py`          | Core: Vec3, Ray, primitives, materials, BVH, camera  |
| `test_enhancements.py`       | v1.1: serialization, integrator modes, parallel      |
| `test_bug_hunt.py`           | Regression tests for fixed bugs                       |
| `test_v2_enhancements.py`    | v2.0: textures, new primitives, animation, logging   |

## Code style

* Pure Python 3.10+ — no external dependencies beyond Pillow (optional: PyYAML).
* Every public class and function has a docstring.
* Type hints are encouraged for public APIs.
* Keep the renderer deterministic when a seed is provided.
* All new features must include tests.
* Materials and primitives must be picklable (for multi-process rendering).

## Adding a new primitive

1. Subclass `Primitive` in `raytracer/primitive.py`.
2. Implement `hit(ray, tmin, tmax) -> Optional[HitRecord]` and `bbox() -> AABB`.
3. Add JSON/YAML/TOML support in `raytracer/serialize.py:build_object`.
4. Add tests in `tests/test_v2_enhancements.py`.

## Adding a new material

1. Subclass `Material` in `raytracer/material.py`.
2. Implement `scatter(ray_in, rec) -> Optional[(Vec3, Ray)]` and
   `emit(u, v, p) -> Vec3`.
3. Add JSON support in `raytracer/serialize.py:build_material`.
4. Add tests.

## Adding a new texture

1. Subclass `Texture` in `raytracer/texture.py`.
2. Implement `value(u, v, p) -> Vec3`.
3. Add JSON support in `raytracer/serialize.py:build_texture`.
4. Add tests.

## Adding a scene preset

1. Write a `build_<name>(aspect)` function in `raytracer/scene.py`.
2. Register it in `PRESETS` and `SCENES` (in `cli.py`).
3. Add tests in `TestNewPresets`.

## Reporting bugs

Open an issue with:
- A minimal scene (Python or JSON) that reproduces the bug.
- The exact command you ran.
- The output or error traceback.
- The raytracer version (`python -m raytracer.cli info`).