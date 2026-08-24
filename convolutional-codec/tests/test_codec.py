import argparse
import json
import subprocess
import sys
import unittest

from convolutional_codec.channels import AWGNChannel, BinarySymmetricChannel, bpsk_modulate, hard_decide
from convolutional_codec.cli import _parse_float_list
from convolutional_codec.codec import BlockInterleaver, ConvolutionalCodec, Trellis
from convolutional_codec.crc import CRC


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

    def test_awgn_channel_emits_soft_values(self):
        samples = AWGNChannel(6.0, seed=3).transmit([0, 1, 0, 1])
        self.assertEqual(len(samples), 4)
        self.assertTrue(any(not float(sample).is_integer() for sample in samples))

    def test_soft_decode_round_trip_without_noise(self):
        payload = [1, 0, 0, 1, 1]
        encoded = self.codec.encode(payload)
        samples = bpsk_modulate(encoded)
        decoded = self.codec.decode_soft(samples)
        self.assertEqual(decoded.bits, payload)

    def test_punctured_codec_round_trip(self):
        codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)), puncture_pattern=(1, 1, 0, 1))
        payload = [1, 0, 1, 1, 0, 1]
        encoded = codec.encode(payload)
        decoded = codec.decode(encoded)
        self.assertEqual(decoded.bits, payload)

    def test_punctured_hard_decode_matches_soft_decode_without_noise(self):
        codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)), puncture_pattern=(1, 1, 0, 1))
        for payload in (
            [0, 0, 0, 0, 0],
            [1, 0, 0, 1, 1],
            [1, 1, 1, 0, 1],
            [0, 1, 0, 1, 0],
        ):
            encoded = codec.encode(payload)
            hard = codec.decode(encoded)
            soft = codec.decode_soft(bpsk_modulate(encoded))
            self.assertEqual(hard.bits, soft.bits)

    def test_crc_frame_round_trip(self):
        crc = CRC(0b10011, width=4)
        payload = [1, 0, 1, 1, 0, 1, 0, 0]
        encoded = self.codec.encode_frame(payload, crc=crc)
        decoded = self.codec.decode_frame(encoded, crc=crc)
        self.assertEqual(decoded["payload_bits"], payload)
        self.assertTrue(decoded["crc_ok"])

    def test_block_interleaver_round_trip(self):
        interleaver = BlockInterleaver(2, 3)
        payload = [0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1]
        self.assertEqual(interleaver.deinterleave(interleaver.interleave(payload)), payload)

    def test_block_interleaver_supports_real_valued_samples(self):
        interleaver = BlockInterleaver(2, 3)
        samples = [1.0, -0.2, 0.5, 0.7, -1.3, 0.1]
        self.assertEqual(interleaver.deinterleave(interleaver.interleave(samples)), samples)

    def test_simulate_bsc_with_interleaver_and_crc(self):
        crc = CRC(0b10011, width=4)
        interleaver = BlockInterleaver(2, 14)
        payload = [1, 0, 1, 1, 0, 1, 0, 0]
        result = self.codec.simulate_bsc(payload, 0.0, seed=9, crc=crc, interleaver=interleaver)
        self.assertEqual(result["decoded_bits"], payload)
        self.assertTrue(result["crc_ok"])

    def test_hard_decision_helper(self):
        self.assertEqual(hard_decide([1.5, -0.1, 0.0, -2.0]), [0, 1, 0, 1])

    def test_parse_float_list_rejects_empty_fields(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            _parse_float_list("1.0,,2.0")

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

    def test_cli_decode_soft(self):
        completed = subprocess.run(
            [sys.executable, "-m", "convolutional_codec", "decode-soft", "--", "-1.0,1.0,-1.0,1.0,1.0,-1.0,1.0,-1.0,1.0,1.0"],
            cwd="/root/projects/creative-projects/convolutional-codec",
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertIn("bits", payload)


if __name__ == "__main__":
    unittest.main()
