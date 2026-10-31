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

    def test_rejects_bad_records(self):
        sim = MESISimulator()
        for record in ((3, "R", 0), (0, "X", 0), (0, "R", -1)):
            with self.subTest(record=record), self.assertRaises(ValueError):
                sim.access(*record)

if __name__ == "__main__":
    unittest.main()
