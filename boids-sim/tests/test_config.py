"""Tests for config, presets, and config file I/O."""

import os
import tempfile
import pytest
from boids.config import (
    SimulationConfig, get_preset, list_presets, save_config, load_config, PRESETS
)


class TestSimulationConfig:
    def test_defaults(self):
        cfg = SimulationConfig()
        assert cfg.num_boids == 150
        assert cfg.width == 800
        assert cfg.height == 600
        assert cfg.max_speed == 4.0
        assert cfg.spatial_index == "grid"
        assert cfg.num_species == 1

    def test_custom(self):
        cfg = SimulationConfig(num_boids=42, w_sep=3.0, use_wrap=True)
        assert cfg.num_boids == 42
        assert cfg.w_sep == 3.0
        assert cfg.use_wrap == True

    def test_to_dict(self):
        cfg = SimulationConfig(num_boids=10)
        d = cfg.to_dict()
        assert d["num_boids"] == 10
        assert "width" in d
        assert "w_sep" in d

    def test_from_dict(self):
        d = {"num_boids": 50, "w_sep": 2.0, "unknown_key": "ignored"}
        cfg = SimulationConfig.from_dict(d)
        assert cfg.num_boids == 50
        assert cfg.w_sep == 2.0

    def test_from_dict_ignores_unknown(self):
        d = {"num_boids": 50, "bogus_key": 999}
        cfg = SimulationConfig.from_dict(d)
        assert cfg.num_boids == 50
        assert not hasattr(cfg, "bogus_key")


class TestPresets:
    def test_list_presets(self):
        presets = list_presets()
        assert "default" in presets
        assert "tight-flock" in presets
        assert "fast-murmuration" in presets

    def test_get_preset(self):
        cfg = get_preset("tight-flock")
        assert cfg.num_boids == 200
        assert cfg.w_sep == 2.0

    def test_get_unknown_preset(self):
        with pytest.raises(ValueError):
            get_preset("nonexistent")

    def test_new_presets_exist(self):
        presets = list_presets()
        assert "multi-species" in presets
        assert "path-followers" in presets
        assert "quadtree-demo" in presets

    def test_multi_species_preset(self):
        cfg = get_preset("multi-species")
        assert cfg.num_species == 3

    def test_quadtree_preset(self):
        cfg = get_preset("quadtree-demo")
        assert cfg.spatial_index == "quadtree"

    def test_path_followers_preset(self):
        cfg = get_preset("path-followers")
        assert cfg.w_path == 2.0
        assert cfg.path_loop == True


class TestConfigFiles:
    def test_json_round_trip(self):
        cfg = SimulationConfig(num_boids=42, w_sep=2.5)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_config(cfg, path)
            cfg2 = load_config(path)
            assert cfg2.num_boids == 42
            assert cfg2.w_sep == 2.5
        finally:
            os.unlink(path)

    def test_yaml_round_trip(self):
        cfg = SimulationConfig(num_boids=42, w_sep=2.5, use_wrap=True)
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            save_config(cfg, path)
            cfg2 = load_config(path)
            assert cfg2.num_boids == 42
            assert cfg2.w_sep == 2.5
            assert cfg2.use_wrap == True
        finally:
            os.unlink(path)

    def test_toml_round_trip(self):
        cfg = SimulationConfig(num_boids=42, w_sep=2.5, use_wrap=True)
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            path = f.name
        try:
            save_config(cfg, path)
            cfg2 = load_config(path)
            assert cfg2.num_boids == 42
            assert cfg2.w_sep == 2.5
            assert cfg2.use_wrap == True
        finally:
            os.unlink(path)

    def test_unsupported_format(self):
        cfg = SimulationConfig()
        with pytest.raises(ValueError):
            save_config(cfg, "config.txt")
        # Create a real file with unsupported extension to test load
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not a config")
            path = f.name
        try:
            with pytest.raises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.json")

    def test_config_save_load_methods(self):
        cfg = SimulationConfig(num_boids=99)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            cfg.save(path)
            cfg2 = SimulationConfig.load(path)
            assert cfg2.num_boids == 99
        finally:
            os.unlink(path)