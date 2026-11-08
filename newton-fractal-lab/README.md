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

Run tests:

    python3 -m unittest discover -s tests -v

Coordinates, polynomial coefficients, candidate roots, iteration cap, tolerance, and damping are configurable through the Python API. No external packages or network access are required.
