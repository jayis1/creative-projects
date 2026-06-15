"""Tests for BWT codec."""

import pytest
from compression_engine.bwt import BWTCodec, _bwt_transform, _bwt_inverse, _move_to_front_encode, _move_to_front_decode, _rle_encode, _rle_decode


class TestBWTInternals:
    def test_bwt_banana(self):
        data = b"banana"
        transformed, idx = _bwt_transform(data)
        # BWT of "banana" is "annb\xaa" with index... let's verify roundtrip
        recovered = _bwt_inverse(transformed, idx)
        assert recovered == data

    def test_bwt_empty(self):
        transformed, idx = _bwt_transform(b"")
        assert transformed == b""
        assert idx == 0

    def test_bwt_single_char(self):
        data = b"a"
        transformed, idx = _bwt_transform(data)
        recovered = _bwt_inverse(transformed, idx)
        assert recovered == data

    def test_mtf_roundtrip(self):
        data = bytes([3, 1, 4, 1, 5])
        encoded = _move_to_front_encode(data)
        decoded = _move_to_front_decode(encoded)
        assert decoded == data

    def test_rle_roundtrip(self):
        data = bytes([0, 0, 0, 5, 5, 3])
        encoded = _rle_encode(data)
        decoded = _rle_decode(encoded)
        assert decoded == data

    def test_rle_no_runs(self):
        data = bytes([1, 2, 3, 4, 5])
        encoded = _rle_encode(data)
        decoded = _rle_decode(encoded)
        assert decoded == data

    def test_rle_empty(self):
        assert _rle_encode(b"") == b""
        assert _rle_decode(b"") == b""


class TestBWTCodec:
    @pytest.fixture
    def codec(self):
        return BWTCodec()

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

    def test_banana(self, codec):
        data = b"banana"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_repeated_pattern(self, codec):
        data = b"abcabcabc" * 10
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_single_char(self, codec):
        data = b"x"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_english_text(self, codec):
        data = b"The quick brown fox jumps over the lazy dog."
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_all_same_byte(self, codec):
        data = b"a" * 50
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data