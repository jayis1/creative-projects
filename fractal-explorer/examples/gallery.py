"""Example gallery: render a few representative fractals to PNG/ASCII."""
from __future__ import annotations
import os
import sys

# Allow running from anywhere by adding the project root to sys.path.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fractal import (Viewport, render_fractal, render_mandelbrot_hp,
                      write_png, write_ascii)

OUT = os.path.join(os.path.dirname(__file__), "..", "gallery_output")
OUT = os.path.abspath(OUT)
os.makedirs(OUT, exist_ok=True)


def save(name, pixels, w, h, fmt="png"):
    path = os.path.join(OUT, name)
    if fmt == "png":
        write_png(path, pixels, w, h)
    elif fmt == "ascii":
        write_ascii(path, pixels, w, h)
    print("wrote", path)


def main():
    # 1. Classic Mandelbrot
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    px, _ = render_fractal("mandelbrot", vp, 500, 350, max_iter=300, palette_name="fire")
    save("mandelbrot.png", px, 500, 350)

    # 2. Julia set (dendrite)
    vp = Viewport(0 + 0j, 3.0, 2.0)
    px, _ = render_fractal("julia", vp, 500, 350, max_iter=300,
                            palette_name="ice", julia_c=-0.4 + 0.6j)
    save("julia_dendrite.png", px, 500, 350)

    # 3. Multibrot (power 5)
    vp = Viewport(0 + 0j, 3.0, 2.0)
    px, _ = render_fractal("mandelbrot", vp, 500, 350, max_iter=300,
                            palette_name="electric", power=5.0)
    save("multibrot5.png", px, 500, 350)

    # 4. Burning Ship
    vp = Viewport(-0.5 - 0.5j, 3.5, 2.5)
    px, _ = render_fractal("burning_ship", vp, 500, 350, max_iter=300,
                            palette_name="fire")
    save("burning_ship.png", px, 500, 350)

    # 5. Tricorn
    vp = Viewport(0 + 0j, 3.0, 2.0)
    px, _ = render_fractal("tricorn", vp, 500, 350, max_iter=300,
                            palette_name="rainbow")
    save("tricorn.png", px, 500, 350)

    # 6. Newton z^3 - 1
    vp = Viewport(0 + 0j, 4.0, 4.0)
    px, _ = render_fractal("newton", vp, 500, 350, max_iter=80,
                            palette_name="rainbow", coloring="root")
    save("newton_cubic.png", px, 500, 350)

    # 7. ASCII Mandelbrot
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    px, _ = render_fractal("mandelbrot", vp, 120, 40, max_iter=100,
                            palette_name="grayscale", coloring="flat")
    save("mandelbrot.txt", px, 120, 40, fmt="ascii")

    # 8. Deep zoom (high precision) into Seahorse Valley
    vp = Viewport(-0.745 + 0.105j, 0.0005, 0.0005)
    px, _ = render_mandelbrot_hp(vp, 300, 300, max_iter=600, prec=50,
                                   palette_name="fire")
    save("seahorse_hp.png", px, 300, 300)


if __name__ == "__main__":
    main()