import unittest
from tiling import TilingSolver, normalize, orientations, render

class TilingTests(unittest.TestCase):
    def test_two_cells_two_dominoes(self):
        solutions = TilingSolver([(0,0),(0,1)], [[(0,0)],[(0,0)]]).solve(5)
        self.assertEqual(len(solutions), 2)
        self.assertEqual(render([(0,0),(0,1)], solutions[0]), '01')

    def test_domino_orientation_deduplicated(self):
        self.assertEqual(len(list(orientations([(0,0),(0,1)]))), 2)

    def test_area_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            TilingSolver([(0,0)], [[(0,0)],[(0,0)]])

    def test_duplicate_piece_cells_rejected(self):
        with self.assertRaises(ValueError):
            TilingSolver([(0,0)], [[(0,0),(0,0)]])

    def test_generator_board_is_supported(self):
        board = ((r,c) for r,c in [(0,0),(0,1)])
        self.assertEqual(len(TilingSolver(board, [[(0,0)],[(0,0)]]).solve()), 1)

    def test_duplicate_board_cell_rejected(self):
        with self.assertRaises(ValueError):
            TilingSolver([(0,0),(0,0)], [[(0,0)],[(0,0)]])

if __name__ == '__main__':
    unittest.main()
