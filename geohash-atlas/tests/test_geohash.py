import unittest
from geohash_atlas.geohash import encode, decode

class GeohashTests(unittest.TestCase):
    def test_known_vector(self):
        self.assertEqual(encode(42.6, -5.6, 5), "ezs42")
    def test_precision_one(self):
        self.assertEqual(len(encode(0, 0, 1)), 1)
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

if __name__ == "__main__": unittest.main()
