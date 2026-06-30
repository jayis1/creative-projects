"""Tests for visualisation, training, and config modules."""

import os
import sys
import math
import tempfile
import random

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hmm import HMM, forward, viterbi, baum_welch, generate_sequence
from hmm.viz import (
    transition_diagram, viterbi_path_visualization,
    posterior_heatmap, entropy_sparkline, format_model,
)
from hmm.training import (
    k_fold_cross_validation, summarize_cv_results,
    train_with_restarts, constrained_baum_welch, grid_search,
)
from hmm.config import load_config, save_config


def _casino():
    return HMM(
        states=["F", "L"],
        symbols=["1", "2", "3", "4", "5", "6"],
        A=[[0.95, 0.05], [0.10, 0.90]],
        B=[[1/6]*6, [0.10, 0.10, 0.10, 0.10, 0.10, 0.50]],
        pi=[0.5, 0.5],
    )


# -- Visualisation --

class TestVisualisation:
    def test_transition_diagram(self):
        hmm = _casino()
        result = transition_diagram(hmm)
        assert "State Transition Diagram" in result
        assert "F" in result and "L" in result

    def test_viterbi_path_visualization(self):
        hmm = _casino()
        obs = ["1", "2", "3", "6", "6"]
        result = viterbi_path_visualization(hmm, obs)
        assert "Viterbi Path" in result
        assert "Obs:" in result

    def test_viterbi_path_impossible(self):
        hmm = HMM(["A"], ["x", "y"], [[1.0]], [[1.0, 0.0]], [1.0])
        result = viterbi_path_visualization(hmm, ["y"])
        assert "Impossible" in result

    def test_posterior_heatmap(self):
        hmm = _casino()
        obs = ["1", "2", "3"]
        result = posterior_heatmap(hmm, obs)
        assert "Heatmap" in result
        assert "Scale:" in result

    def test_entropy_sparkline(self):
        hmm = _casino()
        obs = ["1", "2", "3", "4"]
        result = entropy_sparkline(hmm, obs)
        assert "Entropy" in result
        assert "nats" in result

    def test_format_model(self):
        hmm = _casino()
        result = format_model(hmm)
        assert "HMM:" in result
        assert "Transition" in result
        assert "Emission" in result
        assert "Initial" in result


# -- Training --

class TestCrossValidation:
    def test_cv_returns_results(self):
        hmm_true = _casino()
        rng = random.Random(42)
        obs_list = []
        for _ in range(10):
            _, syms = generate_sequence(hmm_true, length=30, rng=rng)
            obs_list.append(hmm_true.observation_sequence(syms))
        results = k_fold_cross_validation(
            [], ["1", "2", "3", "4", "5", "6"], obs_list,
            n_states_options=[2, 3], k=5, iterations=10, seed=42,
        )
        assert len(results) > 0
        assert all("n_states" in r for r in results)
        assert all("val_ll" in r for r in results)

    def test_summarize_cv(self):
        results = [
            {"n_states": 2, "fold": 0, "train_ll": -10, "val_ll": -12},
            {"n_states": 2, "fold": 1, "train_ll": -11, "val_ll": -13},
            {"n_states": 3, "fold": 0, "train_ll": -8, "val_ll": -15},
            {"n_states": 3, "fold": 1, "train_ll": -9, "val_ll": -16},
        ]
        summary = summarize_cv_results(results)
        assert 2 in summary and 3 in summary
        assert abs(summary[2]["mean_val_ll"] - (-12.5)) < 1e-9
        assert abs(summary[3]["mean_val_ll"] - (-15.5)) < 1e-9


class TestRestarts:
    def test_restarts_returns_best(self):
        hmm_true = _casino()
        _, syms = generate_sequence(hmm_true, length=100, seed=42)
        obs = hmm_true.observation_sequence(syms)
        best_hmm, best_ll, best_idx = train_with_restarts(
            ["F", "L"], ["1", "2", "3", "4", "5", "6"], obs,
            n_restarts=3, iterations=20, seed=0,
        )
        assert best_idx >= 0
        assert best_ll != -math.inf
        assert best_hmm.n_states == 2


class TestConstrainedBaumWelch:
    def test_locked_transition_stays_fixed(self):
        hmm = _casino()
        original_A01 = hmm.A[0][1]
        obs = [0, 1, 2, 3, 4, 5] * 3
        constrained_baum_welch(
            hmm, obs,
            locked_transitions=[(0, 1)],
            iterations=10,
        )
        # A[0][1] should still be close to original (it was locked)
        assert abs(hmm.A[0][1] - original_A01) < 1e-6

    def test_locked_pi_stays_fixed(self):
        hmm = HMM(["a", "b"], ["x", "y"],
                  [[0.6, 0.4], [0.3, 0.7]],
                  [[0.5, 0.5], [0.8, 0.2]],
                  [0.7, 0.3])
        original_pi0 = hmm.pi[0]
        obs = [0, 1, 0, 1, 0, 1]
        constrained_baum_welch(hmm, obs, locked_pi=[0], iterations=10)
        assert abs(hmm.pi[0] - original_pi0) < 1e-6

    def test_no_locks_same_as_baum_welch(self):
        hmm1 = HMM.random(["a", "b"], ["x", "y"], seed=42)
        hmm2 = HMM.random(["a", "b"], ["x", "y"], seed=42)
        obs = [0, 1, 0, 1, 0, 1, 0, 1]
        constrained_baum_welch(hmm1, obs, iterations=20)
        baum_welch(hmm2, obs, iterations=20)
        # Without locks, constrained should behave like regular BW
        for i in range(2):
            for j in range(2):
                assert abs(hmm1.A[i][j] - hmm2.A[i][j]) < 1e-6


class TestGridSearch:
    def test_grid_returns_results(self):
        hmm_true = _casino()
        _, syms = generate_sequence(hmm_true, length=50, seed=42)
        obs = hmm_true.observation_sequence(syms)
        results = grid_search(
            ["F", "L"], ["1", "2", "3", "4", "5", "6"], obs,
            n_restarts=2, iterations=10, seed=0,
        )
        assert len(results) > 0
        assert all("best_ll" in r for r in results)
        assert all("smooth" in r for r in results)


# -- Config --

class TestConfig:
    def test_json_config(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write('{"iterations": 100, "tol": 0.001, "verbose": true}')
            path = f.name
        config = load_config(path)
        assert config["iterations"] == 100
        assert config["tol"] == 0.001
        assert config["verbose"] is True
        os.unlink(path)

    def test_save_and_load_json(self):
        config = {"iterations": 50, "seed": 42}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            path = f.name
        save_config(config, path)
        loaded = load_config(path)
        assert loaded == config
        os.unlink(path)

    def test_simple_yaml_parse(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("iterations: 50\ntol: 0.001\nverbose: true\nname: test\n")
            path = f.name
        config = load_config(path)
        assert config["iterations"] == 50
        assert config["tol"] == 0.001
        assert config["verbose"] is True
        assert config["name"] == "test"
        os.unlink(path)


# -- CLI smoke tests --

class TestCLI:
    def test_cli_random_and_info(self):
        from hmm.cli import main
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.json")
            ret = main(["random", "--states", "Sunny,Rainy",
                        "--symbols", "Walk,Shop", "--out", model_path, "--seed", "1"])
            assert ret == 0
            assert os.path.exists(model_path)
            ret = main(["info", "--model", model_path])
            assert ret == 0

    def test_cli_generate(self):
        from hmm.cli import main
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.json")
            main(["random", "--states", "A,B", "--symbols", "x,y",
                  "--out", model_path, "--seed", "1"])
            ret = main(["generate", "--model", model_path, "--length", "10", "--seed", "1"])
            assert ret == 0

    def test_cli_uniform(self):
        from hmm.cli import main
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "uniform.json")
            ret = main(["uniform", "--states", "A,B,C", "--symbols", "x,y",
                        "--out", model_path])
            assert ret == 0
            assert os.path.exists(model_path)

    def test_cli_visualize(self):
        from hmm.cli import main
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.json")
            main(["random", "--states", "A,B", "--symbols", "x,y",
                  "--out", model_path, "--seed", "1"])
            ret = main(["visualize", "--model", model_path, "--type", "transition"])
            assert ret == 0
            ret = main(["visualize", "--model", model_path, "--type", "model"])
            assert ret == 0

    def test_cli_dwell(self):
        from hmm.cli import main
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "model.json")
            main(["random", "--states", "A,B", "--symbols", "x,y",
                  "--out", model_path, "--seed", "1"])
            ret = main(["dwell", "--model", model_path])
            assert ret == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])