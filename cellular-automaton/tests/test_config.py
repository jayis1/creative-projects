"""Tests for the configuration system (JSON/YAML/TOML).

Run with: PYTHONPATH=. python -m pytest tests/test_config.py -v
"""

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from cellular_automaton.config import CAConfig


class TestCAConfig:
    """Tests for CAConfig creation and serialization."""

    def test_default_config(self):
        """Default config should have sensible defaults."""
        cfg = CAConfig()
        assert cfg.rule == "GameOfLife"
        assert cfg.width == 80
        assert cfg.steps == 100
        assert cfg.boundary == "periodic"

    def test_from_dict(self):
        """Config should be created from a dict."""
        cfg = CAConfig.from_dict({
            "rule": "Rule30",
            "width": 60,
            "steps": 40,
            "initial": {"center": True},
            "output": {"format": "ascii"},
        })
        assert cfg.rule == "Rule30"
        assert cfg.width == 60
        assert cfg.steps == 40
        assert cfg.initial["center"] is True

    def test_to_dict_roundtrip(self):
        """Config should survive dict round-trip."""
        cfg = CAConfig(rule="Rule90", width=50, steps=30)
        d = cfg.to_dict()
        cfg2 = CAConfig.from_dict(d)
        assert cfg2.rule == cfg.rule
        assert cfg2.width == cfg.width
        assert cfg2.steps == cfg.steps

    def test_to_json(self):
        """Config should serialize to JSON."""
        cfg = CAConfig(rule="GameOfLife", width=40, height=20)
        text = cfg.to_json()
        data = json.loads(text)
        assert data["rule"] == "GameOfLife"
        assert data["width"] == 40


class TestConfigFiles:
    """Tests for loading/saving config files."""

    def test_load_json(self):
        """Config should load from a JSON file."""
        config_data = {
            "rule": "Rule30",
            "width": 50,
            "boundary": "zero",
            "initial": {"center": True},
            "steps": 20,
            "output": {"format": "ascii"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            path = f.name
        try:
            cfg = CAConfig.from_file(path)
            assert cfg.rule == "Rule30"
            assert cfg.width == 50
            assert cfg.boundary == "zero"
            assert cfg.steps == 20
        finally:
            os.unlink(path)

    def test_save_json(self):
        """Config should save to a JSON file."""
        cfg = CAConfig(rule="GameOfLife", width=30, height=20, steps=10)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            cfg.save(path)
            cfg2 = CAConfig.from_file(path)
            assert cfg2.rule == "GameOfLife"
            assert cfg2.width == 30
            assert cfg2.height == 20
            assert cfg2.steps == 10
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        """Loading a non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CAConfig.from_file("/nonexistent/path/config.json")

    def test_unsupported_format(self):
        """Unsupported format should raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write("<config></config>")
            path = f.name
        try:
            with pytest.raises(ValueError):
                CAConfig.from_file(path)
        finally:
            os.unlink(path)


class TestConfigBuildCA:
    """Tests for building CAs from configs."""

    def test_build_ca_rule30(self):
        """Config should build a Rule30 CA."""
        cfg = CAConfig(rule="Rule30", width=50, boundary="zero",
                       initial={"center": True}, steps=20)
        ca = cfg.build_ca()
        assert ca.rule.name == "Rule30"
        assert ca.width == 50
        assert ca.height == 1
        assert ca.grid[0, 25] == 1  # center seed

    def test_build_ca_game_of_life_random(self):
        """Config should build a GameOfLife CA with random init."""
        cfg = CAConfig(rule="GameOfLife", width=30, height=20,
                       initial={"random": 0.3, "seed": 42}, steps=50)
        ca = cfg.build_ca()
        assert ca.rule.name == "GameOfLife"
        assert ca.width == 30
        assert ca.height == 20
        assert ca.alive_count() > 0  # some cells should be alive

    def test_build_ca_with_pattern(self):
        """Config should build a CA with a placed pattern."""
        cfg = CAConfig(rule="GameOfLife", width=20, height=20,
                       initial={"pattern": "blinker", "x": 8, "y": 9},
                       steps=10)
        ca = cfg.build_ca()
        assert ca.alive_count() == 3  # blinker has 3 cells

    def test_build_ca_multistate(self):
        """Config should build a multi-state CA."""
        cfg = CAConfig(rule="Wireworld", width=20, height=10,
                       initial={"random": 0.3, "seed": 42},
                       multistate={}, steps=20)
        ca = cfg.build_ca()
        assert ca._is_multistate
        assert ca.rule.name == "Wireworld"

    def test_config_run(self):
        """Config.run() should execute the CA and return results."""
        cfg = CAConfig(rule="Rule30", width=30, boundary="zero",
                       initial={"center": True}, steps=10,
                       output={"format": "ascii"})
        ca, result = cfg.run()
        assert ca.step_count == 10
        assert result is not None  # ASCII output
        assert len(result) > 0


class TestConfigLogging:
    """Tests for logging configuration."""

    def test_setup_logging(self):
        """setup_logging should not crash."""
        cfg = CAConfig(logging={"level": "WARNING"})
        cfg.setup_logging()  # should not raise

    def test_setup_logging_with_file(self):
        """setup_logging with a file should create the file."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        try:
            cfg = CAConfig(logging={"level": "DEBUG", "file": log_path})
            cfg.setup_logging()
            # Log something.
            import logging
            logging.getLogger("test").debug("test message")
            assert os.path.exists(log_path)
        finally:
            if os.path.exists(log_path):
                os.unlink(log_path)