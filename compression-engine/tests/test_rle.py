"""Tests for RLE codec."""

import pytest
from compression_engine.rle import RLECodec


class TestRLECodec:
    @pytest.fixture
    def codec(self):
        return RLECodec()

    def test_simple_roundtrip(self, codec):
        data = b"aaabbbcccaaa"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_empty_data(self, codec):
        data = b""
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_no_runs(self, codec):
        data = b"abcdefgh"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_all_same_byte(self, codec):
        data = b"a" * 300
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_escape_byte_literal(self, codec):
        """0xFF bytes should be properly escaped."""
        data = bytes([0xFF])
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_escape_byte_run(self, codec):
        """Run of 0xFF bytes should work."""
        data = bytes([0xFF] * 10)
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_mixed_content(self, codec):
        data = b"hello\x00\x00\x00\x00world\xff\xff\xff"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_crc32_mismatch(self, codec):
        """Tampered data should raise CRC32 error."""
        data = b"aaabbb"
        compressed = bytearray(codec.compress(data))
        # Tamper with checksum bytes (bytes 4-7)
        compressed[4] ^= 0xFF
        with pytest.raises(ValueError, match="CRC32"):
            codec.decompress(bytes(compressed))

    def test_binary_data(self, codec):
        data = bytes(range(256))
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data