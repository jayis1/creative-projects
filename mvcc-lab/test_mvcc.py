import unittest
from unittest.mock import patch
from io import StringIO

from mvcc import ScheduleError, main, run_schedule


class SnapshotTests(unittest.TestCase):
    def test_stale_writer_aborts_and_snapshot_reads_are_stable(self):
        result = run_schedule({"initial": {"x": 1}, "transactions": [
            {"name": "old", "ops": [{"get": "x"}]},
            {"name": "new", "ops": [{"put": ["x", 2]}, {"commit": True}]},
            {"name": "old", "ops": [{"get": "x"}, {"put": ["x", 3]}, {"commit": True}]},
        ]})
        self.assertEqual([r.get("value") for r in result if "value" in r], [1, 1])
        self.assertEqual(result[-1]["commit"], "aborted")

    def test_delete_is_visible_only_to_later_snapshot(self):
        result = run_schedule({"initial": {"x": "v"}, "transactions": [
            {"name": "d", "ops": [{"delete": "x"}, {"commit": True}]},
            {"name": "r", "ops": [{"get": "x"}, {"commit": True}]},
        ]})
        self.assertEqual(result[1]["value"], None)

    def test_read_only_old_snapshot_can_commit(self):
        result = run_schedule({"transactions": [
            {"name": "r", "ops": [{"get": "missing"}]},
            {"name": "w", "ops": [{"put": ["x", 1]}, {"commit": True}]},
            {"name": "r", "ops": [{"commit": True}]},
        ]})
        self.assertEqual(result[-1]["commit"], "committed")

    def test_snapshot_scan_is_sorted_prefixed_and_overlays_writes(self):
        result = run_schedule({"initial": {"a:2": 2, "a:1": 1, "b:1": 9}, "transactions": [
            {"name": "t", "ops": [{"put": ["a:3", 3]}, {"delete": "a:1"}, {"scan": "a:"}, {"commit": True}]},
        ]})
        self.assertEqual(result[0]["rows"], {"a:2": 2, "a:3": 3})

    def test_scan_preserves_rows_whose_json_value_is_null(self):
        result = run_schedule({"initial": {"nullable": None}, "transactions": [
            {"name": "t", "ops": [{"scan": ""}, {"commit": True}]},
        ]})
        self.assertEqual(result[0]["rows"], {"nullable": None})

    def test_cli_reads_schedule_from_stdin(self):
        schedule = '{"transactions": [{"name": "t", "ops": [{"commit": true}]}]}'
        output = StringIO()
        with patch("sys.stdin", StringIO(schedule)), patch("sys.stdout", output):
            self.assertEqual(main(["run", "-"]), 0)
        self.assertIn('"commit": "committed"', output.getvalue())

    def test_invalid_unfinished_schedule_is_rejected(self):
        with self.assertRaises(ScheduleError):
            run_schedule({"transactions": [{"name": "x", "ops": [{"put": ["a", 1]}]}]})


if __name__ == "__main__":
    unittest.main()
