import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pathlib import Path
from braille import PGM, read_pgm, render, resize


class BrailleTests(unittest.TestCase):
    def test_dot_layout_and_partial_tile(self):
        self.assertEqual(render(PGM(2, 4, 1, (0, 1, 1, 1, 1, 1, 1, 1))), "⠁")
        self.assertEqual(render(PGM(1, 1, 1, (0,))), "⠁")

    def test_resize_preserves_aspect_ratio_and_samples(self):
        image = PGM(2, 2, 255, (0, 64, 128, 255))
        smaller = resize(image, 1)
        self.assertEqual((smaller.width, smaller.height, smaller.pixels), (1, 1, (0,)))
        larger = resize(image, 4)
        self.assertEqual((larger.width, larger.height), (4, 4))
        self.assertEqual(larger.pixels[0], 0)
        self.assertEqual(larger.pixels[-1], 255)

    def test_pgm_rejects_inconsistent_pixels(self):
        with self.assertRaisesRegex(ValueError, "pixel count"):
            PGM(2, 2, 255, (0, 255))
        with self.assertRaisesRegex(ValueError, "pixel outside"):
            PGM(1, 1, 1, (2,))

    def test_invalid_resize_width(self):
        with self.assertRaisesRegex(ValueError, "width"):
            resize(PGM(1, 1, 1, (0,)), 0)

    def test_threshold_and_invert(self):
        image = PGM(1, 1, 255, (128,))
        self.assertEqual(render(image, 0.6), "⠁")
        self.assertEqual(render(image, 0.6, invert=True), "")

    def test_ascii_pgm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.pgm"
            path.write_bytes(b"P2\n# hi\n2 1\n255\n0 255\n")
            self.assertEqual(read_pgm(path).pixels, (0, 255))
            path.write_bytes(b"P2\n2 1\n255\n0 # inline comment\n255\n")
            self.assertEqual(read_pgm(path).pixels, (0, 255))

    def test_dither_is_deterministic(self):
        image = PGM(4, 4, 255, (128,) * 16)
        self.assertEqual(render(image, dither=True), render(image, dither=True))
        self.assertNotEqual(render(image), render(image, dither=True))

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            render(PGM(1, 1, 1, (0,)), 1.1)


if __name__ == "__main__":
    unittest.main()
