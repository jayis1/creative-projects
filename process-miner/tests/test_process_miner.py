import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from process_miner import discover

class DiscoveryTests(unittest.TestCase):
    def test_counts_trace_edges(self):
        rows = [{"case":"x","activity":"a","timestamp":"2"},
                {"case":"x","activity":"b","timestamp":"1"},
                {"case":"y","activity":"a","timestamp":"1"}]
        result = discover(rows)
        self.assertEqual(result["cases"], 2)
        self.assertEqual(result["directly_follows"], [{"source":"b","target":"a","count":1}])
        self.assertEqual(result["starts"], {"a":1,"b":1})

    def test_invalid_empty_activity(self):
        with self.assertRaises(ValueError):
            discover([{"case":"x", "activity":"  ", "timestamp":"1"}])

    def test_empty_log(self):
        self.assertEqual(discover([])["cases"], 0)

if __name__ == "__main__":
    unittest.main()
