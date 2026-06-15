"""Tests for LZ77 codec."""

import pytest
from compression_engine.lz77 import LZ77Codec


class TestLZ77Codec:
    @pytest.fixture
    def codec(self):
        return LZ77Codec(window_size=256, min_match=3, max_match=258)

    def test_simple_roundtrip(self, codec):
        data = b"hello world hello world"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_empty_data(self, codec):
        data = b""
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_no_matches(self, codec):
        data = b"abcdefgh"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_repeated_data(self, codec):
        data = b"abcabcabcabc"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_run_of_same_byte(self, codec):
        data = b"a" * 100
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_binary_data(self, codec):
        data = bytes(range(256)) * 2
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_single_byte(self, codec):
        data = b"x"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_compression_on_repetitive_data(self, codec):
        data = b"ab" * 1000
        compressed = codec.compress(data)
        assert len(compressed) < len(data)

    def test_custom_window_size(self):
        codec = LZ77Codec(window_size=16, min_match=3, max_match=258)
        data = b"hello hello hello"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_long_match(self, codec):
        data = b"abcdefghij" * 30
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data