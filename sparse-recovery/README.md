# Sparse Recovery Lab

A dependency-free compressed-sensing toolkit that reconstructs sparse signals from fewer linear measurements using iterative hard thresholding (IHT), with deterministic synthetic demos and transparent convergence diagnostics.

## How it works

A seeded Gaussian sensing matrix maps a length-N signal to M measurements. IHT repeatedly takes a gradient step on squared measurement error, then keeps only the K largest-magnitude coefficients. The step size is derived from the matrix spectral norm, and the run reports residual history so convergence is inspectable.

## Usage

From this directory, run `python3 -m sparse_recovery --demo`. The seeded example prints measurement count, reconstruction error, and convergence information. To use the library, import `recover`, `gaussian_matrix`, and `matvec` from `sparse_recovery`.

Run tests with `python3 -m unittest discover -s tests -v`.

## Features

- Pure Python standard library; no network or dependencies.
- Reproducible Gaussian sensing matrices and sparse signal generation.
- IHT reconstruction, convergence tolerance, and iteration cap.
- Validated dimensions and finite numeric inputs.
- JSON CLI input/output for reproducible experiments.

## Limitations

This educational reference implementation favors clarity over speed; dense matrix operations scale quadratically and are intended for modest dimensions. IHT is not guaranteed to recover every signal/matrix combination.

## Known Issues (Resolved)

- The initial implementation accepted zero iterations and returned an uninitialized-looking estimate; validation now requires at least one iteration (`test_invalid_iteration_limit`).
- A zero measurement matrix caused a division by zero during step-size setup; reconstruction now rejects matrices with no positive spectral energy (`test_zero_energy_matrix`).
