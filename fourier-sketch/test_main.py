import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from main import Term, dft, reconstruct, resample_polyline, select_terms, validate_points, write_svg

class FourierSketchTests(unittest.TestCase):
    def test_square_round_trip_with_all_terms(self):
        points = [[1, 1], [-1, 1], [-1, -1], [1, -1]]
        rebuilt = reconstruct(dft(points), 4)
        for actual, expected in zip(rebuilt, points):
            self.assertAlmostEqual(actual[0], expected[0], places=10)
            self.assertAlmostEqual(actual[1], expected[1], places=10)

    def test_constant_path_has_finite_svg_coordinates(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "constant.svg"
            write_svg([[2, 3], [2, 3]], path)
            self.assertIn("polyline", path.read_text())
            self.assertNotIn("nan", path.read_text().lower())

    def test_rejects_nonfinite_points(self):
        with self.assertRaises(ValueError):
            validate_points([[0, 0], [math.inf, 2]])

    def test_term_selection_is_deterministic(self):
        terms = [Term(2, 0, 1), Term(0, 1, 0), Term(-1, 2, 0)]
        self.assertEqual([t.frequency for t in select_terms(terms, 2)], [-1, 0])

    def test_cli_exports_reconstructed_points_as_json(self):
        with tempfile.TemporaryDirectory() as d:
            source, target = Path(d) / "shape.json", Path(d) / "curve.json"
            source.write_text('{"points": [[1, 0], [0, 1], [-1, 0], [0, -1]]}')
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("main.py")), str(source), str(target), "--terms", "4", "--samples", "8", "--format", "json"],
                check=False, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            exported = json.loads(target.read_text())
            self.assertEqual(len(exported["points"]), 8)
            self.assertEqual(set(exported), {"points"})

    def test_cli_writes_svg_from_json_and_arc_resampling(self):
        with tempfile.TemporaryDirectory() as d:
            source, target = Path(d) / "shape.json", Path(d) / "shape.svg"
            source.write_text('{"points": [[1, 0], [0, 1], [-1, 0], [0, -1]]}')
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("main.py")), str(source), str(target), "--terms", "4", "--resample", "16"],
                check=False, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("<polyline", target.read_text())

    def test_resampling_includes_closing_edge_for_periodic_fourier_input(self):
        result = resample_polyline([[0, 0], [4, 0], [4, 4], [0, 4]], 4)
        expected = [[0, 0], [4, 0], [4, 4], [0, 4]]
        for actual, target in zip(result, expected):
            self.assertAlmostEqual(actual[0], target[0])
            self.assertAlmostEqual(actual[1], target[1])

    def test_arc_length_resampling_is_uniform_and_wraps(self):
        result = resample_polyline([[0, 0], [4, 0], [4, 2]], 4, closed=False)
        expected = [[0, 0], [1.5, 0], [3, 0], [4, 0.5]]
        for actual, target in zip(result, expected):
            self.assertAlmostEqual(actual[0], target[0])
            self.assertAlmostEqual(actual[1], target[1])
        self.assertEqual(len(resample_polyline([[1, 2], [1, 2]], 3)), 3)

if __name__ == "__main__":
    unittest.main()
