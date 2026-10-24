import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packet_forge import DecodeError, decode_frame, demo_frame, summarize

class PacketTests(unittest.TestCase):
    def test_demo_udp_decodes(self):
        packet = decode_frame(demo_frame())
        self.assertEqual((packet.source, packet.destination), ("192.0.2.1", "198.51.100.2"))
        self.assertEqual((packet.source_port, packet.destination_port, packet.payload_length), (53000, 9000, 5))

    def test_summary_counts(self):
        self.assertEqual(summarize([demo_frame(), b"bad"])["accepted"], 1)
        self.assertEqual(summarize([demo_frame(), b"bad"])["rejected"], 1)

    def test_short_frame(self):
        with self.assertRaises(DecodeError):
            decode_frame(b"short")

if __name__ == "__main__":
    unittest.main()
