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

`--terms` controls retained Fourier vectors (default 12); `--samples` controls SVG polyline smoothness (default 400). Add `--resample 128` to first make 128 uniformly spaced samples around the closed stroke, including its final-to-first segment; this reduces speed bias from unevenly spaced sketch points. Input coordinates must be finite numeric pairs; a repeated-point or degenerate stroke is supported.

## Library examples

```python
from main import dft, reconstruct, select_terms
terms = dft([[0, 0], [1, 0], [1, 1], [0, 1]])
curve = reconstruct(select_terms(terms, 3), 200)
```

Run tests with `python3 -m unittest -v` from this directory. The suite checks exact DFT reconstruction, deterministic coefficient selection, finite SVG output for degenerate geometry, invalid coordinates, and periodic arc-length resampling.

## Known Issues (Resolved)

- Arc-length resampling originally omitted the closing segment, so the Fourier series received unevenly distributed samples and a discontinuity at the stroke boundary. A square regression case reproduced the defect; resampling now includes the closing edge by default. Pass `closed=False` to the library function only when an open stroke is intentionally desired.
- The CLI prevalidated JSON coordinates into complex values, then the DFT validator rejected those complex values. The end-to-end CLI regression test reproduced the failure; validation now happens at the DFT/resampling boundary without converting the source data twice.

## Limitations

The algorithm interpolates uniformly spaced samples in their given order: resample irregularly spaced sketches before analysis to avoid speed bias. The direct transform scales quadratically in point count. SVG output is a single unfilled stroke.
