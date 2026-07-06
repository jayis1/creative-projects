"""Tests for the config module."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fmindex.config import FMIndexConfig, load_config, save_config, ConfigError


def test_default_config():
    cfg = FMIndexConfig()
    cfg.validate()
    assert cfg.sample_rate == 16
    assert cfg.backend == "wavelet_tree"
    assert cfg.serialization.format == "binary"


def test_invalid_sample_rate():
    cfg = FMIndexConfig(sample_rate=0)
    with pytest.raises(ConfigError):
        cfg.validate()


def test_invalid_backend():
    cfg = FMIndexConfig(backend="invalid")
    with pytest.raises(ConfigError):
        cfg.validate()


def test_from_dict():
    data = {
        "sample_rate": 32,
        "backend": "wavelet_matrix",
        "serialization": {"format": "json", "compress_level": 9},
    }
    cfg = FMIndexConfig.from_dict(data)
    assert cfg.sample_rate == 32
    assert cfg.backend == "wavelet_matrix"
    assert cfg.serialization.format == "json"
    assert cfg.serialization.compress_level == 9


def test_to_dict_roundtrip():
    cfg = FMIndexConfig(sample_rate=8, backend="wavelet_matrix")
    d = cfg.to_dict()
    cfg2 = FMIndexConfig.from_dict(d)
    assert cfg2.sample_rate == 8
    assert cfg2.backend == "wavelet_matrix"


def test_json_save_load():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = f.name
    try:
        cfg = FMIndexConfig(sample_rate=4, backend="wavelet_matrix")
        save_config(cfg, path)
        cfg2 = load_config(path)
        assert cfg2.sample_rate == 4
        assert cfg2.backend == "wavelet_matrix"
    finally:
        os.unlink(path)


def test_load_nonexistent():
    with pytest.raises(ConfigError):
        load_config("/nonexistent/config.json")


def test_invalid_compress_level():
    cfg = FMIndexConfig()
    cfg.serialization.compress_level = 15
    with pytest.raises(ConfigError):
        cfg.validate()