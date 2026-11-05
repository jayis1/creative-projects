import unittest
from fountain import encode, decode

class FountainTests(unittest.TestCase):
    def test_single_block_round_trip(self):
        data = b"waterfall"
        packets = encode(data, 16, 3, seed=7)
        self.assertEqual(decode(packets, 1, len(data), 16), data)

    def test_all_singleton_packets_recover_multiple_blocks(self):
        data = b"abcdefghijk"
        # Singleton equations carrying known padded source blocks.
        chunks = [data[i:i+4].ljust(4, b"\0") for i in range(0, len(data), 4)]
        packets = [{"indices": [i], "payload": c.hex()} for i, c in enumerate(chunks)]
        self.assertEqual(decode(packets, 3, len(data), 4), data)

    def test_rank_deficiency_is_reported(self):
        with self.assertRaisesRegex(ValueError, "insufficient"):
            decode([{"indices": [0, 1], "payload": "0000"}], 2, 4, 2)

    def test_invalid_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            decode([], 1, 3, 2)

if __name__ == "__main__":
    unittest.main()
