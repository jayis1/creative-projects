#!/usr/bin/env python3
"""Tests for the Fractal Explorer."""

import math
import os
import sys
import tempfile

# Ensure we can import the module
sys.path.insert(0, os.path.dirname(__file__))
from fractal_explorer import (
    compute_fractal,
    smooth_color,
    render_to_plain_text,
    render_to_text,
    Viewport,
    PALETTES,
    BOOKMARKS,
    FRACTAL_TYPES,
    __version__,
)


def test_mandelbrot_inside():
    """Point inside the Mandelbrot set should return max_iter."""
    # (0, 0) is always in the Mandelbrot set
    it, z = compute_fractal(0.0, 0.0, 100, "mandelbrot")
    assert it == 100, f"Expected max_iter for point inside set, got {it}"


def test_mandelbrot_escapes():
    """Point far from the set should escape quickly."""
    it, z = compute_fractal(10.0, 10.0, 100, "mandelbrot")
    assert it < 5, f"Expected quick escape for (10, 10), got {it}"


def test_mandelbrot_boundary():
    """Point near the boundary should escape after several iterations."""
    it, z = compute_fractal(0.3, 0.0, 100, "mandelbrot")
    assert 0 < it < 100, f"Expected boundary escape, got {it}"


def test_mandelbrot_returns_z():
    """compute_fractal should return a complex z value on escape."""
    it, z = compute_fractal(2.0, 0.0, 100, "mandelbrot")
    assert it < 100, "Should escape"
    assert abs(z) > 2.0, f"Escaped z should have |z|>2, got {abs(z)}"


def test_julia_inside():
    """Julia set with c=0 should have all points inside (z stays fixed)."""
    it, z = compute_fractal(0.5, 0.0, 100, "julia", julia_c=0 + 0j)
    assert it == 100, f"Expected all points in for c=0 Julia, got {it}"


def test_burning_ship_escapes():
    """Burning Ship fractal should escape for far points."""
    it, z = compute_fractal(10.0, 10.0, 100, "burningship")
    assert it < 5, f"Expected quick escape for Burning Ship, got {it}"


def test_tricorn_escapes():
    """Tricorn should escape for far points."""
    it, z = compute_fractal(10.0, 0.0, 100, "tricorn")
    assert it < 5, f"Expected quick escape for Tricorn, got {it}"


def test_tricorn_inside():
    """Tricorn has interior points near (0, 0)."""
    it, z = compute_fractal(0.0, 0.0, 100, "tricorn")
    assert it == 100, f"Expected interior for tricorn origin, got {it}"


def test_smooth_color_inside():
    """Smooth color for max_iter points should return max_iter."""
    result = smooth_color(100, 100, complex(0, 0))
    assert result == 100.0


def test_smooth_color_boundary():
    """Smooth color should produce a float between iter and iter+1."""
    it, z = compute_fractal(0.3, 0.0, 100, "mandelbrot")
    result = smooth_color(it, 100, z)
    # Should be near the iteration count but smoothly interpolated
    assert it <= result <= it + 2, \
        f"Expected smooth value near {it}, got {result}"


def test_smooth_color_less_than_max():
    """Smooth color should give value less than max for escaping points."""
    it, z = compute_fractal(0.3, 0.0, 100, "mandelbrot")
    result = smooth_color(it, 100, z)
    assert result < 100.0, f"Expected value < max_iter for escape, got {result}"


def test_viewport_defaults():
    """Viewport should have sensible defaults."""
    vp = Viewport()
    assert vp.center_x == -0.5
    assert vp.center_y == 0.0
    assert vp.zoom == 1.5
    assert vp.fractal_type == "mandelbrot"
    assert vp.smooth is True


def test_viewport_julia_c():
    """Julia c property should compose correctly."""
    vp = Viewport()
    vp.julia_cx = -0.7
    vp.julia_cy = 0.27015
    c = vp.julia_c
    assert abs(c.real - (-0.7)) < 1e-6
    assert abs(c.imag - 0.27015) < 1e-6


def test_render_plain_text():
    """Plain text render should produce correct dimensions."""
    vp = Viewport()
    text = render_to_plain_text(vp, width=40, height=20)
    lines = text.split("\n")
    assert len(lines) == 20, f"Expected 20 lines, got {len(lines)}"
    for i, line in enumerate(lines):
        assert len(line) == 40, f"Line {i}: expected 40 chars, got {len(line)}"


def test_render_ansi_text():
    """ANSI text render should produce non-empty output with escape codes."""
    vp = Viewport()
    text = render_to_text(vp, width=40, height=20)
    assert "\033[" in text, "Expected ANSI escape codes"
    assert "\033[0m" in text, "Expected reset code"


def test_export_to_file():
    """Export should write a valid file."""
    vp = Viewport()
    text = render_to_plain_text(vp, width=30, height=15)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                     delete=False) as f:
        f.write(text)
        tmppath = f.name
    try:
        with open(tmppath) as f:
            content = f.read()
        lines = content.split("\n")
        assert len(lines) == 15
    finally:
        os.unlink(tmppath)


def test_palettes_exist():
    """All expected palettes should be registered."""
    expected = ["fire", "ocean", "matrix", "electric", "earth",
                "grayscale", "neon", "sunset"]
    for name in expected:
        assert name in PALETTES, f"Missing palette: {name}"


def test_fractal_types():
    """All fractal types should be available."""
    expected = ["mandelbrot", "julia", "burningship", "tricorn"]
    assert FRACTAL_TYPES == expected


def test_bookmarks_exist():
    """Bookmarks should have at least one entry with valid structure."""
    assert len(BOOKMARKS) >= 1
    for name, bm in BOOKMARKS.items():
        assert "center_x" in bm
        assert "center_y" in bm
        assert "zoom" in bm


def test_version():
    """Version should be a valid semver string."""
    parts = __version__.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_burning_ship_interior():
    """Burning Ship should have interior points."""
    it, z = compute_fractal(-1.75, -0.02, 200, "burningship")
    assert it == 200, f"Expected interior for Burning Ship, got {it}"


def test_all_fractals_produce_output():
    """Each fractal type should produce non-empty plain text output."""
    for ftype in FRACTAL_TYPES:
        vp = Viewport()
        vp.fractal_type = ftype
        if ftype == "burningship":
            vp.center_x = -0.4
            vp.center_y = -0.6
        if ftype == "julia":
            vp.julia = True
        text = render_to_plain_text(vp, width=20, height=10)
        assert len(text) > 0, f"Empty output for {ftype}"
        # Should have some non-space characters (fractal detail)
        stripped = text.replace(" ", "").replace("\n", "")
        assert len(stripped) > 0, f"Only spaces for {ftype}"


def test_cli_help():
    """CLI --help should work without error."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "fractal_explorer.py", "--help"],
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "fractal" in result.stdout.lower()


def test_cli_version():
    """CLI --version should work without error."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "fractal_explorer.py", "--version"],
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert __version__ in result.stdout.strip()


def test_cli_export():
    """CLI --export should create a file."""
    import subprocess
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        tmppath = f.name
    try:
        result = subprocess.run(
            [sys.executable, "fractal_explorer.py", "--export", tmppath,
             "--plain", "--width", "20", "--height", "10"],
            capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"Export failed: {result.stderr}"
        assert os.path.exists(tmppath)
        content = open(tmppath).read()
        assert len(content) > 0
    finally:
        if os.path.exists(tmppath):
            os.unlink(tmppath)


def test_cli_list_presets():
    """CLI --list-presets should show Julia presets."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "fractal_explorer.py", "--list-presets"],
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "Dendrite" in result.stdout


def test_cli_list_palettes():
    """CLI --list-palettes should show palette names."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "fractal_explorer.py", "--list-palettes"],
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "fire" in result.stdout
    assert "neon" in result.stdout


if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  ✓ {name}")
                passed += 1
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ✗ {name}: {type(e).__name__}: {e}")
                failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)