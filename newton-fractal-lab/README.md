# Newton Fractal Lab

A dependency-free complex-plane Newton basin renderer for polynomial roots. It performs damped Newton iteration, classifies convergence by root proximity, reports iteration counts, and renders deterministic ASCII or binary PPM output.

## How it works

For a polynomial `p(z)`, Newton's method iterates `z <- z - damping * p(z)/p'(z)`. Root candidates are supplied by the user; each pixel is independently iterated and classified as converged, divergent, or unresolved. Root ordering determines stable basin IDs. The renderer uses only the Python standard library.

## Usage

Run the built-in cubic demo:

    python3 newton_fractal.py --demo

Render an ASCII image:

    python3 newton_fractal.py --width 72 --height 32 --format ascii

Render PPM:

    python3 newton_fractal.py --width 160 --height 90 --format ppm --output newton.ppm

The renderer can be tuned with `--max-iterations` and `--damping`; add `--stats` to print per-basin pixel totals. For example:

    python3 newton_fractal.py --width 40 --height 20 --stats --damping 0.8

Run the existing `z^3 - 1` demo, or provide a JSON file to render another polynomial. Coefficients are ordered from highest to lowest degree; complex values use `[real, imaginary]` pairs:

    {"coefficients": [1, 0, 0, -1], "roots": [1, [-0.5, 0.8660254], [-0.5, -0.8660254]]}

Save this as `cubic.json`, then run:

    python3 newton_fractal.py --config cubic.json --width 80 --height 40 --stats

The config must contain exactly `coefficients` and `roots`, with at least two coefficients and one candidate root. Invalid or non-finite values are rejected with a CLI usage error. With no `--config`, the built-in cubic remains the default.

Run tests:

    python3 -m unittest discover -s tests -v

Known Issues (Resolved)

- Non-finite viewport coordinates such as NaN previously bypassed the increasing-bounds check and could silently generate an invalid image. `render` now rejects NaN and infinity; a regression test was observed failing before the fix and passes after it.

Remaining limitations: the CLI currently renders the built-in `z^3 - 1` polynomial; custom polynomial/root configuration is available through the Python API. Basin colors are categorical and not iteration-shaded.
