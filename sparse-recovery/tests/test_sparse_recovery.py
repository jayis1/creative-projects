import math
import unittest

from sparse_recovery import gaussian_matrix, matvec, recover, sparse_signal


class SparseRecoveryTests(unittest.TestCase):
    def test_seeded_sparse_round_trip(self):
        truth = sparse_signal(32, 4, seed=17)
        matrix = gaussian_matrix(48, 32, seed=23)
        result = recover(matrix, matvec(matrix, truth), 4, max_iterations=3000)
        error = math.sqrt(sum((a - b) ** 2 for a, b in zip(truth, result.estimate)))
        self.assertLess(error, 1e-5)
        self.assertTrue(all(math.isfinite(x) for x in result.residuals))

    def test_seed_reproducibility(self):
        self.assertEqual(gaussian_matrix(3, 4, 5), gaussian_matrix(3, 4, 5))
        self.assertEqual(sparse_signal(8, 3, 9), sparse_signal(8, 3, 9))

    def test_invalid_iteration_limit(self):
        with self.assertRaisesRegex(ValueError, "max_iterations"):
            recover([[1.0]], [1.0], 1, max_iterations=0)

    def test_zero_energy_matrix(self):
        with self.assertRaisesRegex(ValueError, "positive finite energy"):
            recover([[0.0, 0.0]], [0.0], 1)

    def test_rejects_nonfinite_input(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            matvec([[1.0]], [float("nan")])

    def test_rejects_ragged_matrix(self):
        with self.assertRaisesRegex(ValueError, "rectangular"):
            matvec([[1.0], [1.0, 2.0]], [2.0])

    def test_empty_signal_support(self):
        self.assertEqual(sparse_signal(4, 0, seed=1), [0.0] * 4)

    def test_measurement_dimension_mismatch(self):
        with self.assertRaisesRegex(ValueError, "measurement count"):
            recover([[1.0, 0.0], [0.0, 1.0]], [1.0], 1)

    def test_invalid_tolerance(self):
        with self.assertRaisesRegex(ValueError, "tolerance"):
            recover([[1.0]], [1.0], 1, tolerance=float("inf"))

    def test_zero_dimensions_rejected(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            gaussian_matrix(0, 3)


if __name__ == "__main__":
    unittest.main()
