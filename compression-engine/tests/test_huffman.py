"""Tests for Huffman codec."""

import pytest
from compression_engine.huffman import HuffmanCodec, _build_frequency_table, _build_tree, _build_code_table, _lengths_to_canonical


class TestHuffmanInternals:
    def test_frequency_table(self):
        freq = _build_frequency_table(b"aaabbc")
        assert freq[ord('a')] == 3
        assert freq[ord('b')] == 2
        assert freq[ord('c')] == 1
        assert freq[256] == 1  # EOF

    def test_build_tree_single_symbol(self):
        freq = [0] * 257
        freq[ord('a')] = 5
        freq[256] = 1
        tree = _build_tree(freq)
        assert tree is not None

    def test_canonical_codes(self):
        lengths = {0: 2, 1: 2, 2: 3, 3: 3}
        canonical = _lengths_to_canonical(lengths)
        # Canonical: sort by (length, symbol)
        # sym=0 len=2: code=00 (0), sym=1 len=2: code=01 (1)
        # Then shift left by (3-2)=1 and increment:
        # sym=2 len=3: code=(1+1)<<1 = 4 = 100
        # sym=3 len=3: code=4+1 = 5 = 101
        assert canonical[0] == (0, 2)
        assert canonical[1] == (1, 2)
        assert canonical[2] == (4, 3)  # 100 in binary
        assert canonical[3] == (5, 3)  # 101 in binary

    def test_canonical_empty(self):
        assert _lengths_to_canonical({}) == {}


class TestHuffmanCodec:
    @pytest.fixture
    def codec(self):
        return HuffmanCodec()

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

    def test_single_byte(self, codec):
        data = b"a"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_repeated_byte(self, codec):
        data = b"aaaaaa"
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_all_byte_values(self, codec):
        data = bytes(range(256))
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_binary_data(self, codec):
        data = bytes([0, 1, 2, 255, 254, 253, 0, 1, 2])
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_repeated_pattern(self, codec):
        data = b"abcabcabcabc" * 100
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_compression_reduces_size_for_repetitive(self, codec):
        data = b"a" * 1000
        compressed = codec.compress(data)
        # Huffman should compress all-same-byte data significantly
        assert len(compressed) < len(data)

    def test_english_text(self, codec):
        data = b"The quick brown fox jumps over the lazy dog. " * 10
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        assert decompressed == data

    def test_data_too_large(self, codec):
        with pytest.raises(ValueError, match="too large"):
            codec.compress(b"x" * (0xFFFFFFFF + 1))