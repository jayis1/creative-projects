import unittest
from stitch_planner import plan, svg

class PlannerTests(unittest.TestCase):
    def test_runs_and_alternating_scan(self):
        self.assertEqual(plan(["##..#", ".....", "#..##"], 2), [(0.,0.),(1.,0.),(4.,0.),(4.,0.),(4.,2.),(3.,2.),(0.,2.),(0.,2.)])
    def test_invalid_mask(self):
        with self.assertRaises(ValueError): plan(["##", "#"])
    def test_subdivision(self):
        text = svg([(0.,0.), (4.,0.)], 5, 2, 1.5)
        self.assertEqual(text.count("L"), 3)
    def test_stitch_limit(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            plan(["###"], max_stitches=1)
    def test_svg_subdivision_has_output_limit(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            svg([(0., 0.), (1000., 0.)], 1001, 1, 0.001)

    def test_max_stitches_rejects_bool(self):
        with self.assertRaisesRegex(ValueError, "max_stitches"):
            plan(["#"], max_stitches=True)

    def test_svg_rejects_nonpositive_dimensions(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            svg([], 0, 1)

    def test_cli_missing_input_is_a_clean_error(self):
        import subprocess
        import sys
        from pathlib import Path

        script = Path(__file__).parents[1] / "stitch_planner.py"
        result = subprocess.run(
            [sys.executable, str(script), "missing.mask"],
            cwd=Path(__file__).parents[1], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

if __name__ == "__main__": unittest.main()
