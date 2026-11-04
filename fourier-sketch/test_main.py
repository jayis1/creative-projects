import math
import tempfile
import unittest
from pathlib import Path
from main import Term, dft, reconstruct, select_terms, validate_points, write_svg

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

if __name__ == "__main__":
    unittest.main()
