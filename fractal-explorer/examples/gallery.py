"""Example gallery: render representative fractals from each category.

Run:  python3 examples/gallery.py

Output is written to examples/gallery_output/.
"""
from __future__ import annotations
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fractal_explorer import (
    Viewport, render_fractal, render_mandelbrot_hp, write_png, write_ascii,
    write_tga, render_buddhabrot, render_lyapunov, render_ifs,
    BARNSLEY_FERN, SIERPINSKI_TRIANGLE, apply_filter,
)

OUT = os.path.join(_HERE, "gallery_output")
os.makedirs(OUT, exist_ok=True)


def save(name, pixels, w, h, fmt="png"):
    path = os.path.join(OUT, name)
    if fmt == "png":
        write_png(path, pixels, w, h)
    elif fmt == "ascii":
        write_ascii(path, pixels, w, h)
    elif fmt == "tga":
        write_tga(path, pixels, w, h)
    print(f"  wrote {path}")


def main():
    print("Rendering gallery...")

    # 1. Classic Mandelbrot
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    px, _ = render_fractal("mandelbrot", vp, 500, 350, max_iter=300,
                            palette_name="fire")
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

    # 9. Distance-estimator coloring
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    px, _ = render_fractal("mandelbrot", vp, 500, 350, max_iter=500,
                            coloring="de", palette_name="magma")
    save("de_coloring.png", px, 500, 350)

    # 10. Orbit-trap (stripe)
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    from fractal_explorer import StripeTrap
    px, _ = render_fractal("mandelbrot", vp, 500, 350, max_iter=300,
                            coloring="trap", trap=StripeTrap(count=16),
                            palette_name="neon")
    save("stripe_trap.png", px, 500, 350)

    # 11. Buddhabrot
    vp = Viewport(-0.5 + 0j, 3.0, 2.5)
    px, _ = render_buddhabrot(vp, 400, 400, samples=100000, max_iter=500,
                               seed=42, palette_name="magma")
    save("buddhabrot.png", px, 400, 400)

    # 12. Lyapunov fractal
    px, _ = render_lyapunov(width=400, height=400, sequence="ABBA",
                             max_iter=400, palette_name="ocean")
    save("lyapunov.png", px, 400, 400)

    # 13. Barnsley Fern (IFS)
    px, _ = render_ifs(BARNSLEY_FERN, width=300, height=300,
                        iterations=100000, seed=42, palette_name="forest")
    save("barnsley_fern.png", px, 300, 300)

    # 14. Sierpinski Triangle (IFS)
    px, _ = render_ifs(SIERPINSKI_TRIANGLE, width=300, height=300,
                        iterations=50000, seed=42, palette_name="sunset")
    save("sierpinski.png", px, 300, 300)

    # 15. Edge detection filter on a Mandelbrot
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    px, _ = render_fractal("mandelbrot", vp, 300, 200, max_iter=200,
                            palette_name="grayscale", coloring="smooth")
    px = apply_filter(px, 300, 200, "edge")
    save("edge_filtered.png", px, 300, 200)

    # 16. TGA format
    vp = Viewport(-0.5 + 0j, 3.0, 2.0)
    px, _ = render_fractal("mandelbrot", vp, 200, 150, max_iter=100,
                            palette_name="fire")
    save("mandelbrot.tga", px, 200, 150, fmt="tga")

    print(f"\nGallery complete — {len(os.listdir(OUT))} files in {OUT}")


if __name__ == "__main__":
    main()