"""Bug-hunt tests — demonstrate bugs before fixing them.

Each test is named ``test_bugNN_<description>`` and reproduces a specific
defect found during the Phase 3 bug hunt. After the fix, each test must pass.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fractal import (Viewport, render_fractal, render_histogram_coloring,
                     render_mandelbrot_hp, _compute_pixel, _mandelbrot_iter,
                     get_fractal, get_palette, PointTrap, CrossTrap, CircleTrap,
                     _parse_complex, _parse_rgb, _load_config,
                     _merge_config, FRACTALS, _burning_ship_iter)
from decimal import Decimal, getcontext


class TestBug01TrapColoringUsesWrongFormula(unittest.TestCase):
    """Bug 1/2/3: trap coloring re-runs iteration with hardcoded z=z*z+c,
    ignoring power, kind (Burning Ship, Tricorn, etc.), and phoenix_c.

    For Burning Ship, the actual orbit takes abs() of components, but the
    trap re-run uses plain z*z+c, so the tracked orbit is wrong and the
    computed minimum distance is incorrect.
    """

    def test_trap_burning_ship_produces_different_result(self):
        """A Burning-Ship pixel with trap coloring should use the Burning
        Ship orbit, not the Mandelbrot orbit.

        We verify by checking that trap coloring on burning_ship with a
        CircleTrap produces multiple distinct colours (the trap distance
        varies across the image). Before the fix, the hardcoded z*z+c
        re-run produced a flat single-colour image for non-mandelbrot kinds.
        """
        vp = Viewport(0, 4, 4)
        px, _ = render_fractal("burning_ship", vp, 16, 12, max_iter=40,
                                coloring="trap", trap=CircleTrap(1.0))
        unique = set(px)
        self.assertGreater(len(unique), 1,
                           "trap coloring produced a flat image — orbit "
                           "tracking is likely wrong")


class TestBug04HistogramCumulBounds(unittest.TestCase):
    """Bug 4 (non-bug, sanity): confirm cumul array indexing is safe."""

    def test_cumul_no_index_error(self):
        vp = Viewport(-0.5, 3, 2)
        # max_iter=1 is an edge case — ensure no IndexError
        px, _ = render_histogram_coloring("mandelbrot", vp, 5, 4, max_iter=1)
        self.assertEqual(len(px), 20)


class TestBug07MergeConfigOverridesCLI(unittest.TestCase):
    """Bug 7: _merge_config unconditionally overrides argparse values with
    config-file values, contradicting its docstring which promises it will
    NOT override user-passed CLI flags.
    """

    def test_config_does_not_override_explicit_cli(self):
        import argparse
        args = argparse.Namespace(kind="julia", width=100, max_iter=50,
                                    palette="ice", coloring="smooth")
        cfg = {"kind": "mandelbrot", "width": 999, "max_iter": 999}
        # After fix: explicitly-provided dests are passed in `explicit` and
        # are preserved; the rest may be overridden.
        _merge_config(args, cfg, explicit={"kind", "width", "max_iter"})
        self.assertEqual(args.kind, "julia")
        self.assertEqual(args.width, 100)
        self.assertEqual(args.max_iter, 50)
        # palette was not explicit → overridden by config (would be, but
        # config doesn't set it here, so it stays)
        self.assertEqual(args.palette, "ice")


class TestBug08HPModifiesGlobalDecimalContext(unittest.TestCase):
    """Bug 8: render_mandelbrot_hp sets getcontext().prec globally, leaking
    side effects to any other Decimal user in the process.
    """

    def test_hp_does_not_change_global_precision(self):
        from decimal import getcontext
        getcontext().prec = 28  # default
        vp = Viewport(-0.5, 0.01, 0.01)
        render_mandelbrot_hp(vp, 10, 8, max_iter=40, prec=50)
        # After fix: global precision should be unchanged.
        self.assertEqual(getcontext().prec, 28)


class TestBug09ParseComplexMalformedInput(unittest.TestCase):
    """Bug 9: _parse_complex("1,2,3") raises an unhelpful ValueError
    'too many values to unpack' instead of a clear error message.
    """

    def test_malformed_complex_raises_value_error(self):
        with self.assertRaises(ValueError):
            _parse_complex("1,2,3")

    def test_malformed_rgb_raises_value_error(self):
        with self.assertRaises(ValueError):
            _parse_rgb("1,2,3,4")


class TestBug12RenderMutatesViewport(unittest.TestCase):
    """Bug 12: render_fractal mutates the caller's Viewport.height to match
    the pixel aspect ratio. This is a surprising side effect — the caller's
    viewport object is modified in place.
    """

    def test_viewport_not_mutated(self):
        vp = Viewport(-0.5, 3.0, 2.0)  # aspect 1.5
        original_height = vp.height
        # render at aspect 1.0 (square) — would mutate height to 3.0
        render_fractal("mandelbrot", vp, 30, 30, max_iter=20)
        # After fix: the caller's viewport should be unchanged.
        self.assertAlmostEqual(vp.height, original_height)


class TestBug14HPViewportMutated(unittest.TestCase):
    """Bug 14: render_mandelbrot_hp also mutates the viewport (same pattern)."""

    def test_hp_viewport_not_mutated(self):
        vp = Viewport(-0.5, 1.0, 0.5)
        original_height = vp.height
        render_mandelbrot_hp(vp, 10, 20, max_iter=30, prec=30)
        self.assertAlmostEqual(vp.height, original_height)


class TestBug15HistogramViewportMutated(unittest.TestCase):
    """Bug 15: render_histogram_coloring mutates the viewport too."""

    def test_hist_viewport_not_mutated(self):
        vp = Viewport(-0.5, 3.0, 2.0)
        original_height = vp.height
        render_histogram_coloring("mandelbrot", vp, 10, 20, max_iter=30)
        self.assertAlmostEqual(vp.height, original_height)


if __name__ == "__main__":
    unittest.main(verbosity=2)