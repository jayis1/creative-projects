import unittest
from coherence import MESISimulator

class MESITests(unittest.TestCase):
    def test_read_sharing_and_writer_invalidation(self):
        sim = MESISimulator()
        self.assertEqual(sim.access(0, "R", 0), "E")
        self.assertEqual(sim.access(1, "R", 0), "S")
        self.assertEqual(sim.access(0, "W", 0), "M")
        self.assertNotIn(0, sim.caches[1].lines)
        self.assertEqual(sim.stats["invalidations"], 1)

    def test_dirty_eviction_is_written_back(self):
        sim = MESISimulator(capacity=1)
        sim.access(0, "W", 0)
        sim.access(0, "R", 16)
        self.assertEqual(sim.stats["writebacks"], 1)

    def test_trace_record_shape_is_validated(self):
        sim = MESISimulator()
        with self.assertRaisesRegex(ValueError, "record 0"):
            sim.run([[0, "R"]])

    def test_writer_invalidating_modified_peer_counts_writeback(self):
        sim = MESISimulator()
        sim.access(0, "W", 0)
        sim.access(1, "W", 0)
        self.assertEqual(sim.stats["writebacks"], 1)
        self.assertEqual(sim.stats["invalidations"], 1)

    def test_operation_totals_match_trace_length(self):
        sim = MESISimulator()
        sim.run([[0, "R", 0], [1, "W", 16], [0, "R", 32]])
        self.assertEqual(sim.report()["stats"]["reads"], 2)
        self.assertEqual(sim.report()["stats"]["writes"], 1)

    def test_boolean_indices_and_addresses_are_rejected(self):
        sim = MESISimulator()
        for record in ((True, "R", 0), (0, "R", True)):
            with self.subTest(record=record), self.assertRaises(ValueError):
                sim.access(*record)

    def test_rejects_bad_records(self):
        sim = MESISimulator()
        for record in ((3, "R", 0), (0, "X", 0), (0, "R", -1)):
            with self.subTest(record=record), self.assertRaises(ValueError):
                sim.access(*record)

if __name__ == "__main__":
    unittest.main()
