import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from privacy_budget import PrivacyCost, clamp_count, laplace_noise, private_sum


class MechanismTests(unittest.TestCase):
    def test_clipping_and_seeded_sum(self):
        value, cost = private_sum([-2, 5, 20], lower=0, upper=10,
                                  epsilon=1, rng=random.Random(4))
        self.assertAlmostEqual(value, 15 + laplace_noise(10, random.Random(4)))
        self.assertEqual(cost, PrivacyCost(1))

    def test_clamp_edges(self):
        self.assertEqual(clamp_count(1, 1, 3), 1)
        self.assertEqual(clamp_count(4, 1, 3), 3)

    def test_composition(self):
        self.assertEqual(PrivacyCost(.4, .01).compose(PrivacyCost(.6, .02)),
                         PrivacyCost(1, .03))

    def test_noise_zero_scale(self):
        self.assertEqual(laplace_noise(0, random.Random(0)), 0)

    def test_reject_invalid_parameters(self):
        for fn in (lambda: clamp_count(1, 2, 1),
                   lambda: laplace_noise(-1),
                   lambda: private_sum([1], lower=0, upper=1, epsilon=0),
                   lambda: PrivacyCost(-1)):
            with self.assertRaises(ValueError):
                fn()

    def test_nonfinite_input_rejected(self):
        with self.assertRaises(ValueError):
            clamp_count(math.inf, 0, 1)


if __name__ == "__main__":
    unittest.main()
