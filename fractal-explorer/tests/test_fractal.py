"""Fractal Explorer — Test Suite.

Tests for the core rendering, coloring, palettes, fractals, I/O, parallel
rendering, deep zoom, orbit traps, and edge cases.

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
    Viewport, render_fractal, render_histogram_coloring, render_mandelbrot_hp,
    render_zoom_sequence, explore_julia, benchmark, write_png, write_ppm,
    write_ascii, write_svg, get_palette, PALETTES, FRACTALS, DE_CAPABLE,
    _mandelbrot_iter, _mandelbrot_de_iter, _julia_iter, _burning_ship_iter,
    _tricorn_iter, _celtic_iter, _phoenix_iter, _magnet_iter, _newton_iter,
    _smooth_iter, _true_distance, _hsb_to_rgb, _lerp, _lerp_color, _clamp_byte,
    get_fractal, mandelbrot_decimal, PointTrap, LineTrap, CircleTrap, CrossTrap,
    make_trap, TRAPS,
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

    def test_palette_size_zero(self):
        # size 0 should not crash (returns single black)
        pal = get_palette("fire", 0)
        self.assertEqual(len(pal), 1)

    def test_custom_hex_bad(self):
        with self.assertRaises(ValueError):
            get_palette("#zzzzzz", 16)

    def test_json_hex_list(self):
        pal = get_palette('["#ff0000","#00ff00","#0000ff"]', 8)
        self.assertEqual(len(pal), 8)
        self.assertEqual(pal[0], (255, 0, 0))


class TestColorHelpers(unittest.TestCase):
    def test_lerp(self):
        self.assertAlmostEqual(_lerp(0, 10, 0), 0)
        self.assertAlmostEqual(_lerp(0, 10, 1), 10)
        self.assertAlmostEqual(_lerp(0, 10, 0.5), 5)

    def test_lerp_color(self):
        c = _lerp_color((0, 0, 0), (100, 200, 50), 0.5)
        self.assertEqual(c, (50, 100, 25))

    def test_hsb_black_white(self):
        self.assertEqual(_hsb_to_rgb(0, 0, 0), (0, 0, 0))
        self.assertEqual(_hsb_to_rgb(0, 0, 1), (255, 255, 255))

    def test_hsb_red(self):
        # pure red is hue=0, sat=1, val=1
        self.assertEqual(_hsb_to_rgb(0, 1, 1), (255, 0, 0))

    def test_clamp_byte(self):
        self.assertEqual(_clamp_byte(-5), 0)
        self.assertEqual(_clamp_byte(300), 255)
        self.assertEqual(_clamp_byte(127), 127)


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

    def test_auto_height_aspect(self):
        vp = Viewport(0, 4.0, None, aspect=2.0)
        self.assertAlmostEqual(vp.height, 2.0)

    def test_zoom(self):
        vp = Viewport(-0.5, 3.0, 2.0)
        vp2 = vp.zoom(0.5)
        self.assertAlmostEqual(vp2.width, 1.5)
        self.assertAlmostEqual(vp2.height, 1.0)
        self.assertEqual(vp2.center, vp.center)
        # original is untouched
        self.assertAlmostEqual(vp.width, 3.0)

    def test_serialize(self):
        vp = Viewport(-0.5 + 0.1j, 3.0, 2.0)
        d = vp.to_dict()
        vp2 = Viewport.from_dict(d)
        self.assertEqual(vp2.center, vp.center)
        self.assertAlmostEqual(vp2.width, vp.width)
        self.assertAlmostEqual(vp2.height, vp.height)


class TestIterations(unittest.TestCase):
    def test_mandelbrot_origin(self):
        it, z2 = _mandelbrot_iter(0, 100, 1 << 16)
        self.assertEqual(it, 100)

    def test_mandelbrot_escape(self):
        it, z2 = _mandelbrot_iter(2, 100, 1 << 16)
        self.assertLess(it, 5)
        self.assertGreater(z2, 1 << 16)

    def test_mandelbrot_de(self):
        it, (z2, dz2) = _mandelbrot_de_iter(2, 100, 1 << 16)
        self.assertLess(it, 100)
        self.assertGreater(dz2, 0)

    def test_mandelbrot_de_interior(self):
        # c=0 is interior; should not crash and return final values
        it, (z2, dz2) = _mandelbrot_de_iter(0, 50, 1 << 16)
        self.assertEqual(it, 50)
        self.assertGreaterEqual(z2, 0)

    def test_julia_escape(self):
        it, _ = _julia_iter(2 + 0j, -0.7 + 0.27015j, 100, 1 << 16)
        self.assertLess(it, 100)

    def test_burning_ship(self):
        it, _ = _burning_ship_iter(2, 100, 1 << 16)
        self.assertLess(it, 10)

    def test_tricorn(self):
        it, _ = _tricorn_iter(2, 100, 1 << 16)
        self.assertLess(it, 10)
        it, _ = _tricorn_iter(0, 50, 1 << 16)
        self.assertEqual(it, 50)

    def test_celtic_escape(self):
        it, _ = _celtic_iter(2, 100, 1 << 16)
        self.assertLess(it, 10)

    def test_phoenix_escape(self):
        it, _ = _phoenix_iter(2, 50, 1 << 16)
        self.assertLess(it, 50)

    def test_magnet_escape(self):
        # c=0 converges to the attracting fixed point 0 quickly (escapes)
        it, _ = _magnet_iter(0, 100, 1 << 16)
        self.assertLess(it, 100)
        # c=3 stays bounded (interior) — does not escape
        it3, _ = _magnet_iter(3, 100, 1 << 16)
        self.assertEqual(it3, 100)

    def test_newton_converges(self):
        it, root = _newton_iter(0.5, 100, 1 << 16, power=3)
        self.assertGreaterEqual(root, 0)
        self.assertLess(root, 3)

    def test_smooth_iter(self):
        nu = _smooth_iter(50, 1 << 20, 1 << 16, math.log(2))
        self.assertGreater(nu, 0)

    def test_smooth_iter_zero(self):
        self.assertEqual(_smooth_iter(0, 0, 1 << 16, math.log(2)), 0.0)

    def test_true_distance_positive(self):
        d = _true_distance(1e6, 1e4, math.log(2))
        self.assertGreater(d, 0)

    def test_true_distance_zero(self):
        self.assertEqual(_true_distance(0, 0, math.log(2)), 0.0)


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

    def test_invalid_palette_size(self):
        vp = Viewport(0, 3, 2)
        with self.assertRaises(ValueError):
            render_fractal("mandelbrot", vp, 10, 10, palette_size=0)

    def test_invalid_supersample(self):
        vp = Viewport(0, 3, 2)
        with self.assertRaises(ValueError):
            render_fractal("mandelbrot", vp, 10, 10, supersample=0)

    def test_invalid_workers(self):
        vp = Viewport(0, 3, 2)
        with self.assertRaises(ValueError):
            render_fractal("mandelbrot", vp, 10, 10, workers=0)

    def test_unknown_fractal(self):
        with self.assertRaises(ValueError):
            get_fractal("does_not_exist")

    def test_coloring_modes(self):
        vp = Viewport(-0.5, 3, 2)
        for mode in ["smooth", "flat", "de", "trap"]:
            px, _ = render_fractal("mandelbrot", vp, 20, 15, max_iter=50,
                                    coloring=mode)
            self.assertEqual(len(px), 300, mode)

    def test_interior_color(self):
        vp = Viewport(-0.5, 3, 2)
        px, _ = render_fractal("mandelbrot", vp, 20, 15, max_iter=20,
                                interior_color=(10, 20, 30))
        self.assertIn((10, 20, 30), px)

    def test_supersample(self):
        vp = Viewport(-0.5, 3, 2)
        px1, _ = render_fractal("mandelbrot", vp, 20, 15, max_iter=40)
        px2, _ = render_fractal("mandelbrot", vp, 20, 15, max_iter=40,
                                  supersample=2)
        self.assertEqual(len(px1), len(px2))

    def test_histogram_coloring(self):
        vp = Viewport(-0.5, 3, 2)
        px, st = render_histogram_coloring("mandelbrot", vp, 20, 15, max_iter=50)
        self.assertEqual(len(px), 300)

    def test_histogram_invalid(self):
        vp = Viewport(0, 3, 2)
        with self.assertRaises(ValueError):
            render_histogram_coloring("mandelbrot", vp, 0, 10)
        with self.assertRaises(ValueError):
            render_histogram_coloring("mandelbrot", vp, 10, 10, max_iter=0)

    def test_workers_parallel(self):
        # single-process fallback path still works
        vp = Viewport(-0.5, 3, 2)
        px, st = render_fractal("mandelbrot", vp, 20, 15, max_iter=40, workers=1)
        self.assertEqual(len(px), 300)


class TestOrbitTraps(unittest.TestCase):
    def test_point_trap(self):
        t = PointTrap(0 + 0j)
        self.assertEqual(t.distance(0 + 0j), 0)
        self.assertGreater(t.distance(1 + 0j), 0)

    def test_line_trap(self):
        t = LineTrap(0.0)
        # point on x-axis is distance 0 from horizontal line
        self.assertEqual(t.distance(3 + 0j), 0)
        self.assertGreater(t.distance(0 + 1j), 0)

    def test_circle_trap(self):
        t = CircleTrap(1.0)
        self.assertEqual(t.distance(1 + 0j), 0)
        self.assertGreater(t.distance(2 + 0j), 0)

    def test_cross_trap(self):
        t = CrossTrap()
        self.assertEqual(t.distance(1 + 0j), 0)
        self.assertEqual(t.distance(0 + 1j), 0)
        self.assertGreater(t.distance(1 + 1j), 0)

    def test_make_trap(self):
        from fractal_explorer.traps import OrbitTrap
        for name in TRAPS:
            trap = make_trap(name)
            self.assertIsInstance(trap, OrbitTrap)

    def test_make_trap_bad(self):
        with self.assertRaises(ValueError):
            make_trap("nonexistent")

    def test_render_with_trap_object(self):
        vp = Viewport(-0.5, 3, 2)
        px, _ = render_fractal("mandelbrot", vp, 15, 10, max_iter=40,
                                coloring="trap", trap=CircleTrap())
        self.assertEqual(len(px), 150)


class TestHighPrecision(unittest.TestCase):
    def test_decimal_basic(self):
        from decimal import Decimal
        it, z2 = mandelbrot_decimal(Decimal("0"), Decimal("0"), 100,
                                     Decimal(1 << 16), prec=30)
        self.assertEqual(it, 100)

    def test_hp_render(self):
        vp = Viewport(-0.5 + 0j, 0.01, 0.01)
        px, st = render_mandelbrot_hp(vp, 20, 15, max_iter=80, prec=30)
        self.assertEqual(len(px), 300)
        self.assertEqual(st["kind"], "mandelbrot-hp")

    def test_hp_invalid(self):
        vp = Viewport(0, 1, 1)
        with self.assertRaises(ValueError):
            render_mandelbrot_hp(vp, 0, 10)
        with self.assertRaises(ValueError):
            render_mandelbrot_hp(vp, 10, 10, max_iter=0)
        with self.assertRaises(ValueError):
            render_mandelbrot_hp(vp, 10, 10, prec=5)


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

    def test_png_with_metadata(self):
        px = [(0, 0, 0)]
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            write_png(path, px, 1, 1, text_meta={"Software": "test"})
            with open(path, "rb") as f:
                data = f.read()
            self.assertIn(b"Software", data)
        finally:
            os.unlink(path)

    def test_svg(self):
        px = [(255, 255, 255), (0, 0, 0), (128, 128, 128), (200, 200, 200)]
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            write_svg(path, px, 4, 1)
            with open(path) as f:
                txt = f.read()
            self.assertIn("<svg", txt)
            self.assertIn("</svg>", txt)
            self.assertIn("rect", txt)
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


class TestZoomAndExplore(unittest.TestCase):
    def test_zoom_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            files = render_zoom_sequence("mandelbrot", -0.5 + 0j, 3.0, 0.3, 3,
                                          img_size=(20, 15), max_iter=40,
                                          output_dir=d)
            self.assertEqual(len(files), 3)
            for fn in files:
                self.assertTrue(os.path.exists(os.path.join(d, fn)))

    def test_zoom_invalid(self):
        with self.assertRaises(ValueError):
            render_zoom_sequence("mandelbrot", 0, 3, 0.3, 0)
        with self.assertRaises(ValueError):
            render_zoom_sequence("mandelbrot", 0, 3, 0, 3)
        with self.assertRaises(ValueError):
            render_zoom_sequence("mandelbrot", 0, 0, 0.3, 3)
        with self.assertRaises(ValueError):
            render_zoom_sequence("mandelbrot", 0, 3, 3, 3)  # end >= start

    def test_explore_julia(self):
        with tempfile.TemporaryDirectory() as d:
            files = explore_julia(grid_size=2, img_size=(20, 20),
                                  output_dir=d, max_iter=30)
            self.assertEqual(len(files), 4)
            self.assertTrue(os.path.exists(os.path.join(d, "index.html")))


class TestBenchmark(unittest.TestCase):
    def test_benchmark(self):
        res = benchmark(kinds=["mandelbrot"], size=(20, 20), max_iter=30, trials=1)
        self.assertEqual(len(res), 1)
        self.assertGreater(res[0]["pixels_per_sec"], 0)


class TestCLI(unittest.TestCase):
    def test_info(self):
        from fractal import build_cli
        parser = build_cli()
        args = parser.parse_args(["info"])
        self.assertEqual(args.command, "info")

    def test_render_parse(self):
        from fractal import build_cli
        parser = build_cli()
        args = parser.parse_args(["render", "--kind", "julia",
                                   "--julia-c=-0.7,0.27",
                                   "--supersample", "2"])
        self.assertEqual(args.kind, "julia")

    def test_explore_parse(self):
        from fractal import build_cli
        parser = build_cli()
        args = parser.parse_args(["explore", "--grid", "3", "--radius", "1.0"])
        self.assertEqual(args.grid, 3)
        self.assertEqual(args.radius, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)