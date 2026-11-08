import math
import random
import sys
import unittest
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from privacy_budget import (PrivacyCost, clamp_count, laplace_noise, private_histogram,
                            private_mean, private_sum)


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

    def test_mean_uses_fixed_size_replacement_sensitivity(self):
        value, _ = private_mean([0, 10], lower=0, upper=10, epsilon=1,
                                rng=random.Random(9))
        self.assertAlmostEqual(value, 5 + laplace_noise(5, random.Random(9)))

    def test_mean_rejects_empty(self):
        with self.assertRaises(ValueError):
            private_mean([], lower=0, upper=1, epsilon=1)

    def test_histogram_noisy_bins(self):
        output, cost = private_histogram(["a", "a", "b"], categories=["a", "b", "c"],
                                         epsilon=1, rng=random.Random(2))
        self.assertEqual(set(output), {"a", "b", "c"})
        self.assertEqual(cost, PrivacyCost(1))
        self.assertNotEqual(output["c"], 0)

    def test_histogram_rejects_undeclared_category(self):
        with self.assertRaises(ValueError):
            private_histogram(["secret"], categories=["public"], epsilon=1)

    def test_composition_rejects_delta_total_at_least_one(self):
        with self.assertRaises(ValueError):
            PrivacyCost(0, .6).compose(PrivacyCost(0, .5))

    def test_histogram_rejects_non_string_domain_cleanly(self):
        with self.assertRaises(ValueError):
            private_histogram([], categories=cast(list[str], [["unhashable"]]), epsilon=1)

    def test_cli_mean_emits_structured_json(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from privacy_budget import main

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--mode", "mean", "0", "10", "--lower", "0",
                                   "--upper", "10", "--seed", "9"]), 0)
        import json
        result = json.loads(output.getvalue())
        self.assertEqual(result["mechanism"], "mean")
        self.assertEqual(result["epsilon"], 1.0)
        self.assertIn("noisy_mean", result)

    def test_cli_histogram_requires_categories(self):
        from privacy_budget import main
        with self.assertRaises(SystemExit) as error:
            main(["--mode", "histogram", "red"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
