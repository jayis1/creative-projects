"""Tests for LZW compression codec."""

import pytest
from compression_engine.lzw import LZWCodec


class TestLZWBasic:
    """Basic roundtrip tests for LZW codec."""

    def test_empty_data(self):
        codec = LZWCodec()
        assert codec.decompress(codec.compress(b"")) == b""

    def test_single_byte(self):
        codec = LZWCodec()
        for b in [0, 1, 127, 255]:
            data = bytes([b])
            assert codec.decompress(codec.compress(data)) == data

    def test_repeated_byte(self):
        codec = LZWCodec()
        data = b"\x00" * 1000
        assert codec.decompress(codec.compress(data)) == data

    def test_simple_text(self):
        codec = LZWCodec()
        data = b"hello world! " * 50
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data

    def test_two_bytes(self):
        codec = LZWCodec()
        data = b"\x00\xff"
        assert codec.decompress(codec.compress(data)) == data

    def test_incremental_bytes(self):
        codec = LZWCodec()
        data = bytes(range(256)) * 3
        assert codec.decompress(codec.compress(data)) == data

    def test_abab_pattern(self):
        """Classic LZW pattern that builds up dictionary entries."""
        codec = LZWCodec()
        data = b"ab" * 500
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data

    def test_short_repetitive(self):
        codec = LZWCodec()
        data = b"abc" * 100
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data


class TestLZWConfigurations:
    """Test different max_bits configurations."""

    def test_max_bits_9(self):
        codec = LZWCodec(max_bits=9)
        data = b"hello world" * 50
        assert codec.decompress(codec.compress(data)) == data

    def test_max_bits_12(self):
        codec = LZWCodec(max_bits=12)
        data = b"test data for lzw compression" * 20
        assert codec.decompress(codec.compress(data)) == data

    def test_max_bits_16_default(self):
        codec = LZWCodec()
        data = b"longer test data for lzw" * 50
        assert codec.decompress(codec.compress(data)) == data

    def test_invalid_max_bits_low(self):
        with pytest.raises(ValueError):
            LZWCodec(max_bits=8)

    def test_invalid_max_bits_high(self):
        with pytest.raises(ValueError):
            LZWCodec(max_bits=17)


class TestLZWCRC32:
    """CRC32 integrity tests for LZW."""

    def test_crc32_corruption_in_header(self):
        """Corrupt the CRC32 in the header."""
        codec = LZWCodec()
        data = b"test data for CRC32 check" * 10
        compressed = codec.compress(data)
        # Corrupt byte in the CRC32 field (bytes 4-7)
        corrupted = bytearray(compressed)
        corrupted[5] ^= 0xFF
        with pytest.raises(Exception):
            codec.decompress(bytes(corrupted))

    def test_empty_data_crc32(self):
        codec = LZWCodec()
        compressed = codec.compress(b"")
        # Corrupt the CRC32
        corrupted = bytearray(compressed)
        corrupted[4] ^= 0x01
        with pytest.raises(Exception):
            codec.decompress(bytes(corrupted))


class TestLZWCompression:
    """Test compression effectiveness."""

    def test_repetitive_data_compresses(self):
        codec = LZWCodec()
        data = b"aaaa" * 1000
        compressed = codec.compress(data)
        assert len(compressed) < len(data)

    def test_text_compresses(self):
        codec = LZWCodec()
        data = b"The quick brown fox jumps over the lazy dog. " * 100
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data
        assert len(compressed) < len(data)

    def test_random_roundtrip(self):
        """Random data should still roundtrip even if it doesn't compress well."""
        import random
        random.seed(42)
        codec = LZWCodec(max_bits=12)
        data = bytes(random.randint(0, 255) for _ in range(500))
        compressed = codec.compress(data)
        assert codec.decompress(compressed) == data