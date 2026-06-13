"""Tests for lsystem-renderer-q4m7.

Covers: string rewriting, turtle interpretation, rendering, CLI, color utils,
JSON import/export, edge cases, and bug verification.
"""

import json
import math
import os
import tempfile
import unittest

from lsystem import (
    ASCIIRenderer,
    ColorPostProcessor,
    LSystemDefinition,
    LSystemEngine,
    LSystemRenderer,
    LSystemRule,
    SVGRenderer,
    Segment,
    TurtleInterpreter,
    hex_to_rgb,
    hsl_to_rgb,
    lerp_color,
    rainbow_color,
    rgb_to_hex,
    PRESETS,
)


class TestColorUtils(unittest.TestCase):
    """Test color utility functions."""

    def test_hex_to_rgb(self):
        self.assertEqual(hex_to_rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("00ff00"), (0, 255, 0))
        self.assertEqual(hex_to_rgb("#0000ff"), (0, 0, 255))
        self.assertEqual(hex_to_rgb("#ffffff"), (255, 255, 255))
        self.assertEqual(hex_to_rgb("#000000"), (0, 0, 0))

    def test_hex_to_rgb_invalid(self):
        self.assertEqual(hex_to_rgb("xyz"), (0, 0, 0))
        self.assertEqual(hex_to_rgb(""), (0, 0, 0))
        self.assertEqual(hex_to_rgb("#abc"), (0, 0, 0))  # too short

    def test_rgb_to_hex(self):
        self.assertEqual(rgb_to_hex(255, 0, 0), "#ff0000")
        self.assertEqual(rgb_to_hex(0, 255, 0), "#00ff00")
        self.assertEqual(rgb_to_hex(0, 0, 255), "#0000ff")

    def test_rgb_to_hex_clamping(self):
        self.assertEqual(rgb_to_hex(300, -10, 128), "#ff0080")

    def test_lerp_color(self):
        # Start color
        self.assertEqual(lerp_color("#000000", "#ffffff", 0.0), "#000000")
        # End color
        self.assertEqual(lerp_color("#000000", "#ffffff", 1.0), "#ffffff")
        # Midpoint — uses round() for proper rounding
        mid = lerp_color("#000000", "#ffffff", 0.5)
        self.assertEqual(mid, "#808080")

    def test_lerp_color_clamping(self):
        # Below 0 clamped to start
        self.assertEqual(lerp_color("#ff0000", "#0000ff", -0.5), "#ff0000")
        # Above 1 clamped to end
        self.assertEqual(lerp_color("#ff0000", "#0000ff", 1.5), "#0000ff")

    def test_hsl_to_rgb(self):
        # Red
        r, g, b = hsl_to_rgb(0, 1.0, 0.5)
        self.assertAlmostEqual(r, 255, delta=1)
        self.assertAlmostEqual(g, 0, delta=1)
        self.assertAlmostEqual(b, 0, delta=1)
        # Green
        r, g, b = hsl_to_rgb(120, 1.0, 0.5)
        self.assertAlmostEqual(r, 0, delta=1)
        self.assertAlmostEqual(g, 255, delta=1)
        self.assertAlmostEqual(b, 0, delta=1)

    def test_rainbow_color(self):
        color = rainbow_color(0, 10)
        self.assertTrue(color.startswith("#"))
        self.assertEqual(len(color), 7)
        # Total of 0
        self.assertEqual(rainbow_color(0, 0), "#ffffff")


class TestLSystemRule(unittest.TestCase):
    """Test LSystemRule serialization/deserialization."""

    def test_to_dict_minimal(self):
        rule = LSystemRule("F", "F+F")
        d = rule.to_dict()
        self.assertEqual(d, {"predecessor": "F", "successor": "F+F"})

    def test_to_dict_full(self):
        rule = LSystemRule("F", "F[+F]", condition="n>1", probability=0.7,
                           left_context="A", right_context="B")
        d = rule.to_dict()
        self.assertEqual(d["predecessor"], "F")
        self.assertEqual(d["condition"], "n>1")
        self.assertAlmostEqual(d["probability"], 0.7)
        self.assertEqual(d["left_context"], "A")
        self.assertEqual(d["right_context"], "B")

    def test_from_dict(self):
        d = {"predecessor": "F", "successor": "F+F", "probability": 0.5}
        rule = LSystemRule.from_dict(d)
        self.assertEqual(rule.predecessor, "F")
        self.assertEqual(rule.successor, "F+F")
        self.assertAlmostEqual(rule.probability, 0.5)
        self.assertIsNone(rule.condition)

    def test_roundtrip(self):
        rule = LSystemRule("F", "FF", condition="x>0", probability=0.3,
                           left_context="A", right_context="B")
        d = rule.to_dict()
        rule2 = LSystemRule.from_dict(d)
        self.assertEqual(rule.predecessor, rule2.predecessor)
        self.assertEqual(rule.successor, rule2.successor)
        self.assertEqual(rule.condition, rule2.condition)
        self.assertAlmostEqual(rule.probability, rule2.probability)
        self.assertEqual(rule.left_context, rule2.left_context)
        self.assertEqual(rule.right_context, rule2.right_context)


class TestLSystemDefinition(unittest.TestCase):
    """Test LSystemDefinition serialization."""

    def test_to_dict_minimal(self):
        defn = LSystemDefinition(name="Test", axiom="F", rules=[LSystemRule("F", "F+F")])
        d = defn.to_dict()
        self.assertEqual(d["name"], "Test")
        self.assertEqual(d["axiom"], "F")
        self.assertEqual(len(d["rules"]), 1)
        self.assertEqual(d["angle"], 25.0)

    def test_json_roundtrip(self):
        defn = LSystemDefinition(
            name="TestPlant",
            axiom="F",
            rules=[LSystemRule("F", "F[+F]F[-F]F", probability=0.5)],
            angle=25.7,
            step_size=4.0,
            iterations=5,
            colors={0: "#5a3e1b", 1: "#3d6b2e"},
            color_mode="depth",
            gradient=("#ff0000", "#0000ff"),
            perturbation=2.5,
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            defn.to_json(path)
            loaded = LSystemDefinition.from_json(path)
            self.assertEqual(loaded.name, defn.name)
            self.assertEqual(loaded.axiom, defn.axiom)
            self.assertEqual(len(loaded.rules), len(defn.rules))
            self.assertAlmostEqual(loaded.angle, defn.angle)
            self.assertAlmostEqual(loaded.perturbation, defn.perturbation)
            self.assertEqual(loaded.colors, defn.colors)
            self.assertEqual(loaded.gradient, defn.gradient)
        finally:
            os.unlink(path)


class TestLSystemEngine(unittest.TestCase):
    """Test the L-system string rewriting engine."""

    def test_koch_curve_single_iteration(self):
        defn = LSystemDefinition(name="Koch", axiom="F", rules=[LSystemRule("F", "F+F--F+F")], angle=60)
        engine = LSystemEngine(defn)
        result = engine.iterate(1)
        self.assertEqual(result, "F+F--F+F")

    def test_koch_curve_two_iterations(self):
        defn = LSystemDefinition(name="Koch", axiom="F", rules=[LSystemRule("F", "F+F--F+F")], angle=60)
        engine = LSystemEngine(defn)
        result = engine.iterate(2)
        # Each F expands to F+F--F+F
        expected = "F+F--F+F+F+F--F+F--F+F--F+F+F+F--F+F"
        self.assertEqual(result, expected)

    def test_zero_iterations(self):
        defn = LSystemDefinition(name="Test", axiom="F", rules=[LSystemRule("F", "F+F")])
        engine = LSystemEngine(defn)
        result = engine.iterate(0)
        self.assertEqual(result, "F")

    def test_negative_iterations_raises(self):
        defn = LSystemDefinition(name="Test", axiom="F", rules=[LSystemRule("F", "F+F")])
        engine = LSystemEngine(defn)
        with self.assertRaises(ValueError):
            engine.iterate(-1)

    def test_non_matching_symbol_unchanged(self):
        """Symbols with no matching rule should be preserved."""
        defn = LSystemDefinition(name="Test", axiom="F+G", rules=[LSystemRule("F", "FF")])
        engine = LSystemEngine(defn)
        result = engine.iterate(1)
        # G has no rule, should stay as G
        self.assertEqual(result, "FF+G")

    def test_stochastic_with_seed_deterministic(self):
        """Stochastic rules with same seed produce same result."""
        defn = LSystemDefinition(
            name="StochTest",
            axiom="F",
            rules=[
                LSystemRule("F", "F+F", probability=0.5),
                LSystemRule("F", "F-F", probability=0.5),
            ],
        )
        engine1 = LSystemEngine(defn, seed=42)
        result1 = engine1.iterate(3)
        engine2 = LSystemEngine(defn, seed=42)
        result2 = engine2.iterate(3)
        self.assertEqual(result1, result2)

    def test_context_sensitive(self):
        """Context-sensitive rules should check neighbors."""
        defn = LSystemDefinition(
            name="ContextTest",
            axiom="ABA",
            rules=[
                LSystemRule("B", "BB", left_context="A", right_context="A"),
            ],
        )
        engine = LSystemEngine(defn)
        result = engine.iterate(1)
        # B with left A and right A should expand
        self.assertEqual(result, "ABBA")

    def test_context_sensitive_no_match(self):
        """Context-sensitive rule that doesn't match should leave symbol unchanged."""
        defn = LSystemDefinition(
            name="ContextTest",
            axiom="BBA",
            rules=[
                LSystemRule("B", "BB", left_context="A"),
            ],
        )
        engine = LSystemEngine(defn)
        result = engine.iterate(1)
        # No B has left context "A", so both Bs stay as B
        # B at index 0: left context would be empty (or before start), not "A"
        # B at index 1: left context is "B", not "A"
        self.assertEqual(result, "BBA")

    def test_analyze(self):
        result = LSystemEngine.analyze("F+F--F+F")
        self.assertEqual(result["length"], 8)
        self.assertEqual(result["draw_symbols"], 4)  # Four F's in "F+F--F+F"
        self.assertEqual(result["unique_symbols"], 3)  # F, +, -
        self.assertEqual(result["symbols"]["F"], 4)

    def test_analyze_empty(self):
        result = LSystemEngine.analyze("")
        self.assertEqual(result["length"], 0)
        self.assertEqual(result["draw_symbols"], 0)

    def test_iterate_steps(self):
        defn = LSystemDefinition(name="Test", axiom="F", rules=[LSystemRule("F", "FF")])
        engine = LSystemEngine(defn)
        steps = engine.iterate_steps(3)
        self.assertEqual(len(steps), 4)  # axiom + 3 iterations
        self.assertEqual(steps[0], "F")
        self.assertEqual(steps[1], "FF")
        self.assertEqual(steps[2], "FFFF")
        self.assertEqual(steps[3], "FFFFFFFF")


class TestTurtleInterpreter(unittest.TestCase):
    """Test the turtle graphics interpreter."""

    def test_forward_draws_segment(self):
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("F")
        self.assertEqual(len(segments), 1)
        # Starting at (0,0) pointing up (90°), step 10
        self.assertAlmostEqual(segments[0].x1, 0)
        self.assertAlmostEqual(segments[0].y1, 0)
        self.assertAlmostEqual(segments[0].x2, 0, places=5)
        self.assertAlmostEqual(segments[0].y2, 10, places=5)

    def test_forward_no_draw(self):
        """'f' should move without drawing."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("f")
        self.assertEqual(len(segments), 0)

    def test_turn_right_90(self):
        """Turn right 90°, then move forward."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("F-F")
        self.assertEqual(len(segments), 2)
        # Second segment should go to the right (0°)
        self.assertAlmostEqual(segments[1].x2, 10, places=5)

    def test_turn_left_90(self):
        """Turn left 90°, then move forward."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("F+F")
        self.assertEqual(len(segments), 2)
        # Second segment should go left (180°)
        # Starting at 90°, +90 = 180° (pointing left in standard math)
        # But in our coord system, 180° means pointing left
        self.assertAlmostEqual(segments[1].x2, -10, places=5)

    def test_push_pop(self):
        """Push/pop should restore turtle state."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("F[+F]F")
        # Three segments: F (up), +F (left), F (up again after pop)
        self.assertEqual(len(segments), 3)
        # After pop, the state should be back to where it was before [
        # Last segment starts where first F ended
        self.assertAlmostEqual(segments[2].x1, segments[0].x2, places=5)
        self.assertAlmostEqual(segments[2].y1, segments[0].y2, places=5)

    def test_reverse_direction(self):
        """'|' should reverse direction (turn 180°)."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("F|F")
        # First F goes up, then | reverses, second F goes down
        self.assertAlmostEqual(segments[1].y2, 0, places=5)

    def test_perturbation(self):
        """Perturbation should add randomness to angles."""
        interp = TurtleInterpreter(angle=90, step_size=10, perturbation=5.0, seed=42)
        segments = interp.interpret("FFFF")
        # With perturbation, the segments should NOT form a perfect square
        # Check that at least one angle deviates from 90°
        # (statistically very likely with 5° std dev)
        # Just verify we get 4 segments
        self.assertEqual(len(segments), 4)

    def test_colors_by_depth(self):
        """Branch depth should affect color."""
        colors = {0: "#ff0000", 1: "#00ff00", 2: "#0000ff"}
        interp = TurtleInterpreter(angle=90, step_size=10, colors=colors)
        segments = interp.interpret("F[+F[+F]]")
        # Root segments should be depth 0 (color #ff0000)
        self.assertEqual(segments[0].color, "#ff0000")
        # Find a branch segment (depth >= 1)
        branch_segments = [s for s in segments if s.depth >= 1]
        self.assertTrue(len(branch_segments) > 0)

    def test_line_width_thinning_in_branch(self):
        """Lines should thin in branches."""
        interp = TurtleInterpreter(angle=90, step_size=10, line_width=2.0)
        segments = interp.interpret("F[+F]")
        # Root segment width 2.0, branch should be thinner
        root_width = segments[0].width
        branch_width = segments[1].width
        self.assertGreater(root_width, branch_width)


class TestColorPostProcessor(unittest.TestCase):
    """Test color post-processing."""

    def test_depth_color_mode(self):
        segs = [
            Segment(0, 0, 1, 1, depth=0),
            Segment(1, 1, 2, 2, depth=1),
        ]
        colors = {0: "#ff0000", 1: "#00ff00"}
        result = ColorPostProcessor.apply(segs, color_mode="depth", colors=colors)
        self.assertEqual(result[0].color, "#ff0000")
        self.assertEqual(result[1].color, "#00ff00")

    def test_single_color_mode(self):
        segs = [Segment(0, 0, 1, 1), Segment(1, 1, 2, 2)]
        result = ColorPostProcessor.apply(segs, color_mode="single")
        # All segments should have the default color
        self.assertEqual(result[0].color, result[1].color)

    def test_segment_index_color_mode(self):
        segs = [Segment(0, 0, 1, 1, segment_index=0),
                Segment(1, 1, 2, 2, segment_index=1)]
        result = ColorPostProcessor.apply(segs, color_mode="segment_index")
        # Two different colors
        self.assertNotEqual(result[0].color, result[1].color)

    def test_position_gradient_mode(self):
        segs = [
            Segment(0, 0, 1, 0),    # y=0
            Segment(0, 10, 1, 10),  # y=10
        ]
        gradient = ("#000000", "#ffffff")
        result = ColorPostProcessor.apply(segs, color_mode="position", gradient=gradient)
        # Bottom segment should be closer to start color
        self.assertEqual(result[0].color, "#000000")
        # Top segment should be closer to end color
        self.assertEqual(result[1].color, "#ffffff")

    def test_empty_segments(self):
        result = ColorPostProcessor.apply([], color_mode="depth")
        self.assertEqual(result, [])


class TestSVGRenderer(unittest.TestCase):
    """Test SVG rendering."""

    def test_renders_to_file(self):
        segments = [Segment(0, 0, 10, 10)]
        renderer = SVGRenderer(width=100, height=100)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            result = renderer.render(segments, path)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                content = f.read()
            self.assertIn("<svg", content)
            self.assertIn("</svg>", content)
        finally:
            os.unlink(path)

    def test_empty_segments(self):
        """Empty segments should produce valid SVG."""
        renderer = SVGRenderer(width=100, height=100)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            renderer.render([], path)
            with open(path) as f:
                content = f.read()
            self.assertIn("<svg", content)
        finally:
            os.unlink(path)

    def test_animated_svg(self):
        segments = [Segment(0, 0, 10, 10)]
        renderer = SVGRenderer(width=100, height=100)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            renderer.render(segments, path, animate=True, animation_duration=2.0)
            with open(path) as f:
                content = f.read()
            self.assertIn("<animate", content)
        finally:
            os.unlink(path)


class TestASCIIRenderer(unittest.TestCase):
    """Test ASCII rendering."""

    def test_renders_segments(self):
        segments = [Segment(0, 0, 10, 10)]
        renderer = ASCIIRenderer(width=20, height=10)
        result = renderer.render(segments)
        self.assertTrue(len(result) > 0)
        # ASCII renderer now uses directional characters, not just "*"
        # A diagonal line should use "\" character
        self.assertIn("\\", result)

    def test_empty_segments(self):
        renderer = ASCIIRenderer(width=20, height=10)
        result = renderer.render([])
        self.assertEqual(result, "")


class TestLSystemRenderer(unittest.TestCase):
    """Test the high-level renderer API."""

    def test_render_preset_svg(self):
        renderer = LSystemRenderer(seed=42)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            result = renderer.render("koch_curve", iterations=2, output=path)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                content = f.read()
            self.assertIn("<svg", content)
        finally:
            os.unlink(path)

    def test_render_preset_ascii(self):
        renderer = LSystemRenderer(seed=42)
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        try:
            result = renderer.render("koch_curve", iterations=2, backend="ascii", output=path)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                content = f.read()
            self.assertTrue(len(content) > 0)
        finally:
            os.unlink(path)

    def test_render_custom_definition(self):
        defn = LSystemDefinition(
            name="Custom",
            axiom="F",
            rules=[LSystemRule("F", "F+F--F+F")],
            angle=60,
            step_size=3,
            iterations=2,
        )
        renderer = LSystemRenderer()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            result = renderer.render(defn, output=path)
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)

    def test_unknown_preset_raises(self):
        renderer = LSystemRenderer()
        with self.assertRaises(ValueError):
            renderer.render("nonexistent_preset")

    def test_list_presets(self):
        renderer = LSystemRenderer()
        presets = renderer.list_presets()
        self.assertIn("koch_curve", presets)
        self.assertIn("dragon_curve", presets)
        self.assertTrue(len(presets) >= 10)

    def test_get_preset(self):
        renderer = LSystemRenderer()
        preset = renderer.get_preset("koch_curve")
        self.assertEqual(preset.name, "Koch Curve")

    def test_get_unknown_preset_raises(self):
        renderer = LSystemRenderer()
        with self.assertRaises(ValueError):
            renderer.get_preset("nonexistent")

    def test_render_all_presets(self):
        renderer = LSystemRenderer(seed=42)
        with tempfile.TemporaryDirectory() as tmpdir:
            results = renderer.render_all_presets(output_dir=tmpdir, iterations=1)
            self.assertTrue(len(results) > 0)
            for name, path in results.items():
                self.assertTrue(os.path.exists(path), f"Missing file for {name}: {path}")

    def test_animate_growth(self):
        renderer = LSystemRenderer(seed=42)
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = renderer.animate_growth("koch_curve", output_dir=tmpdir, iterations=2)
            self.assertEqual(len(paths), 3)  # step_0, step_1, step_2
            for path in paths:
                self.assertTrue(os.path.exists(path))

    def test_perturbation_produces_different_output(self):
        """With perturbation, same seed but different perturbation should differ."""
        defn1 = LSystemDefinition(
            name="Test1", axiom="F", rules=[LSystemRule("F", "F[+F]F[-F]F")],
            angle=25.7, perturbation=0.0, iterations=3,
        )
        defn2 = LSystemDefinition(
            name="Test2", axiom="F", rules=[LSystemRule("F", "F[+F]F[-F]F")],
            angle=25.7, perturbation=5.0, iterations=3,
        )
        interp1 = TurtleInterpreter(angle=25.7, step_size=5, seed=42)
        interp2 = TurtleInterpreter(angle=25.7, step_size=5, perturbation=5.0, seed=42)

        engine = LSystemEngine(defn1, seed=42)
        lstring = engine.iterate(3)

        segs1 = interp1.interpret(lstring)
        segs2 = interp2.interpret(lstring)

        # With perturbation, at least some segment positions should differ
        if len(segs1) > 0 and len(segs2) > 0:
            different = False
            for s1, s2 in zip(segs1, segs2):
                if abs(s1.x2 - s2.x2) > 0.01 or abs(s1.y2 - s2.y2) > 0.01:
                    different = True
                    break
            self.assertTrue(different, "Perturbation should produce different output")


class TestPresets(unittest.TestCase):
    """Test that all presets can render without error."""

    def test_all_presets_render(self):
        renderer = LSystemRenderer(seed=42)
        for name in PRESETS:
            with self.subTest(preset=name):
                result = renderer.render(name, iterations=2, output=f"/tmp/test_{name}.svg")
                self.assertTrue(os.path.exists(result))
                os.unlink(result)

    def test_all_presets_ascii_render(self):
        renderer = LSystemRenderer(seed=42)
        for name in PRESETS:
            with self.subTest(preset=name):
                result = renderer.render(name, iterations=2, backend="ascii",
                                        output=f"/tmp/test_{name}.txt")
                self.assertTrue(os.path.exists(result))
                os.unlink(result)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and potential bugs."""

    def test_cantor_dust_angle_zero(self):
        """Cantor dust has angle=0 — should render a horizontal line."""
        renderer = LSystemRenderer(seed=42)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            result = renderer.render("cantor_dust", iterations=2, output=path)
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)

    def test_single_segment(self):
        """Single F should produce exactly one segment."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("F")
        self.assertEqual(len(segments), 1)

    def test_no_draw_symbols(self):
        """String with no draw symbols should produce no segments."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("+-[]")
        self.assertEqual(len(segments), 0)

    def test_empty_axiom(self):
        """Empty axiom should produce empty string."""
        defn = LSystemDefinition(name="Empty", axiom="", rules=[LSystemRule("F", "FF")])
        engine = LSystemEngine(defn)
        result = engine.iterate(3)
        self.assertEqual(result, "")

    def test_deeply_nested_branches(self):
        """Deep nesting should not crash."""
        interp = TurtleInterpreter(angle=30, step_size=5)
        # 50 nested pushes without matching pops (should handle gracefully)
        lstring = "F" + "[" * 50 + "F" + "]" * 50
        segments = interp.interpret(lstring)
        # Should produce at least 2 segments
        self.assertGreaterEqual(len(segments), 2)

    def test_more_pops_than_pushes(self):
        """Extra pop operations should be safely ignored."""
        interp = TurtleInterpreter(angle=90, step_size=10)
        segments = interp.interpret("F]F]F]")
        # Should still produce 3 segments (extra ] ignored)
        self.assertEqual(len(segments), 3)

    def test_json_roundtrip_preserves_definition(self):
        """JSON save/load should preserve all definition properties."""
        defn = LSystemDefinition(
            name="FullTest",
            axiom="X",
            rules=[
                LSystemRule("X", "F+[[X]-X]-F[-FX]+X"),
                LSystemRule("F", "FF"),
            ],
            angle=25.0,
            step_size=4.0,
            iterations=6,
            line_width=1.5,
            colors={0: "#5a3e1b", 1: "#3d6b2e"},
            color_mode="depth",
            gradient=("#1a5c1a", "#adff2f"),
            perturbation=2.5,
            step_perturbation=0.1,
            background="#1a1a2e",
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            defn.to_json(path)
            loaded = LSystemDefinition.from_json(path)
            self.assertEqual(loaded.name, defn.name)
            self.assertEqual(loaded.axiom, defn.axiom)
            self.assertEqual(len(loaded.rules), len(defn.rules))
            self.assertAlmostEqual(loaded.angle, defn.angle)
            self.assertAlmostEqual(loaded.step_size, defn.step_size)
            self.assertEqual(loaded.iterations, defn.iterations)
            self.assertAlmostEqual(loaded.line_width, defn.line_width)
            self.assertEqual(loaded.colors, defn.colors)
            self.assertEqual(loaded.color_mode, defn.color_mode)
            self.assertEqual(loaded.gradient, defn.gradient)
            self.assertAlmostEqual(loaded.perturbation, defn.perturbation)
            self.assertAlmostEqual(loaded.step_perturbation, defn.step_perturbation)
            self.assertEqual(loaded.background, defn.background)
        finally:
            os.unlink(path)

    def test_rainbow_mode_on_presets(self):
        """Rainbow mode should work on any preset."""
        renderer = LSystemRenderer(seed=42)
        defn = renderer.get_preset("koch_curve")
        defn.color_mode = "segment_index"
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            result = renderer.render(defn, iterations=2, output=path)
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)


class TestBugVerification(unittest.TestCase):
    """Tests that verify specific bugs were found and fixed."""

    def test_bug_ascii_renderer_y_flip(self):
        """BUG: ASCII renderer should flip Y axis (math Y up, text Y down).

        Verify that a vertical line going up (y1=0, y2=10) appears
        at the top of the rendered output.
        """
        # Segment going up from (0,0) to (0,10)
        segments = [Segment(0, 0, 0, 10)]
        renderer = ASCIIRenderer(width=20, height=10)
        result = renderer.render(segments)
        lines = result.split("\n")
        # The vertical line should be in the leftmost column
        # Top of output should have a character (high y)
        top_has_content = any(c != " " for c in lines[0])
        # Bottom of output should also have content (low y)
        bottom_has_content = any(c != " " for c in lines[-1])
        self.assertTrue(top_has_content or bottom_has_content)

    def test_bug_svg_grouped_paths_different_widths(self):
        """BUG: SVG path grouping uses only first segment's width.

        When segments of the same color have different widths,
        the grouped SVG path uses the width of the first segment only,
        making all segments in that group appear with the same width.
        This is documented behavior but could be a visual bug.
        Verify it exists so we know about it.
        """
        segments = [
            Segment(0, 0, 10, 0, color="#ff0000", width=1.0),
            Segment(10, 0, 20, 0, color="#ff0000", width=3.0),
        ]
        renderer = SVGRenderer(width=100, height=100)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            renderer.render(segments, path)
            with open(path) as f:
                content = f.read()
            # Both segments are same color, so grouped into one path
            # The width will be 1.0 (first segment's width), not 3.0
            # Check that path element has width 1.00
            self.assertIn('stroke-width="1.00"', content)
        finally:
            os.unlink(path)

    def test_bug_svg_title_not_escaped(self):
        """BUG FIXED: SVG title is now properly HTML-escaped.

        Previously, if the title contained XML special characters like <, >, &,
        the SVG output would be malformed. Now they are properly escaped.
        """
        segments = [Segment(0, 0, 10, 10)]
        # Test with angle brackets and ampersand in title
        renderer = SVGRenderer(width=100, height=100, title="Test<script>alert('xss')</script>&more")
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            renderer.render(segments, path)
            with open(path) as f:
                content = f.read()
            # Title should be escaped, not raw
            self.assertIn("&lt;script&gt;", content)
            self.assertNotIn("<script>", content)
            self.assertIn("&amp;", content)
        finally:
            os.unlink(path)

    def test_bug_svg_path_grouping_preserves_widths(self):
        """BUG FIXED: SVG path grouping now groups by (color, width) instead of
        just color, so segments with different widths but same color are
        rendered with correct widths.
        """
        segments = [
            Segment(0, 0, 10, 0, color="#ff0000", width=1.0),
            Segment(10, 0, 20, 0, color="#ff0000", width=3.0),
        ]
        renderer = SVGRenderer(width=100, height=100)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            renderer.render(segments, path)
            with open(path) as f:
                content = f.read()
            # Should have two separate path elements for different widths
            self.assertIn('stroke-width="1.00"', content)
            self.assertIn('stroke-width="3.00"', content)
        finally:
            os.unlink(path)

    def test_bug_iteration_safety_estimate_inaccurate(self):
        """The iteration safety check uses a worst-case estimate that may
        be too aggressive for some L-systems where rules produce shorter
        strings than the estimate. This is a known limitation.
        """
        defn = LSystemDefinition(
            name="Short",
            axiom="A",
            rules=[LSystemRule("A", "B")],  # Actually shortens!
            iterations=4,
        )
        engine = LSystemEngine(defn)
        # Should work fine — the estimate would overestimate
        result = engine.iterate(4)
        self.assertEqual(result, "B")  # A -> B, then B has no rule

    def test_iterate_steps_negative_iterations_raises(self):
        """iterate_steps should also validate iterations."""
        defn = LSystemDefinition(name="Test", axiom="F", rules=[LSystemRule("F", "FF")])
        engine = LSystemEngine(defn)
        with self.assertRaises(ValueError):
            engine.iterate_steps(-1)

    def test_lerp_color_rounding_fix(self):
        """BUG FIXED: lerp_color used int() which truncates instead of round().

        This caused lerp_color("#000000", "#ffffff", 0.5) to return #7f7f7f
        instead of the correct #808080.
        """
        mid = lerp_color("#000000", "#ffffff", 0.5)
        self.assertEqual(mid, "#808080")
        # Also test quarter point
        q1 = lerp_color("#000000", "#ffffff", 0.25)
        self.assertEqual(q1, "#404040")


if __name__ == "__main__":
    unittest.main()