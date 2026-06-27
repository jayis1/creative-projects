"""Tests for the solver configuration module."""

import json
import os
import tempfile

import pytest

from simplex.config import SolverConfig, load_config, save_config


def test_default_config():
    """Default config should have sensible values."""
    cfg = SolverConfig()
    assert cfg.max_iter == 10_000
    assert cfg.max_nodes == 10_000
    assert cfg.bland is True
    assert cfg.use_cuts is True
    assert cfg.eps == pytest.approx(1e-7)
    assert cfg.log_level == "WARNING"
    assert cfg.output_format == "json"


def test_config_from_dict():
    """Config should load from a dict, storing unknown keys in 'extra'."""
    cfg = SolverConfig.from_dict({"max_iter": 50000, "bland": False, "custom_key": 42})
    assert cfg.max_iter == 50000
    assert cfg.bland is False
    assert cfg.extra.get("custom_key") == 42


def test_config_merge():
    """merge() should override existing values with non-None overrides."""
    cfg = SolverConfig(max_iter=10000, bland=True)
    merged = cfg.merge({"max_iter": 50000, "bland": None})
    assert merged.max_iter == 50000
    # None should not override.
    assert merged.bland is True


def test_config_to_dict():
    """to_dict should include all known keys plus extra."""
    cfg = SolverConfig(max_iter=10000)
    cfg.extra = {"foo": "bar"}
    d = cfg.to_dict()
    assert d["max_iter"] == 10000
    assert d["foo"] == "bar"


def test_save_and_load_config():
    """save_config and load_config should round-trip."""
    cfg = SolverConfig(max_iter=42000, bland=False, log_level="INFO")
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        path = f.name
    try:
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded.max_iter == 42000
        assert loaded.bland is False
        assert loaded.log_level == "INFO"
    finally:
        os.unlink(path)


def test_load_config_json():
    """load_config should read a JSON config file."""
    data = {"max_iter": 99999, "bland": False, "eps": 1e-5}
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.max_iter == 99999
        assert cfg.bland is False
        assert cfg.eps == pytest.approx(1e-5)
    finally:
        os.unlink(path)


def test_load_config_toml():
    """load_config should read a TOML config file."""
    toml_content = 'max_iter = 12345\nbland = false\nlog_level = "DEBUG"\n'
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
        f.write(toml_content)
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.max_iter == 12345
        assert cfg.bland is False
        assert cfg.log_level == "DEBUG"
    finally:
        os.unlink(path)


def test_load_config_nonexistent_returns_default():
    """load_config with a nonexistent path returns defaults."""
    cfg = load_config("/nonexistent/path/to/config.json")
    assert isinstance(cfg, SolverConfig)
    assert cfg.max_iter == 10_000  # default