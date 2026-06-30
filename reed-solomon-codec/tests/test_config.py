"""Tests for the configuration system (CodecConfig).

Tests cover:
- Default values and validation
- JSON / YAML / TOML serialisation round-trips
- File load/save with format auto-detection
- Logging setup
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from reed_solomon.config import CodecConfig, _HAS_YAML, _HAS_TOML


# ---------------------------------------------------------------------------
# Defaults and validation
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    """Test default configuration values."""

    def test_defaults(self):
        c = CodecConfig()
        assert c.nsym == 10
        assert c.interleaving_depth == 4
        assert c.log_level == "WARNING"
        assert c.log_file is None

    def test_validate_ok(self):
        c = CodecConfig(nsym=16, interleaving_depth=3, log_level="INFO")
        c.validate()  # should not raise

    def test_validate_bad_nsym(self):
        c = CodecConfig(nsym=-1)
        with pytest.raises(ValueError):
            c.validate()

    def test_validate_bad_nsym_high(self):
        c = CodecConfig(nsym=300)
        with pytest.raises(ValueError):
            c.validate()

    def test_validate_bad_depth(self):
        c = CodecConfig(interleaving_depth=0)
        with pytest.raises(ValueError):
            c.validate()

    def test_validate_bad_log_level(self):
        c = CodecConfig(log_level="Bogus")
        with pytest.raises(ValueError):
            c.validate()


# ---------------------------------------------------------------------------
# Dict conversion
# ---------------------------------------------------------------------------


class TestConfigDict:
    """Test dict conversion."""

    def test_to_dict(self):
        c = CodecConfig(nsym=20, interleaving_depth=8)
        d = c.to_dict()
        assert d["nsym"] == 20
        assert d["interleaving_depth"] == 8

    def test_from_dict(self):
        d = {"nsym": 14, "interleaving_depth": 2, "unknown_key": "ignored"}
        c = CodecConfig.from_dict(d)
        assert c.nsym == 14
        assert c.interleaving_depth == 2

    def test_round_trip_dict(self):
        c1 = CodecConfig(nsym=32, interleaving_depth=6, log_level="DEBUG")
        d = c1.to_dict()
        c2 = CodecConfig.from_dict(d)
        assert c2.nsym == 32
        assert c2.interleaving_depth == 6
        assert c2.log_level == "DEBUG"


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


class TestConfigJSON:
    """Test JSON serialisation."""

    def test_json_round_trip(self):
        c1 = CodecConfig(nsym=12, interleaving_depth=3, log_level="INFO")
        text = c1.to_json()
        c2 = CodecConfig.from_json(text)
        assert c2.nsym == 12
        assert c2.interleaving_depth == 3
        assert c2.log_level == "INFO"

    def test_json_has_valid_json(self):
        c = CodecConfig(nsym=8)
        text = c.to_json()
        parsed = json.loads(text)  # should not raise
        assert parsed["nsym"] == 8


# ---------------------------------------------------------------------------
# YAML
# ---------------------------------------------------------------------------


class TestConfigYAML:
    """Test YAML serialisation (skipped if PyYAML not installed)."""

    @pytest.mark.skipif(not _HAS_YAML, reason="PyYAML not installed")
    def test_yaml_round_trip(self):
        c1 = CodecConfig(nsym=18, interleaving_depth=7, log_level="ERROR")
        text = c1.to_yaml()
        c2 = CodecConfig.from_yaml(text)
        assert c2.nsym == 18
        assert c2.interleaving_depth == 7
        assert c2.log_level == "ERROR"


# ---------------------------------------------------------------------------
# TOML
# ---------------------------------------------------------------------------


class TestConfigTOML:
    """Test TOML serialisation (skipped if no TOML parser)."""

    @pytest.mark.skipif(not _HAS_TOML, reason="No TOML parser available")
    def test_toml_round_trip(self):
        c1 = CodecConfig(nsym=22, interleaving_depth=5, log_level="DEBUG")
        text = c1.to_toml()
        c2 = CodecConfig.from_toml(text)
        assert c2.nsym == 22
        assert c2.interleaving_depth == 5
        assert c2.log_level == "DEBUG"


# ---------------------------------------------------------------------------
# File load/save
# ---------------------------------------------------------------------------


class TestConfigFile:
    """Test file-based config load/save."""

    def test_save_load_json(self, tmp_path):
        path = tmp_path / "config.json"
        c1 = CodecConfig(nsym=16, interleaving_depth=4, log_level="INFO")
        c1.save(path)
        c2 = CodecConfig.load(path)
        assert c2.nsym == 16
        assert c2.interleaving_depth == 4
        assert c2.log_level == "INFO"

    @pytest.mark.skipif(not _HAS_YAML, reason="PyYAML not installed")
    def test_save_load_yaml(self, tmp_path):
        path = tmp_path / "config.yaml"
        c1 = CodecConfig(nsym=20, interleaving_depth=5)
        c1.save(path)
        c2 = CodecConfig.load(path)
        assert c2.nsym == 20
        assert c2.interleaving_depth == 5

    @pytest.mark.skipif(not _HAS_TOML, reason="No TOML parser available")
    def test_save_load_toml(self, tmp_path):
        path = tmp_path / "config.toml"
        c1 = CodecConfig(nsym=14, interleaving_depth=2)
        c1.save(path)
        c2 = CodecConfig.load(path)
        assert c2.nsym == 14
        assert c2.interleaving_depth == 2

    def test_load_nonexistent_raises(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            CodecConfig.load(path)

    def test_unsupported_format_raises(self, tmp_path):
        path = tmp_path / "config.txt"
        path.write_text("nsym=10")
        with pytest.raises(ValueError):
            CodecConfig.load(path)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


class TestConfigLogging:
    """Test logging configuration."""

    def test_setup_logging(self):
        c = CodecConfig(log_level="DEBUG")
        c.setup_logging()  # should not raise
        import logging
        assert logging.getLogger().level == logging.DEBUG