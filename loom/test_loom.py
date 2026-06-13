#!/usr/bin/env python3
"""Tests for LOOM — Terminal Generative Art Weaver."""

import os
import sys
import math
import random
import tempfile
import unittest

# Import the module under test
sys.path.insert(0, os.path.dirname(__file__))
from loom import (
    Loom, WeaveLayer, random_layer, rgb_to_ansi, blend_color,
    palette_color, clamp, PALETTES, WEAVE_PATTERNS, BLOCKS, __version__
)


class TestRGBtoANSI(unittest.TestCase):
    """Test RGB to ANSI color code conversion."""

    def test_basic_conversion(self):
        result = rgb_to_ansi(255, 128, 0)
        self.assertIn("38;2;255;128;0", result)

    def test_zero_values(self):
        result = rgb_to_ansi(0, 0, 0)
        self.assertIn("38;2;0;0;0", result)

    def test_max_values(self):
        result = rgb_to_ansi(255, 255, 255)
        self.assertIn("38;2;255;255;255", result)

    def test_clamping_negative(self):
        """Negative values should be clamped to 0."""
        result = rgb_to_ansi(-10, 50, 50)
        self.assertIn("38;2;0;50;50", result)

    def test_clamping_overflow(self):
        """Values over 255 should be clamped."""
        result = rgb_to_ansi(300, 128, 50)
        self.assertIn("38;2;255;128;50", result)


class TestBlendColor(unittest.TestCase):
    """Test linear color interpolation."""

    def test_start_color(self):
        c1 = (255, 0, 0)
        c2 = (0, 255, 0)
        result = blend_color(c1, c2, 0.0)
        self.assertAlmostEqual(result[0], 255.0)
        self.assertAlmostEqual(result[1], 0.0)

    def test_end_color(self):
        c1 = (255, 0, 0)
        c2 = (0, 255, 0)
        result = blend_color(c1, c2, 1.0)
        self.assertAlmostEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 255.0)

    def test_midpoint(self):
        c1 = (0, 0, 0)
        c2 = (100, 200, 50)
        result = blend_color(c1, c2, 0.5)
        self.assertAlmostEqual(result[0], 50.0)
        self.assertAlmostEqual(result[1], 100.0)
        self.assertAlmostEqual(result[2], 25.0)


class TestPaletteColor(unittest.TestCase):
    """Test palette color lookup with interpolation."""

    def test_first_color(self):
        palette = [(100, 0, 0), (200, 0, 0)]
        result = palette_color(palette, 0.0)
        self.assertAlmostEqual(result[0], 100.0)

    def test_wraps_around(self):
        """Colors should wrap cyclically."""
        palette = [(100, 0, 0), (200, 0, 0)]
        result = palette_color(palette, 1.0)
        # Should be same as t=0 since it wraps
        self.assertAlmostEqual(result[0], 100.0, places=0)

    def test_all_palettes_valid(self):
        """All defined palettes should be usable without errors."""
        for name, palette in PALETTES.items():
            for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
                color = palette_color(palette, t)
                self.assertEqual(len(color), 3, f"Palette {name} at t={t} returned bad color")


class TestClamp(unittest.TestCase):
    """Test the clamp utility function."""

    def test_within_range(self):
        self.assertEqual(clamp(0.5), 0.5)

    def test_below_range(self):
        self.assertEqual(clamp(-0.5), 0.0)

    def test_above_range(self):
        self.assertEqual(clamp(1.5), 1.0)

    def test_custom_range(self):
        self.assertEqual(clamp(5.0, 0.0, 10.0), 5.0)
        self.assertEqual(clamp(-1.0, 0.0, 10.0), 0.0)


class TestRandomLayer(unittest.TestCase):
    """Test random layer generation."""

    def test_returns_namedtuple(self):
        layer = random_layer()
        self.assertIsInstance(layer, WeaveLayer)
        self.assertTrue(hasattr(layer, 'freq_x'))
        self.assertTrue(hasattr(layer, 'freq_y'))
        self.assertTrue(hasattr(layer, 'phase_x'))
        self.assertTrue(hasattr(layer, 'phase_y'))
        self.assertTrue(hasattr(layer, 'speed'))
        self.assertTrue(hasattr(layer, 'amplitude'))

    def test_values_in_expected_range(self):
        """Random layers should have values within expected bounds."""
        for _ in range(100):
            layer = random_layer()
            self.assertGreaterEqual(layer.freq_x, 0.02)
            self.assertLessEqual(layer.freq_x, 0.15)
            self.assertGreaterEqual(layer.freq_y, 0.02)
            self.assertLessEqual(layer.freq_y, 0.15)
            self.assertGreaterEqual(layer.amplitude, 0.3)
            self.assertLessEqual(layer.amplitude, 1.0)
            self.assertGreaterEqual(layer.speed, 0.3)
            self.assertLessEqual(layer.speed, 1.5)


class TestLoomInit(unittest.TestCase):
    """Test Loom initialization."""

    def test_default_init(self):
        loom = Loom(width=40, height=10)
        self.assertEqual(loom.width, 40)
        self.assertEqual(loom.height, 10)
        self.assertEqual(loom.palette_name, "sunset")
        self.assertEqual(loom.pattern_name, "twill")
        self.assertEqual(loom.fps, 15)
        self.assertEqual(len(loom.layers), 3)

    def test_custom_palette(self):
        for palette_name in PALETTES:
            loom = Loom(width=40, height=10, palette=palette_name)
            self.assertEqual(loom.palette_name, palette_name)

    def test_custom_pattern(self):
        for pattern_name in WEAVE_PATTERNS:
            loom = Loom(width=40, height=10, pattern=pattern_name)
            self.assertEqual(loom.pattern_name, pattern_name)

    def test_seed_reproducibility(self):
        """Same seed should produce identical looms."""
        loom1 = Loom(width=40, height=10, seed=42)
        loom2 = Loom(width=40, height=10, seed=42)
        for l1, l2 in zip(loom1.layers, loom2.layers):
            self.assertEqual(l1, l2)
        self.assertEqual(loom1.warp_threads, loom2.warp_threads)
        self.assertEqual(loom1.weft_threads, loom2.weft_threads)

    def test_seed_diversity(self):
        """Different seeds should produce different looms."""
        loom1 = Loom(width=40, height=10, seed=1)
        loom2 = Loom(width=40, height=10, seed=999)
        # At least some thread values should differ
        self.assertNotEqual(loom1.warp_threads, loom2.warp_threads)

    def test_layers_count(self):
        for n in [1, 2, 5, 10]:
            loom = Loom(width=40, height=10, layers=n)
            self.assertEqual(len(loom.layers), n)

    def test_small_width_clamped(self):
        loom = Loom(width=5, height=10)
        self.assertEqual(loom.width, 10)

    def test_small_height_clamped(self):
        loom = Loom(width=40, height=2)
        self.assertEqual(loom.height, 5)

    def test_custom_speed(self):
        loom = Loom(width=40, height=10, speed=5.0)
        self.assertEqual(loom.speed, 5.0)

    def test_info_flag(self):
        loom = Loom(width=40, height=10, info=True)
        self.assertTrue(loom.info)


class TestComputeWeaveValue(unittest.TestCase):
    """Test the core generative function."""

    def setUp(self):
        self.loom = Loom(width=40, height=10, seed=42)

    def test_returns_float(self):
        value = self.loom.compute_weave_value(0, 0, 0.0)
        self.assertIsInstance(value, float)

    def test_reasonable_range(self):
        """Values should be in a reasonable range."""
        for y in range(self.loom.height):
            for x in range(self.loom.width):
                value = self.loom.compute_weave_value(x, y, 1.0)
                self.assertGreater(value, -3.0, f"Value too negative at ({x},{y})")
                self.assertLess(value, 3.0, f"Value too large at ({x},{y})")

    def test_deterministic_with_seed(self):
        loom1 = Loom(width=40, height=10, seed=42)
        loom2 = Loom(width=40, height=10, seed=42)
        for x in range(10):
            for y in range(5):
                v1 = loom1.compute_weave_value(x, y, 1.0)
                v2 = loom2.compute_weave_value(x, y, 1.0)
                self.assertAlmostEqual(v1, v2, places=10)


class TestValueToChar(unittest.TestCase):
    """Test character mapping from weave values."""

    def setUp(self):
        self.loom = Loom(width=40, height=10, seed=42)

    def test_returns_string(self):
        char = self.loom.value_to_char(0.0)
        self.assertIsInstance(char, str)

    def test_extreme_values(self):
        """Very high and very low values should produce valid characters."""
        low_char = self.loom.value_to_char(-10.0)
        high_char = self.loom.value_to_char(10.0)
        self.assertEqual(len(low_char), 1)
        self.assertEqual(len(high_char), 1)

    def test_all_chars_in_blocks(self):
        """All returned characters should be in the BLOCKS dict."""
        all_block_chars = set(BLOCKS.values())
        for v in [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]:
            char = self.loom.value_to_char(v)
            self.assertIn(char, all_block_chars, f"Value {v} produced unexpected char: {char}")


class TestPatternChars(unittest.TestCase):
    """Test all pattern-specific character methods."""

    def test_all_patterns_produce_chars(self):
        """Each pattern should produce valid characters for all positions."""
        for pattern_name in WEAVE_PATTERNS:
            loom = Loom(width=40, height=10, seed=42, pattern=pattern_name)
            all_block_chars = set(BLOCKS.values())
            # Test various positions
            for x in range(0, 40, 5):
                for y in range(0, 10, 2):
                    value = loom.compute_weave_value(x, y, 1.0)
                    color, char = loom.value_to_color_and_char(value, x, y, 1.0)
                    self.assertIn(char, all_block_chars,
                                  f"Pattern {pattern_name} at ({x},{y}) produced invalid char: {char}")


class TestRenderFrame(unittest.TestCase):
    """Test frame rendering."""

    def test_render_ascii_frame(self):
        loom = Loom(width=20, height=5, seed=42)
        lines = loom.render_ascii_frame(1.0)
        self.assertEqual(len(lines), 5)
        self.assertEqual(len(lines[0]), 20)

    def test_render_color_frame(self):
        loom = Loom(width=20, height=5, seed=42)
        lines = loom.render_frame(1.0)
        self.assertEqual(len(lines), 5)
        # Each line should contain ANSI codes (start with escape)
        self.assertIn("\033[", lines[0])

    def test_snapshot_ascii(self):
        loom = Loom(width=20, height=5, seed=42)
        result = loom.snapshot(t=1.0, ascii_mode=True)
        self.assertIsInstance(result, str)
        lines = result.split("\n")
        self.assertEqual(len(lines), 5)

    def test_snapshot_color(self):
        loom = Loom(width=20, height=5, seed=42)
        result = loom.snapshot(t=1.0, ascii_mode=False)
        self.assertIn("\033[", result)


class TestSaveFrames(unittest.TestCase):
    """Test frame saving to file."""

    def test_save_ascii_frames(self):
        loom = Loom(width=20, height=5, seed=42)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            filename = f.name
        try:
            result = loom.save_frames(filename, frames=3, ascii_mode=True)
            self.assertEqual(result, filename)
            with open(filename, "r") as f:
                content = f.read()
            self.assertIn("Frame 0", content)
            self.assertIn("Frame 2", content)
            self.assertNotIn("\033[", content)
        finally:
            os.unlink(filename)

    def test_save_colored_frames(self):
        loom = Loom(width=20, height=5, seed=42)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            filename = f.name
        try:
            loom.save_frames(filename, frames=2, ascii_mode=False, colored=True)
            with open(filename, "r") as f:
                content = f.read()
            self.assertIn("\033[", content)
        finally:
            os.unlink(filename)


class TestHexagonalPattern(unittest.TestCase):
    """Test the hexagonal weave pattern specifically."""

    def test_hexagonal_produces_valid_chars(self):
        loom = Loom(width=20, height=10, seed=42, pattern="hexagonal")
        all_block_chars = set(BLOCKS.values())
        for x in range(20):
            for y in range(10):
                v = loom.compute_weave_value(x, y, 1.0)
                vn = clamp((v + 1.5) / 3.0)
                char = loom._hexagonal_char(vn, x, y, 1.0)
                self.assertIn(char, all_block_chars)

    def test_hexagonal_in_patterns_list(self):
        self.assertIn("hexagonal", WEAVE_PATTERNS)


class TestInfoBar(unittest.TestCase):
    """Test the info bar overlay."""

    def test_info_bar_produces_string(self):
        loom = Loom(width=80, height=20, seed=42, info=True)
        bar = loom._info_bar(t=5.0, fps_actual=14.5)
        self.assertIsInstance(bar, str)
        self.assertIn("\033[", bar)  # Contains ANSI codes

    def test_info_bar_contains_palette(self):
        loom = Loom(width=80, height=20, seed=42, palette="neon", info=True)
        bar = loom._info_bar(t=0.0, fps_actual=15.0)
        self.assertIn("neon", bar)

    def test_info_bar_truncation(self):
        loom = Loom(width=30, height=10, seed=42, info=True)
        bar = loom._info_bar(t=0.0, fps_actual=15.0)
        # Should not exceed width (ANSI codes add length but display shorter)
        # Just check it doesn't crash
        self.assertIsInstance(bar, str)


class TestListMethods(unittest.TestCase):
    """Test palette and pattern listing methods."""

    def test_list_palettes(self):
        loom = Loom(width=40, height=10)
        output = loom.list_palettes()
        self.assertIn("sunset", output)
        self.assertIn("neon", output)
        self.assertIn("thermal", output)

    def test_list_patterns(self):
        loom = Loom(width=40, height=10)
        output = loom.list_patterns()
        self.assertIn("plain", output)
        self.assertIn("hexagonal", output)
        self.assertIn("diamond", output)


class TestNewPalettes(unittest.TestCase):
    """Test the newly added palettes."""

    def test_thermal_palette(self):
        loom = Loom(width=20, height=5, palette="thermal")
        self.assertEqual(loom.palette_name, "thermal")
        lines = loom.render_frame(1.0)
        self.assertEqual(len(lines), 5)

    def test_nightshade_palette(self):
        loom = Loom(width=20, height=5, palette="nightshade")
        self.assertEqual(loom.palette_name, "nightshade")
        lines = loom.render_frame(1.0)
        self.assertEqual(len(lines), 5)

    def test_render_with_all_palettes(self):
        """All palettes should render without errors."""
        for palette_name in PALETTES:
            loom = Loom(width=20, height=5, palette=palette_name, seed=42)
            lines = loom.render_frame(1.0)
            self.assertEqual(len(lines), 5, f"Palette {palette_name} failed")


class TestVersion(unittest.TestCase):
    """Test version string."""

    def test_version_exists(self):
        self.assertIsNotNone(__version__)
        self.assertIsInstance(__version__, str)
        # Should be semver-like
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)


class TestBugFixes(unittest.TestCase):
    """Tests for bugs found and fixed in v1.1.1."""

    def test_compute_weave_value_out_of_bounds(self):
        """compute_weave_value should not crash when x/y exceed width/height."""
        loom = Loom(width=10, height=5, seed=42)
        # These used to cause IndexError
        val = loom.compute_weave_value(15, 3, 1.0)
        self.assertIsInstance(val, float)
        val = loom.compute_weave_value(100, 100, 1.0)
        self.assertIsInstance(val, float)
        val = loom.compute_weave_value(999, 999, 0.0)
        self.assertIsInstance(val, float)

    def test_compute_weave_value_at_boundary(self):
        """compute_weave_value should work at exact boundary indices."""
        loom = Loom(width=10, height=5, seed=42)
        val = loom.compute_weave_value(9, 4, 1.0)
        self.assertIsInstance(val, float)
        val = loom.compute_weave_value(0, 0, 1.0)
        self.assertIsInstance(val, float)

    def test_invalid_palette_name_corrected(self):
        """Invalid palette name should be corrected to 'sunset' with a warning."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            loom = Loom(width=20, height=5, palette="nonexistent")
            self.assertEqual(loom.palette_name, "sunset")
            self.assertEqual(loom.palette, PALETTES["sunset"])
        finally:
            sys.stderr = old_stderr

    def test_invalid_pattern_name_corrected(self):
        """Invalid pattern name should be corrected to 'twill' with a warning."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            loom = Loom(width=20, height=5, pattern="nonexistent")
            self.assertEqual(loom.pattern_name, "twill")
        finally:
            sys.stderr = old_stderr

    def test_fps_zero_corrected(self):
        """FPS=0 should be corrected to 15 with a warning."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            loom = Loom(width=20, height=5, fps=0)
            self.assertEqual(loom.fps, 15)
            self.assertAlmostEqual(loom.frame_time, 1.0 / 15)
        finally:
            sys.stderr = old_stderr

    def test_fps_negative_corrected(self):
        """Negative FPS should be corrected to 15 with a warning."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            loom = Loom(width=20, height=5, fps=-5)
            self.assertEqual(loom.fps, 15)
        finally:
            sys.stderr = old_stderr

    def test_speed_zero_corrected(self):
        """Speed=0 should be corrected to 1.0 with a warning."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            loom = Loom(width=20, height=5, speed=0)
            self.assertEqual(loom.speed, 1.0)
        finally:
            sys.stderr = old_stderr

    def test_speed_negative_corrected(self):
        """Negative speed should be corrected to 1.0 with a warning."""
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            loom = Loom(width=20, height=5, speed=-1)
            self.assertEqual(loom.speed, 1.0)
        finally:
            sys.stderr = old_stderr

    def test_valid_palette_name_unchanged(self):
        """Valid palette names should not be changed."""
        loom = Loom(width=20, height=5, palette="neon")
        self.assertEqual(loom.palette_name, "neon")

    def test_valid_pattern_name_unchanged(self):
        """Valid pattern names should not be changed."""
        loom = Loom(width=20, height=5, pattern="diamond")
        self.assertEqual(loom.pattern_name, "diamond")

    def test_render_with_out_of_bounds_coords(self):
        """Rendering should work even if internal coords go beyond thread arrays."""
        loom = Loom(width=40, height=10, seed=42)
        # This should not raise any exceptions
        lines = loom.render_frame(1.0)
        self.assertEqual(len(lines), 10)
        lines = loom.render_ascii_frame(1.0)
        self.assertEqual(len(lines), 10)


if __name__ == "__main__":
    unittest.main()