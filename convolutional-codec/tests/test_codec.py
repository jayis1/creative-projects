import json
import subprocess
import sys
import unittest

from convolutional_codec.channels import BinarySymmetricChannel
from convolutional_codec.codec import ConvolutionalCodec, Trellis


class CodecTests(unittest.TestCase):
    def setUp(self):
        self.codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)))

    def test_encode_known_sequence(self):
        encoded = self.codec.encode([1, 0, 1, 1])
        self.assertEqual(encoded, [1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1])

    def test_round_trip_without_noise(self):
        payload = [1, 0, 1, 1, 0, 0, 1]
        encoded = self.codec.encode(payload)
        decoded = self.codec.decode(encoded)
        self.assertEqual(decoded.bits, payload)
        self.assertEqual(decoded.path_metric, 0)

    def test_corrects_single_bit_error(self):
        payload = [1, 1, 0, 1, 0, 0]
        encoded = self.codec.encode(payload)
        encoded[3] ^= 1
        decoded = self.codec.decode(encoded)
        self.assertEqual(decoded.bits, payload)

    def test_channel_validates_probability(self):
        with self.assertRaises(ValueError):
            BinarySymmetricChannel(1.1)

    def test_cli_encode(self):
        completed = subprocess.run(
            [sys.executable, "-m", "convolutional_codec", "encode", "1011"],
            cwd="/root/projects/creative-projects/convolutional-codec",
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stdout.strip(), "111000010111")

    def test_cli_decode(self):
        completed = subprocess.run(
            [sys.executable, "-m", "convolutional_codec", "decode", "111000010111"],
            cwd="/root/projects/creative-projects/convolutional-codec",
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["bits"], [1, 0, 1, 1])


if __name__ == "__main__":
    unittest.main()
