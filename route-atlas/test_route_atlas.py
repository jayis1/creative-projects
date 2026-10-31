import unittest
from route_atlas import Network, Trip, format_time


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.net = Network([
            Trip(("A", "B", "C"), (10, 20, 30), "slow"),
            Trip(("A", "D", "C"), (12, 18, 25), "fast"),
            Trip(("C", "E"), (28, 40), "early"),
            Trip(("C", "E"), (35, 42), "later"),
        ])

    def test_earliest_arrival_not_fewest_stops(self):
        j = self.net.route("A", "C", 9)
        self.assertIsNotNone(j)
        assert j is not None
        self.assertEqual((j.arrival, [x.trip_id for x in j.legs]), (25, ["fast"]))

    def test_transfer_and_missed_connection(self):
        j = self.net.route("A", "E", 9)
        self.assertIsNotNone(j)
        assert j is not None
        self.assertEqual(j.arrival, 40)
        self.assertEqual(j.transfers, 1)

    def test_transfer_limit_and_unreachable(self):
        self.assertIsNone(self.net.route("A", "E", 9, max_transfers=0))
        self.assertIsNone(self.net.route("missing", "E", 0))

    def test_identity(self):
        j = self.net.route("A", "A", 17)
        self.assertIsNotNone(j)
        assert j is not None
        self.assertEqual(j.arrival, 17)
        self.assertEqual(j.legs, ())

    def test_invalid_trips(self):
        for stops, times in [(('A',), (1,)), (('A','B'), (2,1)), (('A','B'), (0,))]:
            with self.assertRaises(ValueError):
                Trip(stops, times)

    def test_invalid_search_inputs(self):
        for args in [("", "B", 0), ("A", "B", -1), ("A", "B", 0, -1)]:
            with self.assertRaises(ValueError):
                self.net.route(*args)

    def test_clock_format(self):
        self.assertEqual(format_time(1501), "01:01 (+1d)")
        with self.assertRaises(ValueError):
            format_time(-1)


if __name__ == "__main__":
    unittest.main()
