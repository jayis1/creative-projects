import unittest
from geohash_atlas.geohash import encode, decode, neighbors, cell_size

class GeohashTests(unittest.TestCase):
    def test_known_vector(self): self.assertEqual(encode(42.6, -5.6, 5), "ezs42")
    def test_precision_one(self): self.assertEqual(len(encode(0, 0, 1)), 1)
    def test_decode_known_bounds(self):
        b = decode("ezs42")
        self.assertAlmostEqual(b.south, 42.5830, places=3)
        self.assertAlmostEqual(b.west, -5.625, places=3)
    def test_invalid_coordinate(self):
        with self.assertRaises(ValueError): encode(91, 0)
    def test_invalid_precision(self):
        with self.assertRaises(ValueError): encode(0, 0, 0)
    def test_bad_hash(self):
        with self.assertRaises(ValueError): decode("bad!")
    def test_neighbors_are_eight_unique_adjacent_cells(self):
        result = neighbors("ezs42")
        self.assertEqual(len(result), 8)
        self.assertEqual(len(set(result.values())), 8)
        self.assertIn(encode((decode("ezs42").south + decode("ezs42").north)/2,
                             (decode("ezs42").west + decode("ezs42").east)/2 +
                             cell_size("ezs42")[1], 5), result.values())
    def test_globe_edge_is_clipped(self): self.assertIsNone(neighbors("b")["n"])
    def test_cell_size_shrinks(self):
        self.assertLess(cell_size("ezs42")[0], cell_size("ezs4")[0])

if __name__ == "__main__": unittest.main()
