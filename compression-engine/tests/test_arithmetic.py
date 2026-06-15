"""Tests for Arithmetic coding codec."""

import pytest
from compression_engine.arithmetic import ArithmeticCodec


class TestArithmeticBasic:
    """Basic roundtrip tests for Arithmetic codec."""

    def test_empty_data(self):
        codec = ArithmeticCodec()
        assert codec.decompress(codec.compress(b"")) == b""

    def test_single_byte(self):
        codec = ArithmeticCodec()
        for b in [0, 1, 127, 255]:
            data = bytes([b])
            assert codec.decompress(codec.compress(data)) == data

    def test_two_bytes(self):
        codec = ArithmeticCodec()
        data = b"\x00\xff"
        assert codec.decompress(codec.compress(data)) == data

    def test_repeated_byte(self):
        codec = ArithmeticCodec()
        data = b"\x00" * 500
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data

    def test_simple_text(self):
        codec = ArithmeticCodec()
        data = b"hello world! " * 30
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data

    def test_all_bytes(self):
        codec = ArithmeticCodec()
        data = bytes(range(256))
        assert codec.decompress(codec.compress(data)) == data

    def test_repeated_pattern(self):
        codec = ArithmeticCodec()
        data = b"abcabcabc" * 50
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data

    def test_incremental_bytes(self):
        codec = ArithmeticCodec()
        data = bytes(range(256)) * 3
        assert codec.decompress(codec.compress(data)) == data


class TestArithmeticSkewedData:
    """Test arithmetic coding on data with skewed distributions."""

    def test_mostly_zeros(self):
        codec = ArithmeticCodec()
        data = bytes([0] * 900 + [1] * 100)
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data
        # Should compress well due to skewed distribution
        assert len(compressed) < len(data)

    def test_binary_data(self):
        codec = ArithmeticCodec()
        data = bytes([0, 1] * 500)
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data

    def test_english_text(self):
        codec = ArithmeticCodec()
        data = b"The quick brown fox jumps over the lazy dog. " * 50
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data

    def test_mono_byte(self):
        """Data with only one unique byte value."""
        codec = ArithmeticCodec()
        data = b"\x42" * 1000
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data


class TestArithmeticCRC32:
    """CRC32 integrity tests for Arithmetic codec."""

    def test_crc32_corruption_in_header(self):
        """Corrupt the CRC32 in the header — this should always be caught."""
        codec = ArithmeticCodec()
        data = b"test data for CRC32 check"
        compressed = codec.compress(data)
        # Corrupt byte in the CRC32 field (bytes 4-7)
        corrupted = bytearray(compressed)
        corrupted[5] ^= 0xFF  # corrupt CRC32
        with pytest.raises(Exception):
            codec.decompress(bytes(corrupted))

    def test_crc32_corruption_in_payload(self):
        """Corrupt the compressed payload — should be caught if it changes the output."""
        codec = ArithmeticCodec()
        data = b"A longer test string that produces enough compressed data for corruption testing" * 5
        compressed = codec.compress(data)
        # Corrupt a byte in the middle of the payload area (avoiding header and trailing padding)
        # Header is 12 bytes (4 len + 4 crc + 4 precision). Corrupt byte 12 which is
        # right after the header and in the core compressed bitstream.
        if len(compressed) > 16:
            corrupted = bytearray(compressed)
            corrupted[12] ^= 0xFF  # corrupt core payload, not padding
            with pytest.raises(Exception):
                codec.decompress(bytes(corrupted))

    def test_empty_data_crc32(self):
        codec = ArithmeticCodec()
        compressed = codec.compress(b"")
        # Should produce a valid small header
        assert len(compressed) >= 12


class TestArithmeticErrors:
    """Error handling tests."""

    def test_truncated_data(self):
        codec = ArithmeticCodec()
        with pytest.raises(Exception):
            codec.decompress(b"\x00" * 5)

    def test_format_error_short_data(self):
        codec = ArithmeticCodec()
        with pytest.raises(Exception):
            codec.decompress(b"short")