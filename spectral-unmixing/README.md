# Spectral Unmixing Lab

Estimate nonnegative proportions of known materials from a mixed spectral measurement. In 60 seconds, run the bundled demo and see a synthetic three-material mixture recovered from band measurements. Unlike a generic least-squares wrapper, this project uses a transparent projected-gradient solver with no numeric dependencies.

## How it works
Each column of `signatures` is a material response over measured bands. The solver minimizes the squared residual `||A x - y||²` subject to `x >= 0`, using a safe row-sum bound on the Gram matrix for its step size.

## Usage
Run from this directory:

    python3 unmix.py examples/mixture.json

Input JSON contains `signatures` (bands × materials) and `observed` (one value per band). Tune iterations with `--steps 5000`. Output includes estimated fractions, reconstructed bands, and an L2 residual quantifying mismatch. Python 3.9+, standard library only.

## Enhancements
- Report the reconstruction residual so fit quality is visible rather than inferred.
- Reject malformed dimensions, non-finite numbers, and zero-information signatures.


## Tests

    python3 -m unittest discover -s tests

## Known Issues (Resolved)
- Initial validation treated the band-major signature matrix as material-major, rejecting valid measurements. The recovery-mixture test exposed the mismatch; validation now requires one matrix row per observation, and the documented example runs successfully.
- The bug-hunt boundary suite verifies rejection of mismatched dimensions, non-finite values, zero-information signatures, and nonpositive iteration counts. No further confirmed defects were found.

## Non-goals
This educational tool does not perform instrument calibration, uncertainty quantification, or spectral library selection. Results depend on well-conditioned, representative signatures.
