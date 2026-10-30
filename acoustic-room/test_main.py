import unittest
from main import Room, impulse_response

class AcousticRoomTests(unittest.TestCase):
    def setUp(self):
        self.room = Room((6, 5, 3), (1, 1, 1.5), (4, 3, 1.5), (0.2,) * 6)

    def test_direct_arrival_matches_euclidean_distance(self):
        _, arrivals = impulse_response(self.room, 0, 0.1, 4000)
        self.assertEqual(len(arrivals), 1)
        self.assertAlmostEqual(arrivals[0][0], (13 ** 0.5) / 343)

    def test_reverberant_tail_adds_paths(self):
        _, direct = impulse_response(self.room, 0, 0.1, 4000)
        _, reflected = impulse_response(self.room, 2, 0.1, 4000)
        self.assertGreater(len(reflected), len(direct))
        self.assertEqual(reflected, sorted(reflected))

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            impulse_response(self.room, -1)
        outside = Room((6, 5, 3), (7, 1, 1), (4, 3, 1), (0.2,) * 6)
        with self.assertRaises(ValueError):
            impulse_response(outside)

if __name__ == "__main__":
    unittest.main()
