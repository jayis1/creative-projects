# Architecture

`shape-grammar-city` is organized as a small stdlib-first package:

- `citygen.generator` builds the road network, water corridor, zoning pass, and landmark placement.
- `citygen.analysis` computes connectivity, routing, and validation metrics.
- `citygen.districts` groups contiguous land-use cells into named districts.
- `citygen.config` loads validated JSON/TOML generation profiles.
- `citygen.reports` emits self-contained HTML reports backed by inline SVG.
- `citygen.render` handles ASCII and SVG visualization.
- `citygen.cli` exposes operational workflows: generation, validation, routing, districts, batch comparison, and HTML reporting.

The package keeps generation deterministic by routing all randomness through a local `random.Random(seed)` instance.
