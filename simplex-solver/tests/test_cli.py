"""Tests for the CLI interface."""

import json
import os
import tempfile
from fractions import Fraction

import pytest

from simplex.cli import main
from simplex import LPProblem, SimplexSolver, LPStatus


def _run_cli(args: list[str]) -> tuple[int, str]:
    """Run the CLI with the given args, capturing stdout. Returns (exit_code, output)."""
    import io
    import contextlib
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = main(args)
    return code, stdout.getvalue()


def _write_json(spec: dict, suffix=".json") -> str:
    f = tempfile.NamedTemporaryFile(suffix=suffix, mode="w", delete=False)
    json.dump(spec, f)
    f.close()
    return f.name


def _write_text(content: str, suffix=".lp") -> str:
    f = tempfile.NamedTemporaryFile(suffix=suffix, mode="w", delete=False)
    f.write(content)
    f.close()
    return f.name


def test_cli_version():
    """version subcommand should print the version."""
    code, out = _run_cli(["version"])
    assert code == 0
    assert "simplex-solver" in out


def test_cli_solve_json_pretty():
    """solve with --pretty should produce human-readable output."""
    spec = {
        "name": "test", "objective": "max",
        "variables": ["x", "y"],
        "objective_coeffs": {"x": 3, "y": 2},
        "constraints": [
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6, "name": "c1"},
        ],
        "bounds": {}, "integer": [],
    }
    path = _write_json(spec)
    try:
        code, out = _run_cli(["solve", path, "--pretty"])
        assert code == 0
        assert "optimal" in out.lower()
        assert "10" in out  # objective value
    finally:
        os.unlink(path)


def test_cli_solve_json_table():
    """solve with --table should produce boxed output."""
    spec = {
        "name": "test", "objective": "max",
        "variables": ["x", "y"],
        "objective_coeffs": {"x": 3, "y": 2},
        "constraints": [
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
        ],
        "bounds": {}, "integer": [],
    }
    path = _write_json(spec)
    try:
        code, out = _run_cli(["solve", path, "--table"])
        assert code == 0
        assert "┌" in out  # box drawing
        assert "optimal" in out.lower()
    finally:
        os.unlink(path)


def test_cli_solve_json_default_json():
    """solve without --pretty should produce JSON output."""
    spec = {
        "name": "test", "objective": "max",
        "variables": ["x"],
        "objective_coeffs": {"x": 1},
        "constraints": [
            {"coeffs": {"x": 1}, "relation": "<=", "rhs": 5, "name": "c0"},
        ],
        "bounds": {}, "integer": [],
    }
    path = _write_json(spec)
    try:
        code, out = _run_cli(["solve", path])
        assert code == 0
        data = json.loads(out)
        assert data["status"] == "optimal"
        assert data["objective_value"] == pytest.approx(5.0, abs=1e-6)
    finally:
        os.unlink(path)


def test_cli_validate_ok():
    """validate should succeed for a valid problem."""
    spec = {
        "name": "valid", "objective": "max",
        "variables": ["x", "y"],
        "objective_coeffs": {"x": 1, "y": 1},
        "constraints": [
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 5, "name": "c0"},
        ],
        "bounds": {}, "integer": [],
    }
    path = _write_json(spec)
    try:
        code, out = _run_cli(["validate", path])
        assert code == 0
        assert "OK" in out
    finally:
        os.unlink(path)


def test_cli_validate_bad():
    """validate should fail for an invalid problem."""
    spec = {
        "name": "bad", "objective": "max",
        "variables": ["x"],
        "objective_coeffs": {"x": 1},
        "constraints": [
            {"coeffs": {"x": 1, "z": 1}, "relation": "<=", "rhs": 5, "name": "c0"},
        ],
        "bounds": {}, "integer": [],
    }
    path = _write_json(spec)
    try:
        code, out = _run_cli(["validate", path])
        assert code == 1
        assert "INVALID" in out
    finally:
        os.unlink(path)


def test_cli_convert_json_to_lp():
    """convert should produce an LP file from JSON."""
    spec = {
        "name": "test", "objective": "max",
        "variables": ["x", "y"],
        "objective_coeffs": {"x": 3, "y": 2},
        "constraints": [
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
        ],
        "bounds": {}, "integer": [],
    }
    in_path = _write_json(spec)
    out_path = tempfile.mktemp(suffix=".lp")
    try:
        code, out = _run_cli(["convert", in_path, out_path])
        assert code == 0
        with open(out_path) as f:
            content = f.read()
        assert "Maximize" in content
        assert "Subject To" in content
        assert "End" in content
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_cli_convert_lp_to_json():
    """convert should produce JSON from an LP file."""
    lp_content = """\\ Problem: test

Maximize
  obj: 3 x + 2 y

Subject To
  c0: x + y <= 4

End
"""
    in_path = _write_text(lp_content, ".lp")
    out_path = tempfile.mktemp(suffix=".json")
    try:
        code, out = _run_cli(["convert", in_path, out_path])
        assert code == 0
        with open(out_path) as f:
            data = json.load(f)
        assert data["objective"] == "max"
        assert "x" in data["variables"]
        assert "y" in data["variables"]
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_cli_config_init():
    """config --init should write a config file."""
    path = tempfile.mktemp(suffix=".json")
    try:
        code, out = _run_cli(["config", "--init", "--path", path])
        assert code == 0
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "max_iter" in data
        assert "bland" in data
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_cli_config_init_with_set():
    """config --init --set should apply overrides."""
    path = tempfile.mktemp(suffix=".json")
    try:
        code, out = _run_cli([
            "config", "--init", "--path", path,
            "--set", "max_iter=42000", "--set", "bland=false",
        ])
        assert code == 0
        with open(path) as f:
            data = json.load(f)
        assert data["max_iter"] == 42000
        assert data["bland"] is False
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_cli_solve_milp():
    """solve should detect integer variables and use MILP solver."""
    spec = {
        "name": "milp_test", "objective": "max",
        "variables": ["x", "y"],
        "objective_coeffs": {"x": 1, "y": 1},
        "constraints": [
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 3, "name": "c0"},
        ],
        "bounds": {"x": [0, 2], "y": [0, 2]},
        "integer": ["x", "y"],
    }
    path = _write_json(spec)
    try:
        code, out = _run_cli(["solve", path, "--pretty"])
        assert code == 0
        assert "optimal" in out.lower()
        assert "branch-and-bound" in out
    finally:
        os.unlink(path)


def test_cli_solve_with_strategy():
    """solve --strategy should accept depth-first."""
    spec = {
        "name": "milp_test", "objective": "max",
        "variables": ["x", "y"],
        "objective_coeffs": {"x": 1, "y": 1},
        "constraints": [
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 3, "name": "c0"},
        ],
        "bounds": {"x": [0, 2], "y": [0, 2]},
        "integer": ["x", "y"],
    }
    path = _write_json(spec)
    try:
        code, out = _run_cli(["solve", path, "--pretty", "--strategy", "depth-first"])
        assert code == 0
        assert "optimal" in out.lower()
    finally:
        os.unlink(path)