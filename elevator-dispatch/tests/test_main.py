import unittest

from main import Request, simulate, summarize, validate_requests


class DispatchTests(unittest.TestCase):
    def test_demo_assignment_and_metrics(self):
        rows = simulate([Request(0, 0, 5), Request(1, 2, 8)], floors=10, cars=2)
        self.assertEqual([(r.car, r.pickup_time, r.arrival_time, r.wait) for r in rows],
                         [(0, 0, 5, 0), (1, 3, 9, 2)])

    def test_single_car_waits_for_previous_trip(self):
        rows = simulate([Request(0, 0, 4), Request(1, 1, 2)], cars=1)
        self.assertEqual(rows[1].pickup_time, 7)
        self.assertEqual(rows[1].wait, 6)

    def test_unsorted_calls_are_processed_chronologically(self):
        rows = simulate([Request(5, 0, 1), Request(1, 0, 2)])
        self.assertEqual([r.request.time for r in rows], [1, 5])

    def test_empty_requests(self):
        self.assertEqual(simulate([]), [])

    def test_invalid_requests_rejected(self):
        with self.assertRaises(ValueError):
            validate_requests([Request(-1, 0, 1)], 3)
        with self.assertRaises(ValueError):
            validate_requests([Request(0, 0, 0)], 3)
        with self.assertRaises(ValueError):
            validate_requests([Request(0, 0, 3)], 3)

    def test_summary_metrics_and_empty_case(self):
        rows = simulate([Request(0, 0, 5), Request(1, 2, 8)], cars=2)
        self.assertEqual(summarize(rows, 2), {
            "request_count": 2, "total_wait": 2, "average_wait": 1.0,
            "maximum_wait": 2, "car_requests": [1, 1],
        })
        self.assertEqual(summarize([], 2)["average_wait"], 0.0)
        self.assertEqual(summarize([], 2)["maximum_wait"], 0)

    def test_direct_api_rejects_non_integer_values(self):
        for bad_request in (Request(0.5, 0, 1), Request(0, True, 1)):
            with self.subTest(request=bad_request), self.assertRaises(ValueError):
                simulate([bad_request])
        with self.assertRaises(ValueError):
            simulate([], floors=3.5)
        with self.assertRaises(ValueError):
            simulate([], cars=True)

    def test_car_count_bounds(self):
        with self.assertRaises(ValueError):
            simulate([], cars=0)
        with self.assertRaises(ValueError):
            simulate([], cars=65)


if __name__ == "__main__":
    unittest.main()
