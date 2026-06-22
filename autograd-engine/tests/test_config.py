"""Tests for the config module."""

import json
import tempfile
import os
import pytest
from autograd_engine.config import Config, ModelConfig, OptimizerConfig, default_config
from autograd_engine.nn import MLP
from autograd_engine.train import SGD, Adam


class TestModelConfig:
    def test_build(self):
        cfg = ModelConfig(nin=2, nouts=[4, 1], activation="tanh")
        model = cfg.build()
        assert isinstance(model, MLP)
        assert model.num_parameters() > 0


class TestOptimizerConfig:
    def test_build_sgd(self):
        cfg = OptimizerConfig(type="sgd", lr=0.1)
        model = MLP(2, [4, 1])
        opt = cfg.build(model.parameters())
        assert isinstance(opt, SGD)

    def test_build_adam(self):
        cfg = OptimizerConfig(type="adam", lr=0.01)
        model = MLP(2, [4, 1])
        opt = cfg.build(model.parameters())
        assert isinstance(opt, Adam)

    def test_unknown_type(self):
        cfg = OptimizerConfig(type="bogus")
        model = MLP(2, [4, 1])
        with pytest.raises(ValueError, match="Unknown optimizer"):
            cfg.build(model.parameters())


class TestConfig:
    def test_from_dict(self):
        data = {
            "model": {"nin": 2, "nouts": [4, 1], "activation": "relu"},
            "optimizer": {"type": "adam", "lr": 0.01},
            "training": {"epochs": 100, "seed": 123},
        }
        cfg = Config.from_dict(data)
        assert cfg.model.nin == 2
        assert cfg.model.nouts == [4, 1]
        assert cfg.optimizer.type == "adam"
        assert cfg.training.epochs == 100

    def test_load_json(self):
        data = {
            "model": {"nin": 2, "nouts": [4, 1]},
            "optimizer": {"type": "sgd", "lr": 0.1},
            "training": {"epochs": 50},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = Config.load(path)
            assert cfg.model.nin == 2
            assert cfg.training.epochs == 50
        finally:
            os.unlink(path)

    def test_save_and_load(self):
        cfg = default_config()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            cfg.save(path)
            loaded = Config.load(path)
            assert loaded.model.nin == cfg.model.nin
            assert loaded.model.nouts == cfg.model.nouts
        finally:
            os.unlink(path)

    def test_default_config(self):
        cfg = default_config()
        assert cfg.model.nin == 2
        assert cfg.optimizer.type == "adam"
        assert cfg.training.classification is True