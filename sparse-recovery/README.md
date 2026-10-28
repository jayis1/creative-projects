# Sparse Recovery Lab

A dependency-free compressed-sensing toolkit that reconstructs sparse signals from fewer linear measurements using iterative hard thresholding (IHT), with deterministic synthetic demos and transparent convergence diagnostics.

## How it works

A seeded Gaussian sensing matrix maps a length-N signal to M measurements. IHT repeatedly takes a gradient step on squared measurement error, then keeps only the K largest-magnitude coefficients. A power iteration estimates the matrix's largest squared singular value to set a conservative step; each iteration records the residual norm.

## Usage

From this directory:

```sh
python3 -m sparse_recovery --demo
python3 -m unittest discover -s tests -v
```

The seeded demo prints JSON including the estimate, residual and reconstruction error. For custom experiments, pass `--json input.json`, where the file has `matrix`, `measurements`, and `sparsity` fields. Example:

```json
{"matrix": [[1.0, 0.0], [0.0, 1.0]], "measurements": [0.25, -0.5], "sparsity": 2}
```

The library exports `recover`, `gaussian_matrix`, `matvec`, and `sparse_signal` from `sparse_recovery.py`. `recover` returns a `RecoveryResult` containing the estimate, residual history, iteration count, and a tolerance-based convergence flag.

## Features

- Pure Python standard library; no network or external dependencies.
- Reproducible Gaussian sensing matrices and sparse signal generation.
- IHT reconstruction with caller-controlled iteration cap and tolerance.
- JSON input/output interface for custom experiments.
- Validation for dimensions, rectangular matrices, finite values, sparsity and iteration controls.
- Diagnostic residual history and reproducible CLI examples.

## Limitations

This educational reference implementation favors clarity over speed; dense matrix operations scale quadratically and are intended for modest dimensions. IHT is not guaranteed to recover every signal/matrix combination. Underdetermined systems may yield an approximation rather than the original vector; inspect reconstruction error and residual rather than assuming exact recovery.

## Known Issues (Resolved)

- Zero iteration counts previously permitted a meaningless result; they are now rejected (`test_invalid_iteration_limit`).
- All-zero measurement matrices could cause division by zero during step-size setup; they are now rejected with a clear validation error (`test_zero_energy_matrix`).
- Ragged matrices and nonfinite inputs could produce confusing downstream failures; explicit validation is covered by `test_rejects_ragged_matrix` and `test_rejects_nonfinite_input`.
