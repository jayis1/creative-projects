"""Tests for the CHIP-8 config module."""

import json
import tempfile
from pathlib import Path

import pytest
from chip8_emulator.config import (
    EmulatorConfig, DisplayConfig, KeypadConfig, CpuConfig,
    LoggingConfig, load_config, parse_config, generate_default_config,
)


class TestDefaultConfig:
    """Test default configuration values."""

    def test_default_config(self):
        config = EmulatorConfig()
        assert config.display.width == 64
        assert config.display.height == 32
        assert config.cpu.super_chip is False
        assert config.cpu.speed == 700
        assert config.cpu.max_cycles == 0
        assert config.logging.level == "WARNING"

    def test_display_config_custom(self):
        dc = DisplayConfig(width=128, height=64, on_char="#", off_char=".")
        assert dc.width == 128
        assert dc.height == 64
        assert dc.on_char == "#"
        assert dc.off_char == "."

    def test_keypad_config_default(self):
        kc = KeypadConfig()
        assert kc.mapping["1"] == 0x1
        assert kc.mapping["v"] == 0xF

    def test_cpu_config_custom(self):
        cc = CpuConfig(super_chip=True, speed=1000)
        assert cc.super_chip is True
        assert cc.speed == 1000


class TestParseConfig:
    """Test config parsing from dicts."""

    def test_parse_full_config(self):
        data = {
            "display": {"width": 128, "height": 64, "on_char": "#", "off_char": "."},
            "keypad": {"mapping": {"a": 0x7, "b": 0x8}},
            "cpu": {"super_chip": True, "speed": 1000, "max_cycles": 5000},
            "logging": {"level": "DEBUG", "file": "/tmp/chip8.log"},
        }
        config = parse_config(data)
        assert config.display.width == 128
        assert config.display.height == 64
        assert config.display.on_char == "#"
        assert config.display.off_char == "."
        assert config.keypad.mapping["a"] == 7
        assert config.keypad.mapping["b"] == 8
        assert config.cpu.super_chip is True
        assert config.cpu.speed == 1000
        assert config.cpu.max_cycles == 5000
        assert config.logging.level == "DEBUG"
        assert config.logging.file == "/tmp/chip8.log"

    def test_parse_partial_config(self):
        data = {"cpu": {"super_chip": True}}
        config = parse_config(data)
        assert config.cpu.super_chip is True
        # Defaults for everything else
        assert config.display.width == 64
        assert config.cpu.speed == 700

    def test_parse_empty_config(self):
        config = parse_config({})
        assert config.display.width == 64
        assert config.cpu.speed == 700

    def test_parse_config_keypad_string_values(self):
        data = {"keypad": {"mapping": {"a": "0x7", "b": "8"}}}
        config = parse_config(data)
        assert config.keypad.mapping["a"] == 7
        assert config.keypad.mapping["b"] == 8


class TestLoadConfig:
    """Test loading config from files."""

    def test_load_json_config(self):
        config_data = {
            "display": {"width": 128, "height": 64},
            "cpu": {"super_chip": True},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            path = f.name
        try:
            config = load_config(path)
            assert config.display.width == 128
            assert config.display.height == 64
            assert config.cpu.super_chip is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.json")

    def test_load_unsupported_format(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write("test")
            path = f.name
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                load_config(path)
        finally:
            Path(path).unlink(missing_ok=True)


class TestGenerateDefaultConfig:
    """Test default config generation."""

    def test_generate_json(self):
        result = generate_default_config("json")
        parsed = json.loads(result)
        assert parsed["display"]["width"] == 64
        assert parsed["cpu"]["speed"] == 700

    def test_generate_yaml(self):
        result = generate_default_config("yaml")
        assert "display:" in result
        assert "keypad:" in result
        assert "cpu:" in result

    def test_generate_toml(self):
        result = generate_default_config("toml")
        assert "[display]" in result
        assert "[cpu]" in result


class TestApplyLogging:
    """Test logging configuration."""

    def test_apply_logging_default(self):
        config = EmulatorConfig()
        config.logging.level = "WARNING"
        # Should not raise
        config.apply_logging()