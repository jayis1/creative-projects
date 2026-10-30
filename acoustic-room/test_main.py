import contextlib
import io
import math
import unittest
from main import Room, impulse_response, main

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
        self.assertEqual(reflected, sorted(reflected, key=lambda arrival: (arrival[0], arrival[2])))

    def test_negative_image_uses_near_wall_absorption(self):
        room = Room((6, 5, 3), (1, 1, 1.5), (1, 1, 1.5), (0.1, 0.9, 0.0, 0.0, 0.0, 0.0))
        _, arrivals = impulse_response(room, 1, 0.05, 4000)
        by_image = {image: amplitude for _, amplitude, image in arrivals}
        self.assertAlmostEqual(by_image[(-1, 0, 0)], math.sqrt(0.9) / 2.0)

    def test_two_bounces_attenuate_by_both_opposing_walls(self):
        room = Room((6, 5, 3), (1, 1, 1.5), (1, 1, 1.5), (0.1, 0.9, 0.0, 0.0, 0.0, 0.0))
        _, arrivals = impulse_response(room, 2, 0.05, 4000)
        by_image = {image: amplitude for _, amplitude, image in arrivals}
        expected = math.sqrt(0.9 * 0.1) / 12.0
        self.assertAlmostEqual(by_image[(2, 0, 0)], expected)

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            impulse_response(self.room, -1)
        outside = Room((6, 5, 3), (7, 1, 1), (4, 3, 1), (0.2,) * 6)
        with self.assertRaises(ValueError):
            impulse_response(outside)

    def test_summary_and_custom_wall_absorption(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--summary", "--absorption", "0.1", "0.3", "0.2", "0.4", "0.5", "0.6"]), 0)
        self.assertIn("Sabine RT60 estimate:", output.getvalue())
        self.assertIn("arrivals=125", output.getvalue())

if __name__ == "__main__":
    unittest.main()
