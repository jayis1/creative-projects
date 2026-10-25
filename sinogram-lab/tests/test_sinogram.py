import math
import tempfile
import unittest
from pathlib import Path

from io_tools import save_pgm
from sinogram_lab import demo, phantom, project, reconstruct, render


class SinogramTests(unittest.TestCase):
    def test_phantom_and_projection_shape(self):
        image = phantom(6)
        self.assertEqual((len(image), len(image[0])), (6, 6))
        self.assertEqual(len(project(image, angles=4, detectors=8)), 4)
        self.assertEqual(len(project(image, angles=4, detectors=8)[0]), 8)

    def test_projection_and_reconstruction_are_finite(self):
        image = phantom(5)
        scan = project(image, angles=8, detectors=10)
        result = reconstruct(scan, 5, iterations=3)
        self.assertTrue(all(math.isfinite(v) and v >= 0 for row in result for v in row))
        self.assertTrue(any(v > 0 for row in result for v in row))

    def test_demo_is_reproducible(self):
        self.assertEqual(demo(seed=3, size=5), demo(seed=3, size=5))

    def test_render_shape(self):
        lines = render([[0, 1], [0.5, 0]]) .splitlines()
        self.assertEqual([len(line) for line in lines], [2, 2])

    def test_pgm_export(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "image.pgm"
            save_pgm([[0, 1], [.5, .25]], target)
            self.assertEqual(target.read_text().splitlines()[:4], ["P2", "# Sinogram Lab reconstruction", "2 2", "255"])
            self.assertEqual(target.read_text().splitlines()[-2:], ["0 255", "128 64"])

    def test_invalid_inputs(self):
        for call in (lambda: phantom(1), lambda: project([[1, 2], [3]], 4),
                     lambda: reconstruct([[1], [1, 2]], 2),
                     lambda: reconstruct([[math.nan]], 2),
                     lambda: reconstruct([[1]], 2, relaxation=math.inf)):
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
