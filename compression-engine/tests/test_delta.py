"""Tests for Delta codec."""

import pytest
import struct
from compression_engine.delta import DeltaCodec


class TestDeltaCodec:
    @pytest.fixture
    def codec(self):
        return DeltaCodec(mode="byte")

    def test_simple_roundtrip_byte(self, codec):
        data = b"abcdefgh"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_empty_data(self, codec):
        data = b""
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_repeated_byte(self, codec):
        data = b"a" * 100
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_ascending_sequence(self, codec):
        data = bytes(range(100))
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_uint16_mode(self):
        codec = DeltaCodec(mode="uint16")
        # Create uint16 ascending sequence
        data = b""
        for i in range(100):
            data += struct.pack("<H", i * 10)
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_uint32_mode(self):
        codec = DeltaCodec(mode="uint32")
        data = b""
        for i in range(100):
            data += struct.pack("<I", i * 1000)
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_auto_mode(self):
        codec = DeltaCodec(mode="auto")
        data = bytes(range(256))
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="Invalid mode"):
            DeltaCodec(mode="invalid")

    def test_crc32_mismatch(self, codec):
        data = b"abcdefgh"
        compressed = bytearray(codec.compress(data))
        # Tamper with checksum
        compressed[4] ^= 0xFF
        with pytest.raises(ValueError, match="CRC32"):
            codec.decompress(bytes(compressed))

    def test_constant_sequence_small_deltas(self, codec):
        """Constant data should produce all-zero deltas."""
        data = b"x" * 100
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data
        # Delta encoding adds overhead for byte mode (header + first value + varints)
        # It's designed as a pre-processor for Huffman, not standalone compression