#!/usr/bin/env python3
"""
ASCII Fractal Explorer — Explore Mandelbrot, Julia, Burning Ship, and Tricorn
sets in your terminal.

Zoom, pan, switch fractals, change color palettes, save bookmarks, and export
renders to text files — all from the comfort of your keyboard.

Supports four fractal types:
  - Mandelbrot set: z = z² + c
  - Julia set: z = z² + c (with z₀ from coordinates)
  - Burning Ship: z = (|Re(z)| + i|Im(z)|)² + c
  - Tricorn: z = conj(z)² + c
"""

import argparse
import curses
import math
import os
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

__version__ = "2.0.0"

# ---------------------------------------------------------------------------
# Color palette definitions (each maps iteration 0..max_iter to a char + color)
# ---------------------------------------------------------------------------

PALETTES = OrderedDict()


def _make_gradient(name: str, stops: List[Tuple[int, int, int]],
                   chars: str = " .:-=+*#%@"):
    """Register a palette from RGB stops, interpolating across chars."""
    steps = len(chars)
    colors = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        seg = t * (len(stops) - 1)
        idx = min(int(seg), len(stops) - 2)
        frac = seg - idx
        r = int(stops[idx][0] + (stops[idx + 1][0] - stops[idx][0]) * frac)
        g = int(stops[idx][1] + (stops[idx + 1][1] - stops[idx][1]) * frac)
        b = int(stops[idx][2] + (stops[idx + 1][2] - stops[idx][2]) * frac)
        colors.append((chars[i], (r, g, b)))
    PALETTES[name] = colors


_make_gradient("fire",
    [(0, 0, 0), (128, 0, 0), (255, 60, 0), (255, 165, 0),
     (255, 255, 100), (255, 255, 255)])
_make_gradient("ocean",
    [(0, 0, 20), (0, 20, 80), (0, 80, 180), (40, 180, 255),
     (180, 240, 255), (255, 255, 255)])
_make_gradient("matrix",
    [(0, 0, 0), (0, 40, 0), (0, 120, 0), (0, 200, 0),
     (100, 255, 100), (220, 255, 220)])
_make_gradient("electric",
    [(0, 0, 30), (80, 0, 160), (160, 0, 255), (255, 0, 200),
     (255, 100, 255), (255, 255, 255)])
_make_gradient("earth",
    [(20, 10, 0), (60, 40, 0), (120, 80, 20), (60, 140, 40),
     (40, 180, 100), (200, 255, 200)])
_make_gradient("grayscale",
    [(0, 0, 0), (60, 60, 60), (120, 120, 120), (180, 180, 180),
     (220, 220, 220), (255, 255, 255)])
_make_gradient("neon",
    [(0, 0, 0), (255, 0, 80), (255, 0, 255), (0, 200, 255),
     (100, 255, 200), (255, 255, 255)])
_make_gradient("sunset",
    [(10, 0, 20), (80, 0, 60), (200, 40, 80), (255, 120, 50),
     (255, 200, 80), (255, 255, 220)])

# ---------------------------------------------------------------------------
# Fractal types
# ---------------------------------------------------------------------------

FRACTAL_TYPES = ["mandelbrot", "julia", "burningship", "tricorn"]

FRACTAL_DESCRIPTIONS = {
    "mandelbrot": "Classic z = z² + c",
    "julia": "z = z² + c with fixed c",
    "burningship": "z = (|Re(z)| + i|Im(z)|)² + c",
    "tricorn": "z = conj(z)² + c",
}


def compute_fractal(cx: float, cy: float, max_iter: int,
                    fractal_type: str = "mandelbrot",
                    julia_c: complex = 0 + 0j) -> Tuple[int, complex]:
    """
    Compute escape iteration and final z for a point in the complex plane.

    Returns (iteration_count, final_z) so that smooth coloring can reuse
    the final z value without recomputing the entire iteration.
    """
    if fractal_type == "julia":
        z = complex(cx, cy)
        c = julia_c
    elif fractal_type == "burningship":
        z = 0 + 0j
        c = complex(cx, cy)
    elif fractal_type == "tricorn":
        z = 0 + 0j
        c = complex(cx, cy)
    else:  # mandelbrot
        z = 0 + 0j
        c = complex(cx, cy)

    for i in range(max_iter):
        if z.real * z.real + z.imag * z.imag > 4.0:
            return i, z
        if fractal_type == "burningship":
            z = complex(abs(z.real), abs(z.imag))
            z = z * z + c
        elif fractal_type == "tricorn":
            z = z.conjugate()
            z = z * z + c
        else:
            z = z * z + c

    return max_iter, z


def smooth_color(iter_count: int, max_iter: int, z_final: complex) -> float:
    """
    Smooth iteration count for nicer gradients using log₂ escape.

    Takes the final z value directly (avoiding recomputation).
    """
    if iter_count >= max_iter:
        return float(max_iter)
    mag_sq = z_final.real * z_final.real + z_final.imag * z_final.imag
    if mag_sq <= 0:
        return float(iter_count)
    log_zn = math.log(mag_sq) / 2.0
    nu = math.log(log_zn / math.log(2)) / math.log(2)
    return iter_count + 1 - nu


# ---------------------------------------------------------------------------
# Interesting coordinate bookmarks
# ---------------------------------------------------------------------------

BOOKMARKS = OrderedDict([
    ("Seahorse Valley", {"center_x": -0.745, "center_y": 0.186, "zoom": 0.005}),
    ("Elephant Valley", {"center_x": 0.281, "center_y": 0.011, "zoom": 0.005}),
    ("Double Spiral", {"center_x": -0.743643, "center_y": 0.131826, "zoom": 0.0001}),
    ("Mini Mandelbrot", {"center_x": -1.768, "center_y": 0.002, "zoom": 0.001}),
    ("Lightning", {"center_x": -0.170337, "center_y": -1.06506, "zoom": 0.001}),
    ("Starfish", {"center_x": -0.374004, "center_y": 0.659792, "zoom": 0.001}),
])

# ---------------------------------------------------------------------------
# Viewport state
# ---------------------------------------------------------------------------


@dataclass
class Viewport:
    center_x: float = -0.5
    center_y: float = 0.0
    zoom: float = 1.5        # half-width of the view in complex coords
    max_iter: int = 100
    palette_name: str = "fire"
    fractal_type: str = "mandelbrot"
    julia: bool = False
    julia_cx: float = -0.7
    julia_cy: float = 0.27015
    smooth: bool = True
    ascii_mode: bool = True   # True = chars, False = half-blocks
    needs_redraw: bool = True

    @property
    def julia_c(self) -> complex:
        return complex(self.julia_cx, self.julia_cy)

    @property
    def aspect(self) -> float:
        # approximate terminal character aspect ratio
        return 0.5  # chars are ~2x tall as wide


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class Renderer:
    def __init__(self, stdscr: curses.window, vp: Viewport):
        self.stdscr = stdscr
        self.vp = vp
        self.palette = PALETTES[vp.palette_name]
        self._color_pairs: dict = {}
        self._next_pair = 1
        self._init_colors()
        self._render_time: float = 0.0

    def _init_colors(self):
        """Pre-register color pairs for the current palette."""
        self._color_pairs = {}
        self._next_pair = 1
        self.palette = PALETTES[self.vp.palette_name]
        for ch, (r, g, b) in self.palette:
            idx = self._next_pair
            try:
                curses.init_color(idx + 7, r * 1000 // 255,
                                  g * 1000 // 255, b * 1000 // 255)
            except curses.error:
                pass  # terminal doesn't support custom colors
            try:
                curses.init_pair(idx, idx + 7, curses.COLOR_BLACK)
            except curses.error:
                curses.init_pair(idx, curses.COLOR_WHITE, curses.COLOR_BLACK)
            self._color_pairs[(ch, (r, g, b))] = idx
            self._next_pair += 1

    def _get_color_pair(self, r: int, g: int, b: int) -> int:
        """Find the closest registered color for an RGB value."""
        best = None
        best_dist = float('inf')
        for ch, (cr, cg, cb) in self.palette:
            d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if d < best_dist:
                best_dist = d
                best = (ch, (cr, cg, cb))
        if best and best in self._color_pairs:
            return self._color_pairs[best]
        return 0

    def render(self):
        """Render the fractal into the terminal."""
        vp = self.vp
        h, w = self.stdscr.getmaxyx()
        # leave room for status bar
        draw_h = max(h - 2, 1)
        draw_w = w

        aspect = vp.aspect
        x_min = vp.center_x - vp.zoom
        x_max = vp.center_x + vp.zoom
        y_range = vp.zoom * draw_h / draw_w / aspect
        y_min = vp.center_y - y_range
        y_max = vp.center_y + y_range

        dx = (x_max - x_min) / draw_w
        dy = (y_max - y_min) / draw_h

        palette = self.palette
        n_colors = len(palette)
        fractal_type = vp.fractal_type
        julia_c = vp.julia_c
        max_iter = vp.max_iter
        use_smooth = vp.smooth

        try:
            self.stdscr.erase()
        except curses.error:
            return

        t_start = time.monotonic()

        for row in range(draw_h):
            cy = y_min + row * dy
            for col in range(draw_w):
                cx = x_min + col * dx
                it, z_final = compute_fractal(cx, cy, max_iter,
                                              fractal_type, julia_c)
                if it >= max_iter:
                    # inside the set
                    ch, (r, g, b) = palette[0]
                else:
                    if use_smooth:
                        raw = smooth_color(it, max_iter, z_final)
                        t = raw / max_iter
                    else:
                        t = it / max_iter
                    idx = int(t * (n_colors - 1))
                    idx = max(0, min(idx, n_colors - 1))
                    ch, (r, g, b) = palette[idx]

                pair = self._color_pairs.get((ch, (r, g, b)), 0)
                try:
                    self.stdscr.addch(row, col, ord(ch),
                                      curses.color_pair(pair))
                except curses.error:
                    pass

        self._render_time = time.monotonic() - t_start

        # Status bar
        fractal_name = vp.fractal_type.capitalize()
        if vp.fractal_type == "julia":
            fractal_name = f"Julia (c={vp.julia_cx:.4f}+{vp.julia_cy:.4f}i)"
        status = (f" {fractal_name} | ({vp.center_x:.6f}, {vp.center_y:.6f}) "
                  f"| {1 / vp.zoom:.1f}x | Iter:{max_iter} "
                  f"| {vp.palette_name} | "
                  f"{'smooth' if use_smooth else 'flat'} "
                  f"| {self._render_time * 1000:.0f}ms")

        try:
            self.stdscr.addstr(draw_h, 0, status[:w - 1], curses.A_REVERSE)
        except curses.error:
            pass

        help_line = (" Arrows:Pan +/-:Zoom F:Fractal P:Palette "
                     "I/Shift-I:Iter T:Smooth R:Reset E:Export B:Bookmark Q:Quit")
        try:
            self.stdscr.addstr(draw_h + 1, 0, help_line[:w - 1],
                                curses.A_DIM)
        except curses.error:
            pass

        self.stdscr.refresh()
        vp.needs_redraw = False


# ---------------------------------------------------------------------------
# Non-curses batch renderer (for --export mode)
# ---------------------------------------------------------------------------

def render_to_text(vp: Viewport, width: int = 120, height: int = 60) -> str:
    """Render fractal to plain text (ANSI color codes)."""
    palette = PALETTES[vp.palette_name]
    n_colors = len(palette)
    aspect = vp.aspect

    x_min = vp.center_x - vp.zoom
    x_max = vp.center_x + vp.zoom
    y_range = vp.zoom * height / width / aspect
    y_min = vp.center_y - y_range
    y_max = vp.center_y + y_range

    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height

    def ansi_color(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    RESET = "\033[0m"
    lines = []
    for row in range(height):
        cy = y_min + row * dy
        buf = ""
        for col in range(width):
            cx = x_min + col * dx
            it, z_final = compute_fractal(cx, cy, vp.max_iter,
                                          vp.fractal_type, vp.julia_c)
            if it >= vp.max_iter:
                ch, (r, g, b) = palette[0]
            else:
                if vp.smooth:
                    raw = smooth_color(it, vp.max_iter, z_final)
                    t = raw / vp.max_iter
                else:
                    t = it / vp.max_iter
                idx = int(t * (n_colors - 1))
                idx = max(0, min(idx, n_colors - 1))
                ch, (r, g, b) = palette[idx]
            buf += f"{ansi_color(r, g, b)}{ch}"
        lines.append(buf + RESET)

    # Legend
    fractal_name = vp.fractal_type.capitalize()
    if vp.fractal_type == "julia":
        fractal_name += f" (c={vp.julia_cx:.4f}+{vp.julia_cy:.4f}i)"
    lines.append(f"\n{fractal_name} | Center: ({vp.center_x:.6f}, "
                 f"{vp.center_y:.6f}) | Zoom: {1 / vp.zoom:.1f}x "
                 f"| Iter: {vp.max_iter} | Palette: {vp.palette_name}")
    return "\n".join(lines)


def render_to_plain_text(vp: Viewport, width: int = 120,
                         height: int = 60) -> str:
    """Render fractal to plain ASCII (no color codes)."""
    chars = " .:-=+*#%@"
    n = len(chars)

    aspect = vp.aspect
    x_min = vp.center_x - vp.zoom
    x_max = vp.center_x + vp.zoom
    y_range = vp.zoom * height / width / aspect
    y_min = vp.center_y - y_range
    y_max = vp.center_y + y_range
    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height

    lines = []
    for row in range(height):
        cy = y_min + row * dy
        buf = ""
        for col in range(width):
            cx = x_min + col * dx
            it, _ = compute_fractal(cx, cy, vp.max_iter,
                                    vp.fractal_type, vp.julia_c)
            if it >= vp.max_iter:
                buf += chars[0]
            else:
                t = it / vp.max_iter
                idx = int(t * (n - 1))
                idx = max(0, min(idx, n - 1))
                buf += chars[idx]
        lines.append(buf)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interactive mode (curses)
# ---------------------------------------------------------------------------

def show_bookmark_menu(stdscr: curses.window, vp: Viewport) -> Optional[dict]:
    """Show a bookmark selection overlay. Returns chosen bookmark or None."""
    h, w = stdscr.getmaxyx()
    names = list(BOOKMARKS.keys())
    selected = 0

    while True:
        stdscr.erase()
        lines = [
            "╔════════════════════════════════════════════╗",
            "║         Fractal Bookmarks                  ║",
            "╠════════════════════════════════════════════╣",
        ]
        for i, name in enumerate(names):
            bm = BOOKMARKS[name]
            marker = "►" if i == selected else " "
            line = f"║ {marker} {name:<20s} ({bm['center_x']:.3f}, {bm['center_y']:.3f})"
            line = line.ljust(45) + "║"
            lines.append(line)
        lines.append("╠════════════════════════════════════════════╣")
        lines.append("║ Enter:Jump  Esc/Q:Cancel                    ║")
        lines.append("╚════════════════════════════════════════════╝")

        start_row = max(0, (h - len(lines)) // 2)
        for i, line in enumerate(lines):
            col = max(0, (w - len(line)) // 2)
            attr = curses.A_BOLD if i == selected + 3 else curses.A_NORMAL
            try:
                stdscr.addstr(start_row + i, col, line, attr)
            except curses.error:
                pass
        stdscr.refresh()

        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        if key == -1:
            continue
        if key in (ord('q'), ord('Q'), 27):  # ESC
            return None
        if key in (curses.KEY_UP, ord('k'), ord('K')):
            selected = (selected - 1) % len(names)
        elif key in (curses.KEY_DOWN, ord('j')):
            # lowercase j for menu nav (not Julia preset)
            selected = (selected + 1) % len(names)
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            return BOOKMARKS[names[selected]]


def interactive_main(stdscr: curses.window, vp: Viewport):
    """Main interactive loop with curses."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    # Try to enable 256 colors and mouse
    try:
        curses.start_color()
        curses.use_default_colors()
    except Exception:
        pass

    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    except Exception:
        pass

    renderer = Renderer(stdscr, vp)
    vp.needs_redraw = True

    # Help overlay
    showing_help = False
    help_text = [
        "╔══════════════════════════════════════════════╗",
        "║          ASCII Fractal Explorer              ║",
        "╠══════════════════════════════════════════════╣",
        "║  Arrow Keys      Pan around                  ║",
        "║  + / -           Zoom in / out               ║",
        "║  F               Cycle fractal type            ║",
        "║  P               Cycle color palette           ║",
        "║  I / Shift+I     Increase / Decrease iter    ║",
        "║  T               Toggle smooth coloring       ║",
        "║  R               Reset view                   ║",
        "║  E               Export to file                ║",
        "║  B               Open bookmarks menu           ║",
        "║  J               Cycle Julia presets (Julia)  ║",
        "║  Shift+Arrows    Adjust Julia c parameter    ║",
        "║  Mouse click     Re-center on click point    ║",
        "║  H               Toggle this help              ║",
        "║  Q / Esc         Quit                         ║",
        "╠══════════════════════════════════════════════╣",
        "║  Fractal types:                               ║",
        "║    Mandelbrot · Julia · Burning Ship · Tricorn║",
        "╚══════════════════════════════════════════════╝",
    ]

    julia_presets = [
        (-0.7, 0.27015),
        (-0.8, 0.156),
        (0.285, 0.01),
        (-0.4, 0.6),
        (0.45, 0.1428),
        (-0.70176, -0.3842),
        (-0.835, -0.2321),
        (-0.1, 0.651),
    ]
    julia_preset_idx = 0

    PAN_STEP_SMALL = 0.05
    ZOOM_FACTOR = 1.5

    # Flash message support
    flash_msg = ""
    flash_until = 0.0

    while True:
        now = time.monotonic()
        if flash_msg and now > flash_until:
            flash_msg = ""
            vp.needs_redraw = True

        if vp.needs_redraw and not showing_help:
            renderer.render()
            if flash_msg:
                h, w = stdscr.getmaxyx()
                try:
                    stdscr.addstr(h // 2, max(0, (w - len(flash_msg)) // 2),
                                  flash_msg, curses.A_REVERSE | curses.A_BOLD)
                    stdscr.refresh()
                except curses.error:
                    pass

        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        # Handle mouse click
        if key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, _ = curses.getmouse()
                # Convert screen coords to complex coords
                h, w = stdscr.getmaxyx()
                draw_h = max(h - 2, 1)
                draw_w = w
                x_min = vp.center_x - vp.zoom
                y_range = vp.zoom * draw_h / draw_w / vp.aspect
                y_min = vp.center_y - y_range
                vp.center_x = x_min + (mx / draw_w) * 2 * vp.zoom
                vp.center_y = y_min + (my / draw_h) * 2 * y_range
                vp.needs_redraw = True
                continue
            except Exception:
                continue

        if key == -1:
            continue

        # Quit
        if key in (ord('q'), ord('Q'), 27):  # 27 = ESC
            if showing_help:
                showing_help = False
                vp.needs_redraw = True
                continue
            break

        # Help
        if key in (ord('h'), ord('H')):
            showing_help = not showing_help
            if showing_help:
                stdscr.erase()
                h, w = stdscr.getmaxyx()
                start_row = max(0, (h - len(help_text)) // 2)
                for i, line in enumerate(help_text):
                    col = max(0, (w - len(line)) // 2)
                    try:
                        stdscr.addstr(start_row + i, col, line,
                                      curses.A_BOLD)
                    except curses.error:
                        pass
                stdscr.refresh()
            else:
                vp.needs_redraw = True
            continue

        if showing_help:
            continue

        # Movement (arrow keys + WASD without conflict)
        if key == curses.KEY_UP or key == ord('w') or key == ord('W'):
            vp.center_y -= vp.zoom * PAN_STEP_SMALL
            vp.needs_redraw = True
        elif key == curses.KEY_DOWN or key == ord('x') or key == ord('X'):
            vp.center_y += vp.zoom * PAN_STEP_SMALL
            vp.needs_redraw = True
        elif key == curses.KEY_LEFT or key == ord('a') or key == ord('A'):
            vp.center_x -= vp.zoom * PAN_STEP_SMALL
            vp.needs_redraw = True
        elif key == curses.KEY_RIGHT or key == ord('d') or key == ord('D'):
            vp.center_x += vp.zoom * PAN_STEP_SMALL
            vp.needs_redraw = True

        # Smooth toggle (T key — no conflict)
        elif key == ord('t') or key == ord('T'):
            vp.smooth = not vp.smooth
            flash_msg = f" Smooth: {'ON' if vp.smooth else 'OFF'} "
            flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True

        # Zoom
        elif key in (ord('+'), ord('=')):
            vp.zoom /= ZOOM_FACTOR
            vp.max_iter = max(50, int(50 + 30 * math.log10(1 / vp.zoom + 1)))
            vp.needs_redraw = True
        elif key in (ord('-'), ord('_')):
            vp.zoom *= ZOOM_FACTOR
            vp.max_iter = max(50, int(50 + 30 * math.log10(1 / vp.zoom + 1)))
            vp.needs_redraw = True

        # Fractal type cycle
        elif key == ord('f') or key == ord('F'):
            idx = FRACTAL_TYPES.index(vp.fractal_type)
            vp.fractal_type = FRACTAL_TYPES[(idx + 1) % len(FRACTAL_TYPES)]
            if vp.fractal_type == "julia":
                vp.julia = True
            else:
                vp.julia = False
            flash_msg = f" Fractal: {vp.fractal_type.capitalize()} "
            flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True

        # Palette cycle
        elif key == ord('p') or key == ord('P'):
            names = list(PALETTES.keys())
            idx = names.index(vp.palette_name)
            vp.palette_name = names[(idx + 1) % len(names)]
            renderer = Renderer(stdscr, vp)
            flash_msg = f" Palette: {vp.palette_name.capitalize()} "
            flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True

        # Iterations
        elif key == ord('i'):
            vp.max_iter = min(5000, vp.max_iter + 50)
            flash_msg = f" Iterations: {vp.max_iter} "
            flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True
        elif key == ord('I'):
            vp.max_iter = max(20, vp.max_iter - 50)
            flash_msg = f" Iterations: {vp.max_iter} "
            flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True

        # Reset
        elif key == ord('r') or key == ord('R'):
            vp.center_x = -0.5 if vp.fractal_type == "mandelbrot" else 0.0
            if vp.fractal_type == "burningship":
                vp.center_x = -0.4
                vp.center_y = -0.6
            else:
                vp.center_y = 0.0
            vp.zoom = 1.5
            vp.max_iter = 100
            flash_msg = " View Reset "
            flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True

        # Julia presets
        elif key == ord('j') or key == ord('J'):
            julia_preset_idx = (julia_preset_idx + 1) % len(julia_presets)
            vp.julia_cx, vp.julia_cy = julia_presets[julia_preset_idx]
            vp.fractal_type = "julia"
            vp.julia = True
            name = ["Dendrite", "Spiral", "Siegel Disk", "Rabbit",
                    "San Marco", "Lightning", "Dragon", "Starfish"]
            flash_msg = (f" Julia: {name[julia_preset_idx]} "
                         f"({vp.julia_cx:.4f}+{vp.julia_cy:.4f}i) ")
            flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True

        # Bookmarks
        elif key == ord('b') or key == ord('B'):
            bm = show_bookmark_menu(stdscr, vp)
            if bm:
                vp.center_x = bm["center_x"]
                vp.center_y = bm["center_y"]
                vp.zoom = bm["zoom"]
                flash_msg = f" Jumped to bookmark "
                flash_until = time.monotonic() + 1.5
            vp.needs_redraw = True

        # Export
        elif key == ord('e') or key == ord('E'):
            fname = os.path.expanduser("~/fractal_export.txt")
            try:
                output = render_to_text(vp)
                with open(fname, "w") as f:
                    f.write(output)
                flash_msg = f" Exported to {fname} "
            except OSError as exc:
                flash_msg = f" Export failed: {exc} "
            flash_until = time.monotonic() + 2.0
            vp.needs_redraw = True

        # Shift+Arrows for Julia c parameter
        elif key == 0x102:  # shift up
            vp.julia_cy += 0.01
            vp.needs_redraw = True
        elif key == 0x103:  # shift down
            vp.julia_cy -= 0.01
            vp.needs_redraw = True
        elif key == 0x104:  # shift left
            vp.julia_cx -= 0.01
            vp.needs_redraw = True
        elif key == 0x105:  # shift right
            vp.julia_cx += 0.01
            vp.needs_redraw = True


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ASCII Fractal Explorer — Explore Mandelbrot, Julia, "
                    "Burning Ship, and Tricorn sets in your terminal.",
        epilog="Examples:\n"
               "  %(prog)s                                    # Interactive mode\n"
               "  %(prog)s --fractal burningship              # Burning Ship fractal\n"
               "  %(prog)s --export out.txt --palette neon    # Export with neon palette\n"
               "  %(prog)s --list-presets                     # Show Julia presets\n",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("--fractal", type=str, default="mandelbrot",
                        choices=FRACTAL_TYPES,
                        help="Fractal type (default: mandelbrot)")
    parser.add_argument("--julia", action="store_true",
                        help="Start in Julia set mode (shorthand for "
                             "--fractal julia)")
    parser.add_argument("--julia-c", type=str, default=None,
                        help="Julia c parameter as 'real,imag' "
                             "(e.g. '-0.7,0.27015')")
    parser.add_argument("--center", type=str, default=None,
                        help="Center as 'x,y' (e.g. '-0.5,0')")
    parser.add_argument("--zoom", type=float, default=None,
                        help="Initial zoom level (half-width in complex "
                             "coords)")
    parser.add_argument("--iter", type=int, default=None,
                        help="Maximum iterations")
    parser.add_argument("--palette", type=str, default=None,
                        choices=list(PALETTES.keys()),
                        help="Color palette name")
    parser.add_argument("--smooth", action="store_true", default=True,
                        help="Enable smooth coloring (default)")
    parser.add_argument("--no-smooth", action="store_true",
                        help="Disable smooth coloring")
    parser.add_argument("--export", type=str, default=None,
                        help="Export to file and exit (non-interactive)")
    parser.add_argument("--width", type=int, default=120,
                        help="Width for export mode (default: 120)")
    parser.add_argument("--height", type=int, default=60,
                        help="Height for export mode (default: 60)")
    parser.add_argument("--plain", action="store_true",
                        help="Plain text export (no ANSI colors)")
    parser.add_argument("--no-curses", action="store_true",
                        help="Print fractal to terminal directly (no curses)")
    parser.add_argument("--list-presets", action="store_true",
                        help="List available Julia presets and exit")
    parser.add_argument("--list-palettes", action="store_true",
                        help="List available color palettes and exit")
    parser.add_argument("--list-bookmarks", action="store_true",
                        help="List interesting coordinate bookmarks and exit")

    args = parser.parse_args()

    # Handle list commands
    if args.list_presets:
        presets = [
            ("Dendrite", -0.7, 0.27015),
            ("Spiral", -0.8, 0.156),
            ("Siegel Disk", 0.285, 0.01),
            ("Rabbit", -0.4, 0.6),
            ("San Marco", 0.45, 0.1428),
            ("Lightning", -0.70176, -0.3842),
            ("Dragon", -0.835, -0.2321),
            ("Starfish", -0.1, 0.651),
        ]
        print("Julia set presets:")
        print(f"  {'Name':<15s} {'Real':>10s} {'Imag':>10s}")
        print("  " + "-" * 37)
        for name, r, i in presets:
            print(f"  {name:<15s} {r:>10.5f} {i:>10.5f}")
        return

    if args.list_palettes:
        print("Available color palettes:")
        for name in PALETTES:
            chars = "".join(ch for ch, _ in PALETTES[name])
            print(f"  {name:<12s}  {chars}")
        return

    if args.list_bookmarks:
        print("Interesting coordinate bookmarks:")
        print(f"  {'Name':<20s} {'Center X':>12s} {'Center Y':>12s} {'Zoom':>10s}")
        print("  " + "-" * 56)
        for name, bm in BOOKMARKS.items():
            print(f"  {name:<20s} {bm['center_x']:>12.6f} "
                  f"{bm['center_y']:>12.6f} {bm['zoom']:>10.6f}")
        return

    vp = Viewport()

    if args.julia:
        vp.fractal_type = "julia"
        vp.julia = True
    if args.fractal != "mandelbrot" or args.julia:
        if args.fractal == "julia":
            vp.fractal_type = "julia"
            vp.julia = True
        else:
            vp.fractal_type = args.fractal
            vp.julia = False
    if args.julia_c:
        parts = args.julia_c.split(",")
        vp.julia_cx = float(parts[0])
        vp.julia_cy = float(parts[1])
        vp.julia = True
        vp.fractal_type = "julia"
    if args.center:
        parts = args.center.split(",")
        vp.center_x = float(parts[0])
        vp.center_y = float(parts[1])
    if args.zoom is not None:
        vp.zoom = args.zoom
    if args.iter is not None:
        vp.max_iter = args.iter
    if args.palette:
        vp.palette_name = args.palette
    if args.no_smooth:
        vp.smooth = False

    # Adjust defaults for Burning Ship (different interesting center)
    if vp.fractal_type == "burningship" and args.center is None and not args.julia:
        vp.center_x = -0.4
        vp.center_y = -0.6

    # Non-interactive export
    if args.export:
        if args.plain:
            output = render_to_plain_text(vp, args.width, args.height)
        else:
            output = render_to_text(vp, args.width, args.height)
        try:
            with open(args.export, "w") as f:
                f.write(output)
            print(f"Fractal exported to {args.export}")
        except OSError as exc:
            print(f"Error writing to {args.export}: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    # Direct terminal print (no curses)
    if args.no_curses:
        try:
            w, h = os.get_terminal_size()
            h = max(h - 2, 10)
        except OSError:
            w, h = args.width, args.height
        if args.plain:
            output = render_to_plain_text(vp, w, h)
        else:
            output = render_to_text(vp, w, h)
        print(output)
        return

    # Interactive curses mode
    curses.wrapper(interactive_main, vp)


if __name__ == "__main__":
    main()