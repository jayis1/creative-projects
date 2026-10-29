import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pathlib import Path
from braille import PGM, read_pgm, render


class BrailleTests(unittest.TestCase):
    def test_dot_layout_and_partial_tile(self):
        self.assertEqual(render(PGM(2, 4, 1, (0, 1, 1, 1, 1, 1, 1, 1))), "⠁")
        self.assertEqual(render(PGM(1, 1, 1, (0,))), "⠁")

    def test_threshold_and_invert(self):
        image = PGM(1, 1, 255, (128,))
        self.assertEqual(render(image, 0.6), "⠁")
        self.assertEqual(render(image, 0.6, invert=True), "")

    def test_ascii_pgm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.pgm"
            path.write_bytes(b"P2\n# hi\n2 1\n255\n0 255\n")
            self.assertEqual(read_pgm(path).pixels, (0, 255))

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            render(PGM(1, 1, 1, (0,)), 1.1)


if __name__ == "__main__":
    unittest.main()
