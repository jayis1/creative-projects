"""Tests for configuration management."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from delaunay_voronoi.config import (
    Config, RenderConfig, AlgorithmConfig,
    load_config, save_config, default_config,
)


class TestConfig:
    def test_default(self):
        c = default_config()
        assert c.render.width == 800
        assert c.algorithm.num_points == 30
        assert c.log_level == "INFO"

    def test_from_dict(self):
        data = {
            "render": {"width": 1024, "height": 768, "background": "#000000"},
            "algorithm": {"num_points": 50, "seed": 99},
            "output_dir": "/tmp/out",
            "log_level": "DEBUG",
        }
        c = Config.from_dict(data)
        assert c.render.width == 1024
        assert c.render.height == 768
        assert c.render.background == "#000000"
        assert c.algorithm.num_points == 50
        assert c.algorithm.seed == 99
        assert c.output_dir == "/tmp/out"
        assert c.log_level == "DEBUG"

    def test_from_dict_partial(self):
        c = Config.from_dict({"render": {"width": 500}})
        assert c.render.width == 500
        # Other fields keep defaults
        assert c.render.height == 600
        assert c.algorithm.num_points == 30

    def test_from_dict_ignores_unknown_keys(self):
        c = Config.from_dict({"render": {"unknown_key": 42, "width": 100}})
        assert c.render.width == 100

    def test_to_dict(self):
        c = Config()
        d = c.to_dict()
        assert "render" in d
        assert "algorithm" in d
        assert d["render"]["width"] == 800


class TestConfigIO:
    def test_json_roundtrip(self, tmp_path):
        c = Config()
        c.render.width = 1024
        c.algorithm.num_points = 50
        path = str(tmp_path / "config.json")
        save_config(c, path)
        c2 = load_config(path)
        assert c2.render.width == 1024
        assert c2.algorithm.num_points == 50

    def test_toml_roundtrip(self, tmp_path):
        c = Config()
        c.render.width = 640
        c.algorithm.seed = 123
        path = str(tmp_path / "config.toml")
        save_config(c, path)
        c2 = load_config(path)
        assert c2.render.width == 640
        assert c2.algorithm.seed == 123

    def test_unsupported_format(self, tmp_path):
        path = str(tmp_path / "config.txt")
        with pytest.raises(ValueError):
            save_config(Config(), path)
        with pytest.raises(ValueError):
            load_config(path)

    def test_yaml_minimal(self, tmp_path):
        """Test the minimal YAML parser (no pyyaml required)."""
        path = str(tmp_path / "config.yaml")
        with open(path, "w") as f:
            f.write("output_dir: /tmp/test\n")
            f.write("log_level: DEBUG\n")
            f.write("render:\n")
            f.write("  width: 1200\n")
            f.write("  height: 800\n")
            f.write("algorithm:\n")
            f.write("  num_points: 75\n")
            f.write("  seed: 7\n")
        c = load_config(path)
        assert c.output_dir == "/tmp/test"
        assert c.log_level == "DEBUG"
        assert c.render.width == 1200
        assert c.render.height == 800
        assert c.algorithm.num_points == 75
        assert c.algorithm.seed == 7