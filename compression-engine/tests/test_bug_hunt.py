"""Bug hunt tests for compression engine - Phase 3.

These tests verify bugs found during code review and prove fixes work.
"""

import pytest
import struct
from compression_engine.huffman import HuffmanCodec
from compression_engine.lz77 import LZ77Codec
from compression_engine.bwt import BWTCodec, _bwt_transform, _bwt_inverse, _rle_encode, _rle_decode
from compression_engine.deflate import DeflateCodec, _lz77_tokenize, _length_to_code, _distance_to_code
from compression_engine.rle import RLECodec
from compression_engine.delta import DeltaCodec
from compression_engine.pipeline import Pipeline, create_pipeline
from compression_engine.bitio import BitWriter, BitReader


class TestLZ77MinMatchBug:
    """BUG #7: LZ77 decompress hardcodes min_match=3, but encoder allows custom values."""

    def test_custom_min_match_roundtrip(self):
        """Custom min_match should be preserved in compressed data header."""
        codec = LZ77Codec(min_match=4, window_size=256)
        data = b"abcabcabc"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        # With min_match=4, the "abc" repeat of length 3 is NOT encoded as a match
        assert decompressed == data

    def test_min_match_5_roundtrip(self):
        codec = LZ77Codec(min_match=5, window_size=256)
        data = b"abcdefabcdef"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_min_match_affects_compressed_size(self):
        """Higher min_match should produce larger compressed output for repetitive data."""
        codec3 = LZ77Codec(min_match=3, window_size=256)
        codec5 = LZ77Codec(min_match=5, window_size=256)
        data = b"abcabcabc" * 10
        c3 = codec3.compress(data)
        c5 = codec5.compress(data)
        # With min_match=3, LZ77 can encode the 3-byte repeats
        # With min_match=5, the 3-byte repeats become literals
        assert len(c3) <= len(c5)


class TestDeltaTrailingBytesBug:
    """BUG #8: Delta codec uint16/uint32 modes ignore trailing bytes."""

    def test_uint16_odd_length(self):
        """uint16 mode with odd number of bytes should handle trailing byte."""
        codec = DeltaCodec(mode="uint16")
        # 5 bytes = 2 uint16 values + 1 trailing byte
        data = struct.pack("<HH", 100, 200) + b"\x42"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_uint32_non_aligned(self):
        """uint32 mode with non-aligned data should handle trailing bytes."""
        codec = DeltaCodec(mode="uint32")
        # 6 bytes = 1 uint32 + 2 trailing bytes
        data = struct.pack("<I", 1000) + b"\xAB\xCD"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data


class TestDeltaAutoDetectBug:
    """BUG #9: Delta auto-detect with very short data can misfire."""

    def test_auto_detect_short_data(self):
        """Auto mode with very short data should still roundtrip correctly."""
        codec = DeltaCodec(mode="auto")
        # 2 bytes - too short for uint16 auto-detect
        data = b"\x00\x01"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_auto_detect_single_byte(self):
        codec = DeltaCodec(mode="auto")
        data = b"\xFF"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data


class TestBWTRLEEdgeCases:
    """Test BWT internal RLE encoding edge cases."""

    def test_rle_pair_then_same_byte(self):
        """Two identical bytes followed by the same byte again."""
        data = bytes([5, 5, 5])  # Run of 3
        encoded = _rle_encode(data)
        decoded = _rle_decode(encoded)
        assert decoded == data

    def test_rle_single_then_pair(self):
        """Single byte then pair of same value."""
        data = bytes([3, 5, 5])
        encoded = _rle_encode(data)
        decoded = _rle_decode(encoded)
        assert decoded == data

    def test_rle_max_run(self):
        """Maximum run length (255)."""
        data = bytes([42]) * 255
        encoded = _rle_encode(data)
        decoded = _rle_decode(encoded)
        assert decoded == data

    def test_rle_long_run_exceeding_max(self):
        """Run exceeding 255 should be split."""
        data = bytes([42]) * 300
        encoded = _rle_encode(data)
        decoded = _rle_decode(encoded)
        assert decoded == data

    def test_bwt_roundtrip_with_many_repeats(self):
        """BWT with highly repetitive data that creates long MTF runs."""
        codec = BWTCodec()
        data = b"a" * 50
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data


class TestDeflateEdgeCases:
    """DEFLATE edge case tests."""

    def test_deflate_distance_code_boundary(self):
        """Test distance code at boundary values."""
        # Distance 1 (code 0, no extra bits)
        code, extra, bits = _distance_to_code(1)
        assert code == 0
        assert extra == 0
        assert bits == 0

    def test_deflate_length_code_boundary(self):
        """Test length codes at boundary values."""
        # Length 3 (minimum, code 257)
        code, extra, bits = _length_to_code(3)
        assert code == 257
        assert extra == 0
        assert bits == 0

        # Length 258 (maximum, code 285)
        code, extra, bits = _length_to_code(258)
        assert code == 285
        assert extra == 0
        assert bits == 0

    def test_deflate_large_distance(self):
        """Test with data that has long-distance matches."""
        codec = DeflateCodec()
        # Create data with a long-distance match
        data = b"A" * 1000 + b"B" * 10 + b"A" * 100
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_deflate_all_byte_values(self):
        """Test with all 256 byte values."""
        codec = DeflateCodec()
        data = bytes(range(256))
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data


class TestRLEEdgeCases:
    """RLE edge cases that might reveal bugs."""

    def test_rle_exact_boundary_run(self):
        """Run of exactly 3 (minimum for RLE encoding)."""
        codec = RLECodec()
        data = b"aaa"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_rle_run_of_257(self):
        """Run of 257 bytes (max single RLE run is 257 = 255 + 2)."""
        codec = RLECodec()
        data = b"x" * 257
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_rle_run_of_258(self):
        """Run of 258 (requires two RLE entries: 257 + 1 literal)."""
        codec = RLECodec()
        data = b"x" * 258
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_rle_pair_of_escape_byte(self):
        """Two consecutive 0xFF bytes (should each be individually escaped)."""
        codec = RLECodec()
        data = bytes([0xFF, 0xFF])
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_rle_alternating_bytes(self):
        """Alternating bytes (no compressible runs)."""
        codec = RLECodec()
        data = bytes([i % 2 for i in range(100)])
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data


class TestHuffmanEdgeCases:
    """Huffman edge case tests."""

    def test_huffman_two_byte_types(self):
        """Data with only two distinct byte values."""
        codec = HuffmanCodec()
        data = bytes([0, 255] * 50)
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_huffman_all_same_byte_large(self):
        """Large data with single repeated byte."""
        codec = HuffmanCodec()
        data = b"\x00" * 10000
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_huffman_crc32_tampering(self):
        """CRC32 mismatch should be detected."""
        codec = HuffmanCodec()
        data = b"test data for crc"
        compressed = bytearray(codec.compress(data))
        # Tamper with the CRC32 bytes (bytes 4-7)
        compressed[4] ^= 0xFF
        with pytest.raises(ValueError, match="CRC32"):
            codec.decompress(bytes(compressed))


class TestBitIOEdgeCases:
    """Bit I/O edge cases."""

    def test_write_then_flush_empty(self):
        """BitWriter flush with no data written."""
        writer = BitWriter()
        result = writer.flush()
        assert result == b""

    def test_read_bits_zero(self):
        """Reading 0 bits should return 0 without advancing."""
        reader = BitReader(b"\xFF")
        val = reader.read_bits(0)
        assert val == 0
        # Should still have 8 bits remaining
        assert reader.bits_remaining == 8

    def test_bit_roundtrip_single_bit(self):
        """Write and read a single bit."""
        writer = BitWriter()
        writer.write_bit(1)
        data = writer.flush()
        reader = BitReader(data)
        assert reader.read_bit() == 1

    def test_bit_writer_bit_length(self):
        """Bit length tracking."""
        writer = BitWriter()
        assert writer.bit_length == 0
        writer.write_bit(0)
        assert writer.bit_length == 1
        writer.write_bits(0xFF, 8)
        assert writer.bit_length == 9