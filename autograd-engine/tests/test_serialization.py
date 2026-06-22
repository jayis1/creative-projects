"""Tests for model serialization."""

import tempfile
import os
import pytest
from autograd_engine import MLP
from autograd_engine.train import train, Adam
from autograd_engine.serialization import save_model, load_model


class TestSerialization:
    def test_save_and_load(self):
        model = MLP(2, [4, 1], activation="tanh")
        xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
        ys = [0, 1, 1, 0]
        train(model, xs, ys, epochs=10, seed=42, classification=True)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_model(model, path)
            loaded = load_model(path)

            # Predictions should match
            for x in xs:
                p1 = model(x)[0].data
                p2 = loaded(x)[0].data
                assert abs(p1 - p2) < 1e-10
        finally:
            os.unlink(path)

    def test_architecture_preserved(self):
        model = MLP(3, [8, 4, 2], activation="relu", dropout=0.1)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_model(model, path)
            loaded = load_model(path)
            assert len(loaded.layers) == 3
            assert len(loaded.layers[0].neurons) == 8
            assert len(loaded.layers[1].neurons) == 4
            assert len(loaded.layers[2].neurons) == 2
        finally:
            os.unlink(path)

    def test_params_count_matches(self):
        model = MLP(2, [8, 8, 1], activation="tanh")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_model(model, path)
            loaded = load_model(path)
            assert model.num_parameters() == loaded.num_parameters()
        finally:
            os.unlink(path)