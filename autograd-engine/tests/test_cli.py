"""Tests for the CLI module."""

import subprocess
import sys
import os
import tempfile
import json

import pytest


def run_cli(*args, cwd=None):
    """Run the CLI as a subprocess and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "autograd_engine.cli"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=60)
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def project_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCLIInfo:
    def test_info_command(self, project_dir):
        rc, out, err = run_cli("info", cwd=project_dir)
        assert rc == 0
        assert "autograd-engine" in out
        assert "Available operations" in out

    def test_no_command_shows_help(self, project_dir):
        rc, out, err = run_cli(cwd=project_dir)
        assert rc == 1
        assert "usage" in out.lower() or "help" in out.lower()


class TestCLIDemo:
    def test_demo_command(self, project_dir):
        rc, out, err = run_cli("demo", cwd=project_dir)
        assert rc == 0
        assert "XOR" in out
        assert "loss" in out.lower() or "Loss" in out


class TestCLIGradCheck:
    def test_grad_check_command(self, project_dir):
        rc, out, err = run_cli("grad-check", cwd=project_dir)
        assert rc == 0
        assert "PASS" in out


class TestCLITrain:
    def test_train_xor(self, project_dir):
        rc, out, err = run_cli(
            "train", "--xor", "--epochs", "50", "--optimizer", "adam",
            "--lr", "0.01", "--activation", "tanh",
            cwd=project_dir
        )
        assert rc == 0
        assert "Final loss" in out
        assert "Predictions" in out

    def test_train_with_config(self, project_dir):
        config = {
            "model": {"nin": 2, "nouts": [4, 1], "activation": "tanh"},
            "optimizer": {"type": "adam", "lr": 0.01},
            "training": {"epochs": 30, "seed": 42, "classification": True},
            "logging": {"level": "INFO", "verbose": False}
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name
        try:
            rc, out, err = run_cli("train", "--config", path, cwd=project_dir)
            assert rc == 0
            assert "Final loss" in out
        finally:
            os.unlink(path)

    def test_train_with_plot(self, project_dir):
        rc, out, err = run_cli(
            "train", "--xor", "--epochs", "20", "--plot",
            cwd=project_dir
        )
        assert rc == 0
        assert "●" in out  # ASCII chart marker