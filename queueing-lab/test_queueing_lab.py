import unittest

from queueing_lab import QueueingNetwork, Route, Station, demo


class QueueingNetworkTests(unittest.TestCase):
    def test_demo_completes_batch_and_is_seed_reproducible(self):
        first = demo(seed=13, customers=80)
        second = demo(seed=13, customers=80)
        self.assertEqual(first, second)
        self.assertEqual(first["customers_entered"], 80)
        self.assertEqual(first["completed"], 80)
        self.assertGreater(first["events"], 80)
        self.assertGreater(first["stations"]["inspection"]["visits"], 80)

    def test_single_station_statistics_and_zero_duration_start(self):
        net = QueueingNetwork([Station("svc", 1, 1.0)], [Route("svc", None, 1.0)], seed=1)
        result = net.run(customers=12, interarrival_mean=2.0)
        self.assertEqual(result["completed"], 12)
        self.assertEqual(result["stations"]["svc"]["visits"], 12)
        self.assertGreaterEqual(result["stations"]["svc"]["mean_wait"], 0.0)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            QueueingNetwork([], [])
        with self.assertRaises(ValueError):
            QueueingNetwork([Station("a", 1, 1.0)], [Route("a", None, 0.8)])
        with self.assertRaises(ValueError):
            QueueingNetwork([Station("a", 1, 1.0)], [Route("a", "missing", 1.0)])

    def test_invalid_run_limits_are_rejected(self):
        net = QueueingNetwork([Station("a", 1, 1.0)], [Route("a", None, 1.0)])
        for customers, gap in [(0, 1), (3, 0), (3, float("inf"))]:
            with self.subTest(customers=customers, gap=gap), self.assertRaises(ValueError):
                net.run(customers=customers, interarrival_mean=gap)


if __name__ == "__main__":
    unittest.main()
