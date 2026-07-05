"""Julia-explorer: render a grid of Julia sets."""
from __future__ import annotations

import os

from .render import render_fractal
from .io_writers import write_png
from .viewport import Viewport


def explore_julia(grid_size=4, img_size=(150, 150), output_dir="julia_grid",
                  max_iter=150, palette_name="rainbow", power=2.0,
                  c_radius=1.5, workers=1):
    """Render a ``grid_size×grid_size`` grid of Julia sets.

    The Julia constant ``c`` is varied over a grid in the complex plane
    within radius ``c_radius``. Each cell is written as a separate PNG and
    an HTML index page is generated.
    """
    os.makedirs(output_dir, exist_ok=True)
    step = (2 * c_radius) / max(1, grid_size - 1)
    files = []
    w, h = img_size
    for r in range(grid_size):
        ci = -c_radius + r * step
        for c in range(grid_size):
            cr = -c_radius + c * step
            jc = complex(cr, ci)
            vp = Viewport(0 + 0j, 3.0, 3.0)
            pixels, _ = render_fractal("julia", vp, w, h, max_iter=max_iter,
                                        palette_name=palette_name, power=power,
                                        julia_c=jc, workers=workers)
            name = f"julia_r{r}_c{c}.png"
            write_png(os.path.join(output_dir, name), pixels, w, h,
                      text_meta={"julia_c": str(jc)})
            files.append(name)
    html = [f"<html><head><title>Julia Grid {grid_size}x{grid_size}</title>",
            "<style>img{{width:120px;height:120px;image-rendering:pixelated}}"
            " table{{border-collapse:collapse}} td{{padding:2px}}</style>",
            "</head><body>",
            f"<h1>Julia Set Grid ({grid_size}×{grid_size})</h1>",
            "<table>"]
    idx = 0
    for r in range(grid_size):
        html.append("<tr>")
        for c in range(grid_size):
            html.append(f'<td><img src="{files[idx]}"></td>')
            idx += 1
        html.append("</tr>")
    html.append("</table></body></html>")
    with open(os.path.join(output_dir, "index.html"), "w") as f:
        f.write("\n".join(html))
    return files