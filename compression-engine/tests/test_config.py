"""Tests for configuration module."""

import json
import os
import tempfile
import pytest
from compression_engine.config import (
    load_config, save_config, get_codec_config,
    resolve_pipeline, DEFAULT_CONFIG, _deep_merge,
)


class TestDefaultConfig:
    """Test default configuration."""

    def test_default_config_has_codecs(self):
        assert "codecs" in DEFAULT_CONFIG
        assert "huffman" in DEFAULT_CONFIG["codecs"]
        assert "deflate" in DEFAULT_CONFIG["codecs"]

    def test_default_config_has_pipelines(self):
        assert "pipelines" in DEFAULT_CONFIG
        assert "fast" in DEFAULT_CONFIG["pipelines"]
        assert "balanced" in DEFAULT_CONFIG["pipelines"]

    def test_default_config_has_default_codec(self):
        assert DEFAULT_CONFIG["default_codec"] == "deflate"


class TestLoadSaveConfig:
    """Test config loading and saving."""

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {"default_codec": "huffman", "codecs": {"huffman": {}}}
            json.dump(config, f)
            f.flush()
            path = f.name

        try:
            loaded = load_config(path)
            assert loaded["default_codec"] == "huffman"
        finally:
            os.unlink(path)

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")

    def test_save_creates_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "config.json")
            save_config(DEFAULT_CONFIG, path)
            assert os.path.exists(path)

    def test_deep_merge(self):
        base = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        override = {"b": {"c": 99}, "f": 5}
        result = _deep_merge(base, override)
        assert result["a"] == 1
        assert result["b"]["c"] == 99
        assert result["b"]["d"] == 3
        assert result["e"] == 4
        assert result["f"] == 5


class TestResolvePipeline:
    """Test pipeline resolution."""

    def test_resolve_known_pipeline(self):
        config = DEFAULT_CONFIG
        assert resolve_pipeline(config, "fast") == "rle+lz77"
        assert resolve_pipeline(config, "balanced") == "rle+deflate"
        assert resolve_pipeline(config, "best") == "bwt+huffman"

    def test_resolve_unknown_returns_as_is(self):
        config = DEFAULT_CONFIG
        assert resolve_pipeline(config, "rle+huffman") == "rle+huffman"
        assert resolve_pipeline(config, "unknown") == "unknown"


class TestGetCodecConfig:
    """Test codec configuration retrieval."""

    def test_get_existing_codec(self):
        config = DEFAULT_CONFIG
        lz77_config = get_codec_config(config, "lz77")
        assert "window_size" in lz77_config

    def test_get_missing_codec(self):
        config = DEFAULT_CONFIG
        result = get_codec_config(config, "nonexistent")
        assert result == {}