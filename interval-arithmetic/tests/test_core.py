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

    def test_rejects_invalid_interval(self):
        with self.assertRaises(ValueError):
            Interval(2, 1)
        with self.assertRaises(ValueError):
            Interval(math.nan, 1)


if __name__ == "__main__":
    unittest.main()
