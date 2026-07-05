"""Tests for the new features added in the comprehensive improvement.

Covers: Buddhabrot, Lyapunov, IFS, filters, animation, presets, new palettes,
new traps (stripe, spiral), TGA output, periodicity detection, and the CLI
for new subcommands.
"""
from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fractal_explorer import (
    Viewport, render_fractal, write_png, write_tga, write_ppm,
    render_buddhabrot, AntiBuddhabrot,
    render_lyapunov,
    IFSFractal, BARNSLEY_FERN, SIERPINSKI_TRIANGLE, DRAGON_CURVE, render_ifs,
    box_blur, gaussian_blur, edge_detect, emboss, grayscale_filter,
    invert, brightness, contrast, apply_filter, FILTERS,
    render_julia_morph, render_color_cycle,
    PresetManager, PRESETS, save_preset, load_preset,
    get_palette, PALETTES,
    make_trap, StripeTrap, SpiralTrap,
)
from fractal_explorer.periodicity import iterate_with_periodicity


class TestNewPalettes(unittest.TestCase):
    """Tests for neon and forest palettes."""

    def test_neon_palette(self):
        pal = get_palette("neon", 32)
        self.assertEqual(len(pal), 32)
        for c in pal:
            self.assertEqual(len(c), 3)
            for ch in c:
                self.assertTrue(0 <= ch <= 255)

    def test_forest_palette(self):
        pal = get_palette("forest", 32)
        self.assertEqual(len(pal), 32)

    def test_new_palettes_in_registry(self):
        self.assertIn("neon", PALETTES)
        self.assertIn("forest", PALETTES)


class TestNewTraps(unittest.TestCase):
    """Tests for stripe and spiral traps."""

    def test_stripe_trap(self):
        t = StripeTrap(count=8)
        d = t.distance(1 + 0j)
        self.assertGreaterEqual(d, 0)

    def test_spiral_trap(self):
        t = SpiralTrap(tightness=0.3)
        d = t.distance(1 + 0j)
        self.assertGreaterEqual(d, 0)

    def test_make_new_traps(self):
        s = make_trap("stripe")
        self.assertIsInstance(s, StripeTrap)
        sp = make_trap("spiral")
        self.assertIsInstance(sp, SpiralTrap)

    def test_stripe_trap_distance_zero(self):
        t = StripeTrap()
        self.assertEqual(t.distance(0), 0.0)

    def test_spiral_trap_distance_zero(self):
        t = SpiralTrap()
        self.assertEqual(t.distance(0), 0.0)


class TestBuddhabrot(unittest.TestCase):
    """Tests for Buddhabrot rendering."""

    def test_buddhabot_basic(self):
        vp = Viewport(-0.5 + 0j, 3.0, 2.0)
        px, stats = render_buddhabrot(vp, 20, 20, samples=500, max_iter=50,
                                       seed=42)
        self.assertEqual(len(px), 400)
        self.assertEqual(stats["kind"], "buddhabrot")
        self.assertEqual(stats["samples"], 500)

    def test_buddhabrot_seed_reproducible(self):
        vp = Viewport(-0.5 + 0j, 3.0, 2.0)
        px1, _ = render_buddhabrot(vp, 20, 20, samples=500, seed=123)
        px2, _ = render_buddhabrot(vp, 20, 20, samples=500, seed=123)
        self.assertEqual(px1, px2)

    def test_anti_buddhabrot(self):
        vp = Viewport(-0.5 + 0j, 3.0, 2.0)
        px, stats = render_buddhabrot(vp, 20, 20, samples=500, max_iter=50,
                                       seed=42, anti=True)
        self.assertEqual(len(px), 400)
        self.assertTrue(stats["anti"])

    def test_buddhabrot_invalid_args(self):
        with self.assertRaises(ValueError):
            render_buddhabrot(Viewport(0, 1, 1), 0, 10)
        with self.assertRaises(ValueError):
            render_buddhabrot(Viewport(0, 1, 1), 10, 10, samples=0)


class TestLyapunov(unittest.TestCase):
    """Tests for Lyapunov fractal rendering."""

    def test_lyapunov_basic(self):
        px, stats = render_lyapunov(width=20, height=20, max_iter=100,
                                     sequence="AB")
        self.assertEqual(len(px), 400)
        self.assertEqual(stats["kind"], "lyapunov")
        self.assertEqual(stats["sequence"], "AB")

    def test_lyapunov_sequence_validation(self):
        with self.assertRaises(ValueError):
            render_lyapunov(sequence="", max_iter=10)
        with self.assertRaises(ValueError):
            render_lyapunov(sequence="ABC", max_iter=10)

    def test_lyapunov_invalid_dims(self):
        with self.assertRaises(ValueError):
            render_lyapunov(width=0, height=10)
        with self.assertRaises(ValueError):
            render_lyapunov(max_iter=0)


class TestIFS(unittest.TestCase):
    """Tests for IFS fractals."""

    def test_fern_basic(self):
        px, stats = render_ifs(BARNSLEY_FERN, width=30, height=30,
                                iterations=2000, seed=42)
        self.assertEqual(len(px), 900)
        self.assertIn("ifs", stats["kind"])

    def test_sierpinski_basic(self):
        px, stats = render_ifs(SIERPINSKI_TRIANGLE, width=30, height=30,
                                iterations=2000, seed=42)
        self.assertEqual(len(px), 900)

    def test_dragon_basic(self):
        px, stats = render_ifs(DRAGON_CURVE, width=30, height=30,
                                iterations=2000, seed=42)
        self.assertEqual(len(px), 900)

    def test_ifs_custom(self):
        ifs = IFSFractal([
            (0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 0.5),
            (0.5, 0.0, 0.0, 0.5, 0.5, 0.5, 0.5),
        ], name="custom")
        px, stats = ifs.render(width=20, height=20, iterations=1000, seed=1)
        self.assertEqual(len(px), 400)

    def test_ifs_zero_probability(self):
        with self.assertRaises(ValueError):
            IFSFractal([
                (0.5, 0, 0, 0.5, 0, 0, 0),
                (0.5, 0, 0, 0.5, 0.5, 0.5, 0),
            ])


class TestFilters(unittest.TestCase):
    """Tests for post-processing filters."""

    def setUp(self):
        # Create a simple test image
        self.w, self.h = 10, 10
        self.pixels = []
        for y in range(self.h):
            for x in range(self.w):
                self.pixels.append((x * 25 % 256, y * 25 % 256, 128))

    def test_invert(self):
        out = invert(self.pixels, self.w, self.h)
        self.assertEqual(len(out), len(self.pixels))
        r, g, b = out[0]
        self.assertEqual(r, 255 - self.pixels[0][0])

    def test_grayscale(self):
        out = grayscale_filter(self.pixels, self.w, self.h)
        for r, g, b in out:
            self.assertEqual(r, g)
            self.assertEqual(g, b)

    def test_brightness(self):
        out = brightness(self.pixels, self.w, self.h, delta=50)
        r, g, b = out[0]
        self.assertEqual(r, min(255, self.pixels[0][0] + 50))

    def test_contrast(self):
        out = contrast(self.pixels, self.w, self.h, factor=2.0)
        self.assertEqual(len(out), len(self.pixels))

    def test_box_blur(self):
        out = box_blur(self.pixels, self.w, self.h, radius=1)
        self.assertEqual(len(out), len(self.pixels))

    def test_gaussian_blur(self):
        out = gaussian_blur(self.pixels, self.w, self.h, radius=1)
        self.assertEqual(len(out), len(self.pixels))

    def test_edge_detect(self):
        out = edge_detect(self.pixels, self.w, self.h)
        self.assertEqual(len(out), len(self.pixels))

    def test_emboss(self):
        out = emboss(self.pixels, self.w, self.h)
        self.assertEqual(len(out), len(self.pixels))

    def test_apply_filter_named(self):
        out = apply_filter(self.pixels, self.w, self.h, "invert")
        self.assertEqual(len(out), len(self.pixels))

    def test_apply_filter_unknown(self):
        with self.assertRaises(ValueError):
            apply_filter(self.pixels, self.w, self.h, "nonexistent")

    def test_all_filters_in_registry(self):
        for name in FILTERS:
            out = apply_filter(self.pixels, self.w, self.h, name)
            self.assertEqual(len(out), len(self.pixels))


class TestTGAOutput(unittest.TestCase):
    """Tests for TGA output."""

    def test_write_tga(self):
        w, h = 5, 4
        pixels = [(i, i, i) for i in range(w * h)]
        with tempfile.NamedTemporaryFile(suffix=".tga", delete=False) as f:
            path = f.name
        try:
            write_tga(path, pixels, w, h)
            with open(path, "rb") as f:
                data = f.read()
            # TGA header is 18 bytes
            self.assertEqual(len(data), 18 + w * h * 3)
            # Check image type (byte 2) = 2 (uncompressed truecolor)
            self.assertEqual(data[2], 2)
            # Check width
            self.assertEqual(struct.unpack("<H", data[12:14])[0], w)
            self.assertEqual(struct.unpack("<H", data[14:16])[0], h)
            self.assertEqual(data[16], 24)  # bits per pixel
        finally:
            os.unlink(path)


class TestPeriodicity(unittest.TestCase):
    """Tests for Brent cycle detection."""

    def test_periodicity_escapes(self):
        # c = 2+0j escapes immediately
        it, z2 = iterate_with_periodicity(2 + 0j, 100, 1 << 16, power=2.0)
        self.assertLess(it, 100)

    def test_periodicity_interior(self):
        # c = 0+0j is interior (stays at 0)
        it, z2 = iterate_with_periodicity(0 + 0j, 100, 1 << 16, power=2.0)
        self.assertEqual(it, 100)

    def test_periodicity_matches_plain(self):
        from fractal_explorer.iterators import _mandelbrot_iter
        for c in [-1 + 0j, 0.3 + 0.5j, -0.5 + 0j]:
            it1, _ = _mandelbrot_iter(c, 200, 1 << 16, 2.0)
            it2, _ = iterate_with_periodicity(c, 200, 1 << 16, 2.0)
            # Both should agree on escape vs non-escape
            self.assertEqual(it1 >= 200, it2 >= 200)


class TestPresets(unittest.TestCase):
    """Tests for preset management."""

    def test_builtin_presets(self):
        self.assertGreater(len(PRESETS), 5)
        self.assertIn("mandelbrot-classic", PRESETS)
        self.assertIn("seahorse-valley", PRESETS)

    def test_preset_save_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = save_preset("test_preset", {"kind": "julia", "width": 100},
                               directory=d)
            self.assertTrue(os.path.exists(path))
            params = load_preset("test_preset", directory=d)
            self.assertEqual(params["kind"], "julia")
            self.assertEqual(params["width"], 100)

    def test_preset_manager_list(self):
        with tempfile.TemporaryDirectory() as d:
            pm = PresetManager(d)
            pm.save("a", {"x": 1})
            pm.save("b", {"y": 2})
            names = pm.list()
            self.assertIn("a", names)
            self.assertIn("b", names)

    def test_preset_manager_delete(self):
        with tempfile.TemporaryDirectory() as d:
            pm = PresetManager(d)
            pm.save("test", {"x": 1})
            self.assertTrue(pm.delete("test"))
            self.assertFalse(pm.delete("test"))

    def test_preset_load_missing(self):
        with tempfile.TemporaryDirectory() as d:
            pm = PresetManager(d)
            with self.assertRaises(FileNotFoundError):
                pm.load("nonexistent")


class TestAnimation(unittest.TestCase):
    """Tests for animation renderers."""

    def test_julia_morph(self):
        with tempfile.TemporaryDirectory() as d:
            files = render_julia_morph(-0.4 + 0.6j, 0.285 + 0.01j, frames=3,
                                        width=20, height=15, max_iter=30,
                                        palette_name="rainbow",
                                        output_dir=d)
            self.assertEqual(len(files), 3)
            for f in files:
                self.assertTrue(os.path.exists(os.path.join(d, f)))

    def test_color_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            vp = Viewport(-0.5 + 0j, 3, 2)
            files = render_color_cycle("mandelbrot", vp, frames=3,
                                        width=20, height=15, max_iter=30,
                                        palette_name="rainbow",
                                        output_dir=d)
            self.assertEqual(len(files), 3)
            for f in files:
                self.assertTrue(os.path.exists(os.path.join(d, f)))


class TestViewportImprovements(unittest.TestCase):
    """Tests for new Viewport methods."""

    def test_copy(self):
        vp = Viewport(-0.5 + 0j, 3, 2)
        vp2 = vp.copy()
        self.assertEqual(vp.center, vp2.center)
        self.assertEqual(vp.width, vp2.width)
        self.assertEqual(vp.height, vp2.height)
        vp2.width = 99
        self.assertEqual(vp.width, 3)  # original unchanged

    def test_fit_aspect(self):
        vp = Viewport(-0.5 + 0j, 3, 3)  # square
        vp2 = vp.fit_aspect(2.0)  # width/height = 2
        self.assertAlmostEqual(vp2.width, 3)
        self.assertAlmostEqual(vp2.height, 1.5)

    def test_fit_aspect_no_change(self):
        vp = Viewport(-0.5 + 0j, 3, 1.5)
        vp2 = vp.fit_aspect(2.0)
        self.assertAlmostEqual(vp2.width, vp.width)
        self.assertAlmostEqual(vp2.height, vp.height)

    def test_pixel_to_complex(self):
        vp = Viewport(0 + 0j, 2, 2)
        c = vp.pixel_to_complex(0, 0, 10, 10)
        # center of first pixel (top-left = low x, low y in this convention)
        self.assertAlmostEqual(c.real, -0.9)
        self.assertAlmostEqual(c.imag, -0.9)
        # last pixel (bottom-right)
        c2 = vp.pixel_to_complex(9, 9, 10, 10)
        self.assertAlmostEqual(c2.real, 0.9)
        self.assertAlmostEqual(c2.imag, 0.9)


class TestCLINewCommands(unittest.TestCase):
    """Tests for new CLI subcommands."""

    def test_cli_buddhabrot(self):
        from fractal_explorer.cli import build_cli
        parser = build_cli()
        args = parser.parse_args(["buddhabrot", "--width", "10",
                                   "--height", "10", "--samples", "50",
                                   "--max-iter", "20", "--seed", "42",
                                   "-o", "/tmp/test_buddha.png"])
        self.assertEqual(args.command, "buddhabrot")
        self.assertEqual(args.width, 10)

    def test_cli_lyapunov(self):
        from fractal_explorer.cli import build_cli
        parser = build_cli()
        args = parser.parse_args(["lyapunov", "--width", "10", "--height", "10",
                                   "--max-iter", "50", "--sequence", "AB",
                                   "-o", "/tmp/test_lyap.png"])
        self.assertEqual(args.command, "lyapunov")
        self.assertEqual(args.sequence, "AB")

    def test_cli_ifs(self):
        from fractal_explorer.cli import build_cli
        parser = build_cli()
        args = parser.parse_args(["ifs", "--type", "fern", "--width", "10",
                                   "--height", "10", "--iterations", "100",
                                   "-o", "/tmp/test_ifs.png"])
        self.assertEqual(args.type, "fern")

    def test_cli_animate(self):
        from fractal_explorer.cli import build_cli
        parser = build_cli()
        args = parser.parse_args(["animate", "--mode", "julia-morph",
                                   "--frames", "2", "--width", "10",
                                   "--height", "8"])
        self.assertEqual(args.mode, "julia-morph")

    def test_cli_preset_list(self):
        from fractal_explorer.cli import build_cli
        parser = build_cli()
        args = parser.parse_args(["preset", "list"])
        self.assertEqual(args.action, "list")

    def test_cli_filter_flag(self):
        from fractal_explorer.cli import build_cli
        parser = build_cli()
        args = parser.parse_args(["render", "--filter", "invert",
                                   "--width", "5", "--height", "5"])
        self.assertEqual(args.filter, "invert")

    def test_cli_tga_format(self):
        from fractal_explorer.cli import build_cli
        parser = build_cli()
        args = parser.parse_args(["render", "--format", "tga", "-o", "/tmp/t.tga"])
        self.assertEqual(args.format, "tga")

    def test_cli_info_includes_filters(self):
        from fractal_explorer.cli import build_cli, cmd_info
        import io
        from contextlib import redirect_stdout
        parser = build_cli()
        args = parser.parse_args(["info"])
        f = io.StringIO()
        with redirect_stdout(f):
            cmd_info(args)
        output = f.getvalue()
        self.assertIn("Filters:", output)
        self.assertIn("Presets:", output)
        self.assertIn("tga", output)


class TestPackageStructure(unittest.TestCase):
    """Tests for the modular package structure."""

    def test_version(self):
        import fractal_explorer
        self.assertTrue(hasattr(fractal_explorer, "__version__"))
        self.assertTrue(hasattr(fractal_explorer, "__author__"))

    def test_all_imports(self):
        import fractal_explorer
        for name in fractal_explorer.__all__:
            self.assertTrue(hasattr(fractal_explorer, name),
                            f"Missing {name} in fractal_explorer")

    def test_submodules_exist(self):
        import fractal_explorer
        from fractal_explorer import palettes, iterators, traps, viewport
        from fractal_explorer import coloring, render, hp, io_writers
        from fractal_explorer import zoom, julia, benchmark, config
        from fractal_explorer import buddhabrot, lyapunov, ifs, filters
        from fractal_explorer import animation, presets, cli

    def test_backward_compat_shim(self):
        # The old fractal.py shim should still work
        import fractal
        self.assertTrue(hasattr(fractal, "Viewport"))
        self.assertTrue(hasattr(fractal, "render_fractal"))
        self.assertTrue(hasattr(fractal, "write_png"))


if __name__ == "__main__":
    unittest.main(verbosity=2)