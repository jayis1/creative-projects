import math
import unittest
from interval_arithmetic import Interval, interval_product, interval_sum


class IntervalTests(unittest.TestCase):
    def test_addition_contains_all_endpoint_combinations(self):
        result = Interval(1, 2) + Interval(3, 5)
        self.assertLessEqual(result.lower, 4)
        self.assertGreaterEqual(result.upper, 7)

    def test_multiplication_handles_sign_changes(self):
        result = Interval(-2, 3) * Interval(-4, 5)
        self.assertLessEqual(result.lower, -12)
        self.assertGreaterEqual(result.upper, 15)

    def test_division_rejects_zero_crossing(self):
        with self.assertRaises(ZeroDivisionError):
            Interval(1, 2) / Interval(-1, 1)

    def test_helpers(self):
        self.assertIn(6, interval_sum([Interval(1, 2), 4]))
        self.assertIn(-6, interval_product([Interval(-2, -1), 3]))

    def test_transcendental_bounds(self):
        self.assertIn(math.sqrt(4), Interval(3.9, 4.1).sqrt())
        self.assertIn(1.0, Interval(0, math.pi / 2).sin())
        self.assertIn(0.0, Interval(0, 2 * math.pi).cos())
        self.assertEqual(Interval(0, 10).sin(), Interval(-1, 1))
        self.assertIn(math.e, Interval(1, 1).exp())
        with self.assertRaises(ValueError):
            Interval(-1, 2).sqrt()
        with self.assertRaises(ValueError):
            Interval(0, 1).log()

    def test_cosine_captures_interior_minimum(self):
        # The minimum at pi must be included even when neither endpoint is pi.
        self.assertIn(-1.0, Interval(2.0, 4.0).cos())

    def test_rejects_invalid_interval(self):
        with self.assertRaises(ValueError):
            Interval(2, 1)
        with self.assertRaises(ValueError):
            Interval(math.nan, 1)


if __name__ == "__main__":
    unittest.main()
