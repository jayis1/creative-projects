# Fourier Sketch

Approximate a closed 2D drawing with rotating Fourier vectors (a truncated discrete Fourier series). The dependency-free Python tool reads sampled points from JSON and exports a scalable SVG curve.

## How it works

Treat each point `(x, y)` as a complex sample. The discrete Fourier transform (DFT) expresses the ordered, periodically repeated samples as complex coefficients indexed by signed frequency. The coefficient magnitude is the vector radius; its frequency determines rotation speed. Keeping the largest coefficients gives a compact approximation. The inverse series is evaluated at evenly spaced times and written as a polyline.

This is a direct, transparent O(N²) DFT, suited to sketches with tens to a few hundred samples rather than huge recordings.

## Usage

Requires Python 3.10+; no third-party packages.

Create `drawing.json`:

```json
{"points": [[0, 0], [1, 0], [1, 1], [0, 1]]}
```

Run:

```sh
python3 main.py drawing.json drawing.svg --terms 4 --samples 300
```

`--terms` controls retained Fourier vectors (default 12); `--samples` controls SVG polyline smoothness (default 400). Coordinates are closed periodically; the first point need not be duplicated. A straight-line or constant sketch is allowed. Input coordinates must be finite numeric pairs.

## Library examples

```python
from main import dft, reconstruct, select_terms
terms = dft([[0, 0], [1, 0], [1, 1], [0, 1]])
curve = reconstruct(select_terms(terms, 3), 200)
```

Run tests with `python3 -m unittest -v` from this directory. The suite checks exact DFT reconstruction, deterministic coefficient selection, finite SVG output for degenerate geometry, and invalid coordinates.

## Limitations

The algorithm interpolates uniformly spaced samples in their given order: resample irregularly spaced sketches before analysis to avoid speed bias. The direct transform scales quadratically in point count. SVG output is a single unfilled stroke.
