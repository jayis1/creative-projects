import math
import tempfile
import unittest
from pathlib import Path
from main import generate, thermal_step, erode, write_pgm, write_ppm

class TerrainTests(unittest.TestCase):
    def test_generation_is_seeded_and_bounded(self):
        a = generate(8, 5, 4)
        self.assertEqual(a, generate(8, 5, 4))
        self.assertTrue(all(0 <= v <= 1 for row in a for v in row))

    def test_erosion_conserves_mass_and_smooths_peak(self):
        field = [[0., 0., 0.], [0., 1., 0.], [0., 0., 0.]]
        before = sum(map(sum, field))
        result = thermal_step(field, talus=0, rate=.5)
        self.assertAlmostEqual(before, sum(map(sum, result)))
        self.assertLess(result[1][1], 1.)
        self.assertTrue(any(result[y][x] > 0 for x, y in ((0, 1), (2, 1), (1, 0), (1, 2))))

    def test_color_ppm_header_and_pixel_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'color.ppm'
            write_ppm([[0.0, .5, 1.0]], path)
            lines = path.read_text().splitlines()
            self.assertEqual(lines[:3], ['P3', '3 1', '255'])
            self.assertEqual(len(lines[3].split()), 9)

    def test_rejects_non_numeric_height_values(self):
        for bad in ([["ridge"]], [[True]]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                thermal_step(bad)

    def test_invalid_grids_and_controls(self):
        for bad in ([], [[1], [1, 2]], [[math.nan]]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                thermal_step(bad)
        with self.assertRaises(ValueError):
            erode([[0.]], -1)
        with self.assertRaises(ValueError):
            thermal_step([[0.]], rate=2)

    def test_pgm_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x.pgm'
            write_pgm([[0, 1]], path)
            self.assertEqual(path.read_text().splitlines()[:3], ['P2', '2 1', '255'])

if __name__ == '__main__':
    unittest.main()
