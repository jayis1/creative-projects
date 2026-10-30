import unittest
from main import floats, plain_weave, render, twill, validate_draft


class DraftTests(unittest.TestCase):
    def test_twill_has_cyclic_structure(self):
        draft = twill(4)
        self.assertEqual(draft[0], [1, 0, 0, 0])
        self.assertEqual([sum(row) for row in draft], [1] * 4)

    def test_float_lengths_and_render(self):
        draft = [[1, 0, 1], [0, 1, 0]]
        self.assertEqual(floats(draft), {"warp": 1, "weft": 1, "worst": 1})
        self.assertEqual(render(draft), "█·█\n·█·")

    def test_plain_weave_checkerboard(self):
        self.assertEqual(plain_weave(3), [[0, 1, 0], [1, 0, 1], [0, 1, 0]])

    def test_bounds(self):
        with self.assertRaises(ValueError):
            twill(1)

    def test_rejects_ragged_draft(self):
        with self.assertRaises(ValueError):
            validate_draft([[0, 1], [1]])


if __name__ == "__main__":
    unittest.main()
