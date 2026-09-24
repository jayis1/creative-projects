# Dependency Resolver

A deterministic package dependency solver built from scratch. It parses semantic versions, evaluates caret/tilde/comparison/wildcard constraints, and uses most-constrained-first backtracking to choose a compatible version for every transitive dependency.

This is deliberately different from the repository's parser, database, and solver projects: it models a practical package-manager problem with version semantics, graph expansion, and reproducible lock output rather than a general-purpose SAT/CSP engine.

## How it works

1. A JSON manifest supplies root dependencies and an in-memory package index.
2. `Version` implements semantic ordering, including prereleases.
3. `Requirement` turns range expressions into predicates.
4. `Resolver` expands dependencies and chooses the package with the fewest candidates first. Failed choices backtrack without mutating earlier state.
5. The CLI emits a sorted JSON lock mapping package names to selected versions.

Supported expressions include `*`, exact versions, `1.x`, `>=1.2.0`, `<2.0.0`, `^1.2.0`, `~1.2.0`, and comma/space-separated AND constraints.

## Usage

Python 3.10+ and the standard library are sufficient.

```bash
python3 resolver.py examples.json
python3 -m unittest discover -s tests -v
```

Example manifest:

```json
{
  "dependencies": {"app": "1.0.0"},
  "packages": [
    {"name": "app", "version": "1.0.0", "dependencies": {"core": "^1.0.0"}},
    {"name": "core", "version": "1.0.0"},
    {"name": "core", "version": "1.2.0"}
  ]
}
```

The command prints a stable mapping such as `{ "app": "1.0.0", "core": "1.2.0" }` (pretty-printed).

## Limitations

The index is supplied in one JSON file; it does not contact registries, evaluate peer/optional dependencies, or implement platform-specific packages. Those boundaries keep resolution deterministic and safe to run offline.
