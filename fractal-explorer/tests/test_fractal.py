"""Fractal Explorer — Test Suite.

Tests for the core rendering, coloring, palettes, I/O, and edge cases.
Run with: ``python3 -m pytest tests/`` (or ``python3 tests/test_fractal.py``).
"""
from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import unittest

# Make the package importable when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fractal import (
    Viewport, render_fractal, render_mandelbrot_hp, write_png, write_ppm,
    write_ascii, get_palette, PALETTES, FRACTALS,
    _mandelbrot_iter, _julia_iter, _burning_ship_iter, _tricorn_iter,
    _newton_iter, _smooth_iter, _hsb_to_rgb, _lerp, _lerp_color,
    get_fractal, mandelbrot_decimal,
)


class TestPalettes(unittest.TestCase):
    def test_palette_size(self):
        for name in PALETTES:
            pal = get_palette(name, 64)
            self.assertEqual(len(pal), 64)
            for c in pal:
                self.assertEqual(len(c), 3)
                for ch in c:
                    self.assertTrue(0 <= ch <= 255, f"{name}: {c}")

    def test_custom_hex(self):
        pal = get_palette("#000000,#ffffff", 16)
        self.assertEqual(len(pal), 16)
        self.assertEqual(pal[0], (0, 0, 0))
        self.assertEqual(pal[-1], (255, 255, 255))

    def test_bad_palette(self):
        with self.assertRaises(ValueError):
            get_palette("nonexistent", 64)

    def test_grayscale_monotonic(self):
        pal = get_palette("grayscale", 32)
        for i in range(len(pal) - 1):
            self.assertLessEqual(pal[i][0], pal[i + 1][0])


class TestColorHelpers(unittest.TestCase):
    def test_lerp(self):
        self.assertAlmostEqual(_lerp(0, 10, 0), 0)
        self.assertAlmostEqual(_lerp(0, 10, 1), 10)
        self.assertAlmostEqual(_lerp(0, 10, 0.5), 5)

    def test_lerp_color(self):
        c = _lerp_color((0, 0, 0), (100, 200, 50), 0.5)
        self.assertEqual(c, (50, 100, 25))

    def test_hsb_black(self):
        self.assertEqual(_hsb_to_rgb(0, 0, 0), (0, 0, 0))
        self.assertEqual(_hsb_to_rgb(0, 0, 1), (255, 255, 255))


class TestViewport(unittest.TestCase):
    def test_ranges(self):
        vp = Viewport(1 + 1j, 2, 4)
        x0, x1 = vp.x_range()
        y0, y1 = vp.y_range()
        self.assertAlmostEqual(x0, 0)
        self.assertAlmostEqual(x1, 2)
        self.assertAlmostEqual(y0, -1)
        self.assertAlmostEqual(y1, 3)

    def test_auto_height(self):
        vp = Viewport(0, 4.0, None)
        self.assertAlmostEqual(vp.height, 4.0)


class TestIterations(unittest.TestCase):
    def test_mandelbrot_origin(self):
        # c = 0 is in the Mandelbrot set (never escapes)
        it, z2 = _mandelbrot_iter(0, 100, 1 << 16)
        self.assertEqual(it, 100)  # did not escape

    def test_mandelbrot_escape(self):
        # c = 2 + 0i escapes quickly
        it, z2 = _mandelbrot_iter(2, 100, 1 << 16)
        self.assertLess(it, 5)
        self.assertGreater(z2, 1 << 16)

    def test_julia_escape(self):
        it, _ = _julia_iter(2 + 0j, -0.7 + 0.27015j, 100, 1 << 16)
        self.assertLess(it, 100)

    def test_burning_ship(self):
        it, _ = _burning_ship_iter(2, 100, 1 << 16)
        self.assertLess(it, 10)

    def test_tricorn(self):
        it, _ = _tricorn_iter(2, 100, 1 << 16)
        self.assertLess(it, 10)
        # origin stays bounded
        it, _ = _tricorn_iter(0, 50, 1 << 16)
        self.assertEqual(it, 50)

    def test_newton_converges(self):
        # z^3 - 1 has roots 1, e^{2pi i/3}, e^{4pi i/3}
        it, root = _newton_iter(0.5, 100, 1 << 16, power=3)
        self.assertGreaterEqual(root, 0)
        self.assertLess(root, 3)

    def test_smooth_iter(self):
        # basic sanity: smooth value is non-negative and not crazy
        nu = _smooth_iter(50, 1 << 20, 1 << 16, math.log(2))
        self.assertGreater(nu, 0)


class TestRendering(unittest.TestCase):
    def test_render_dimensions(self):
        vp = Viewport(-0.5 + 0j, 3, 2)
        px, stats = render_fractal("mandelbrot", vp, 30, 20, max_iter=50)
        self.assertEqual(len(px), 30 * 20)
        for c in px:
            self.assertEqual(len(c), 3)

    def test_render_all_kinds(self):
        for kind in FRACTALS:
            vp = Viewport(0 + 0j, 3, 3)
            px, st = render_fractal(kind, vp, 15, 10, max_iter=30)
            self.assertEqual(len(px), 150, kind)

    def test_invalid_dims(self):
        vp = Viewport(0, 3, 2)
        with self.assertRaises(ValueError):
            render_fractal("mandelbrot", vp, 0, 10)
        with self.assertRaises(ValueError):
            render_fractal("mandelbrot", vp, 10, 0)

    def test_invalid_max_iter(self):
        vp = Viewport(0, 3, 2)
        with self.assertRaises(ValueError):
            render_fractal("mandelbrot", vp, 10, 10, max_iter=0)

    def test_unknown_fractal(self):
        with self.assertRaises(ValueError):
            get_fractal("does_not_exist")

    def test_coloring_modes(self):
        vp = Viewport(-0.5, 3, 2)
        for mode in ["smooth", "flat", "de"]:
            px, _ = render_fractal("mandelbrot", vp, 20, 15, max_iter=50,
                                    coloring=mode)
            self.assertEqual(len(px), 300)

    def test_interior_color(self):
        vp = Viewport(-0.5, 3, 2)
        px, _ = render_fractal("mandelbrot", vp, 20, 15, max_iter=20,
                                interior_color=(10, 20, 30))
        # at least one interior pixel (the origin area)
        self.assertIn((10, 20, 30), px)


class TestHighPrecision(unittest.TestCase):
    def test_decimal_basic(self):
        from decimal import Decimal
        it, z2 = mandelbrot_decimal(Decimal("0"), Decimal("0"), 100,
                                     Decimal(1 << 16), prec=30)
        self.assertEqual(it, 100)  # origin never escapes

    def test_hp_render(self):
        vp = Viewport(-0.5 + 0j, 0.01, 0.01)
        px, st = render_mandelbrot_hp(vp, 20, 15, max_iter=80, prec=30)
        self.assertEqual(len(px), 300)
        self.assertEqual(st["kind"], "mandelbrot-hp")


class TestIO(unittest.TestCase):
    def test_ppm(self):
        px = [(i % 256, (i * 2) % 256, (i * 3) % 256) for i in range(10)]
        with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
            path = f.name
        try:
            write_ppm(path, px, 5, 2)
            with open(path, "rb") as f:
                data = f.read()
            self.assertTrue(data.startswith(b"P6"))
        finally:
            os.unlink(path)

    def test_png_valid(self):
        px = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            write_png(path, px, 2, 2)
            with open(path, "rb") as f:
                data = f.read()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            w, h, bd, ct = struct.unpack(">IIBB", data[16:26])
            self.assertEqual(w, 2)
            self.assertEqual(h, 2)
            self.assertEqual(bd, 8)
            self.assertEqual(ct, 2)
        finally:
            os.unlink(path)

    def test_ascii(self):
        px = [(255, 255, 255), (0, 0, 0), (128, 128, 128), (200, 200, 200)]
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        try:
            write_ascii(path, px, 4, 1)
            with open(path) as f:
                txt = f.read()
            lines = txt.strip().split("\n")
            self.assertEqual(len(lines), 1)
            self.assertEqual(len(lines[0]), 4)
        finally:
            os.unlink(path)


class TestCLI(unittest.TestCase):
    def test_info(self):
        from fractal import build_cli
        parser = build_cli()
        # parse should not raise
        args = parser.parse_args(["info"])
        self.assertEqual(args.command, "info")


if __name__ == "__main__":
    unittest.main(verbosity=2)