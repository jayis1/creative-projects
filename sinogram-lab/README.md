# Sinogram Lab

A dependency-free tomography sandbox for learners exploring computational imaging. Run `python3 -m sinogram_lab --demo` from this directory; it prints an ASCII reconstruction and a mean absolute error (MAE) against its known phantom. Lower MAE means closer pixel values. Unlike a generic image filter, this implements the forward measurement process and reconstructs from simulated projections using algebraic reconstruction (ART).

## How it works

`phantom()` creates a small asymmetric phantom. `project()` approximates parallel-beam line integrals at evenly spaced angles using bilinear samples through pixel centers. `reconstruct()` applies sequential ART: each ray's residual is distributed along its weights, normalized by the squared weight norm, with non-negativity projection. The demo adds seeded Gaussian measurement noise. This is educational discretized tomography, not a clinical imaging tool.

## Usage

```sh
python3 run.py --demo
python3 run.py --demo --size 16 --seed 19
python3 run.py --demo --output reconstruction.pgm
python3 -m unittest discover -s tests -v
```

The first command prints the size, scan geometry, seed, MAE, and an ASCII image. The second changes resolution and reproducible noise. Supported size is 2..128; the implementation is intended for small examples and runtime grows with image size, angle count, detector count, and iteration count.

## Testing

Run `python3 -m unittest discover -s tests -v`. Tests cover deterministic phantom/projections, a projection reconstruction invariant, ASCII rendering, PGM export, and invalid inputs. Only Python 3 standard library is required.

## Known Issues (Resolved)

- Explicit `detectors=0` was silently treated as the default detector count because zero is falsey. `test_zero_detectors_is_rejected` reproduced the issue; detector defaults now apply only when the argument is `None`, and zero raises `ValueError`.

## Why this version

It exposes both sides of a tomography problem—the measured sinogram and an iterative inverse—using only inspectable Python and a deterministic, headless output rather than hiding reconstruction behind a large imaging dependency.
