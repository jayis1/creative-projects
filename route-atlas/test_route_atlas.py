import json
import tempfile
import unittest
from pathlib import Path
from route_atlas import Network, Trip, format_time, journey_dict, load_network, main


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

    def test_json_loading_export_and_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feed.json"
            path.write_text(json.dumps({"trips": [{"id": "x", "stops": ["A", "B"], "times": [4, 9]}]}))
            network = load_network(path)
            journey = network.route("A", "B", 0)
            self.assertIsNotNone(journey)
            assert journey is not None
            self.assertEqual(journey_dict(journey)["arrival"], 9)
            self.assertEqual(main([str(path), "--from-stop", "A", "--to-stop", "B", "--json"]), 0)

    def test_bad_json_schedule_and_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "feed.json"
            for text in ('{', '{"trips":[],"extra":1}', '{"trips":[{"stops":["A","B"],"times":[true,3]}]}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_network(path)
            with self.assertRaises(ValueError):
                load_network(Path(folder) / "missing.json")

    def test_trip_rejects_non_string_stops_and_ids(self):
        with self.assertRaises(ValueError):
            Trip(("A", 7), (1, 2))
        with self.assertRaises(ValueError):
            Trip(("A", "B"), (1, 2), 4)

    def test_transfer_bound_is_capped(self):
        with self.assertRaises(ValueError):
            self.net.route("A", "E", 0, max_transfers=101)

    def test_clock_format(self):
        self.assertEqual(format_time(1501), "01:01 (+1d)")
        with self.assertRaises(ValueError):
            format_time(-1)


if __name__ == "__main__":
    unittest.main()
