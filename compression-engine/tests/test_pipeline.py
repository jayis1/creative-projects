"""Tests for Pipeline codec."""

import pytest
from compression_engine.pipeline import Pipeline, create_pipeline, CODEC_REGISTRY


class TestPipeline:
    def test_rle_huffman(self):
        pipe = create_pipeline("rle+huffman")
        data = b"a" * 100 + b"b" * 100 + b"c" * 100
        compressed = pipe.compress(data)
        decompressed = pipe.decompress(compressed)
        assert decompressed == data

    def test_rle_lz77(self):
        pipe = create_pipeline("rle+lz77")
        data = b"abcabcabc" * 20
        compressed = pipe.compress(data)
        decompressed = pipe.decompress(compressed)
        assert decompressed == data

    def test_delta_huffman(self):
        pipe = Pipeline(["delta", "huffman"])
        data = bytes(range(100))
        compressed = pipe.compress(data)
        decompressed = pipe.decompress(compressed)
        assert decompressed == data

    def test_delta_deflate(self):
        pipe = Pipeline(["delta", "deflate"])
        data = bytes(range(100)) * 3
        compressed = pipe.compress(data)
        decompressed = pipe.decompress(compressed)
        assert decompressed == data

    def test_unknown_codec(self):
        with pytest.raises(ValueError, match="Unknown codec"):
            Pipeline(["nonexistent"])

    def test_empty_data(self):
        pipe = create_pipeline("rle+huffman")
        data = b""
        compressed = pipe.compress(data)
        decompressed = pipe.decompress(compressed)
        assert decompressed == data

    def test_create_pipeline(self):
        pipe = create_pipeline("rle+huffman")
        assert len(pipe.codecs) == 2
        assert pipe.codec_names == ["rle", "huffman"]

    def test_all_codecs_registered(self):
        """Check that all expected codecs are in the registry."""
        expected = {"huffman", "lz77", "bwt", "deflate", "rle", "delta"}
        assert set(CODEC_REGISTRY.keys()) == expected