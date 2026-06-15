"""Tests for DEFLATE codec."""

import pytest
from compression_engine.deflate import DeflateCodec, _length_to_code, _code_to_length, _distance_to_code, _code_to_distance


class TestDeflateTables:
    def test_length_code_roundtrip(self):
        for length in [3, 4, 10, 11, 18, 19, 34, 258]:
            code, extra_val, extra_bits = _length_to_code(length)
            decoded = _code_to_length(code, extra_val)
            assert decoded == length, f"Length {length} -> code {code} -> {decoded}"

    def test_distance_code_roundtrip(self):
        for dist in [1, 2, 3, 4, 5, 7, 13, 25, 49, 16385, 24577]:
            code, extra_val, extra_bits = _distance_to_code(dist)
            decoded = _code_to_distance(code, extra_val)
            assert decoded == dist, f"Distance {dist} -> code {code} -> {decoded}"

    def test_all_lengths(self):
        """Test every possible length value."""
        for length in range(3, 259):
            code, extra_val, extra_bits = _length_to_code(length)
            decoded = _code_to_length(code, extra_val)
            assert decoded == length

    def test_invalid_length(self):
        with pytest.raises(ValueError):
            _length_to_code(2)  # Below minimum

    def test_invalid_distance(self):
        with pytest.raises(ValueError):
            _distance_to_code(0)  # Below minimum


class TestDeflateCodec:
    @pytest.fixture
    def codec(self):
        return DeflateCodec()

    def test_simple_roundtrip(self, codec):
        data = b"hello world"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_empty_data(self, codec):
        data = b""
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_repeated_data(self, codec):
        data = b"abcabcabc" * 20
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_no_matches(self, codec):
        data = b"abcdefgh"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_run_of_same_byte(self, codec):
        data = b"a" * 300
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_binary_data(self, codec):
        data = bytes(range(50)) * 3
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_compression_on_repetitive(self, codec):
        data = b"ab" * 500
        compressed = codec.compress(data)
        assert len(compressed) < len(data)

    def test_english_text(self, codec):
        data = b"The quick brown fox jumps over the lazy dog. " * 20
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data