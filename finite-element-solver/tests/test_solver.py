from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from finite_element_solver.cli import EXAMPLE_MODELS, format_summary, load_model, serialize_result
from finite_element_solver.core import TrussModel, TrussSolver, ValidationError, summarize_model


ROOT = Path(__file__).resolve().parents[1]


def test_example_service_case_solves_with_expected_vertical_displacement():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    result = TrussSolver(model).solve("service")
    dx, dy = result.displacements["C"]
    assert dx == pytest.approx(1.5873015873015874e-06)
    assert dy == pytest.approx(-1.5873015873015874e-06)
    assert result.max_displacement > 0.0


def test_support_reactions_balance_applied_load_for_service_case():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    result = TrussSolver(model).solve("service")
    total_ry = sum(ry for _, ry in result.reactions.values())
    assert total_ry == pytest.approx(1000.0)


def test_self_weight_case_accumulates_mass_and_loads():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    result = TrussSolver(model).solve("gravity")
    assert result.total_mass == pytest.approx((1.0 + 1.0 + 2**0.5) * 0.003 * 7850.0)
    assert sum(ry for _, ry in result.reactions.values()) > 0.0


def test_summary_reports_expected_counts():
    model = TrussModel.from_dict(EXAMPLE_MODELS["roof"])
    summary = summarize_model(model)
    assert summary["node_count"] == 5
    assert summary["element_count"] == 7
    assert "Bounding box" in format_summary(summary)


def test_invalid_duplicate_node_ids_are_rejected():
    bad = {
        "nodes": [{"id": "A", "x": 0, "y": 0}, {"id": "A", "x": 1, "y": 0}],
        "elements": [{"id": "E1", "start": "A", "end": "B", "E": 1.0, "A": 1.0}],
        "supports": [{"node": "A", "fix": [True, True]}, {"node": "B", "fix": [True, False]}],
    }
    with pytest.raises(ValidationError):
        TrussModel.from_dict(bad)


def test_cli_json_output_round_trips():
    input_path = ROOT / "tests" / "tmp_example.json"
    input_path.write_text(json.dumps(EXAMPLE_MODELS["triangle"]))
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "finite_element_solver", "solve", str(input_path), "--case", "service", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        input_path.unlink(missing_ok=True)
    payload = json.loads(proc.stdout)
    assert payload["case_name"] == "service"
    assert payload["max_displacement"] > 0.0
    assert payload["elements"][0]["mass"] > 0.0


def test_cli_lists_load_cases():
    input_path = ROOT / "tests" / "tmp_roof.json"
    input_path.write_text(json.dumps(EXAMPLE_MODELS["roof"]))
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "finite_element_solver", "list-load-cases", str(input_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        input_path.unlink(missing_ok=True)
    assert proc.stdout.strip().splitlines() == ["snow", "self-weight"]


def test_load_model_accepts_toml():
    toml_path = ROOT / "tests" / "tmp_model.toml"
    toml_path.write_text(
        """
[metadata]
title = "Tiny truss"

[[nodes]]
id = "A"
x = 0.0
y = 0.0

[[nodes]]
id = "B"
x = 1.0
y = 0.0

[[nodes]]
id = "C"
x = 1.0
y = 1.0

[[elements]]
id = "AB"
start = "A"
end = "B"
E = 210000000000.0
A = 0.003

[[elements]]
id = "BC"
start = "B"
end = "C"
E = 210000000000.0
A = 0.003

[[elements]]
id = "AC"
start = "A"
end = "C"
E = 210000000000.0
A = 0.003

[[supports]]
node = "A"
fix = [true, true]

[[supports]]
node = "B"
fix = [false, true]

[[load_cases]]
name = "service"

[[load_cases.node_loads]]
node = "C"
load = [0.0, -1000.0]
        """.strip()
    )
    try:
        model = TrussModel.from_dict(load_model(toml_path))
    finally:
        toml_path.unlink(missing_ok=True)
    assert TrussSolver(model).solve("service").max_displacement > 0.0


def test_unknown_load_case_is_rejected():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    with pytest.raises(ValidationError):
        TrussSolver(model).solve("missing")


def test_serialized_result_contains_utilization_field():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    payload = serialize_result(TrussSolver(model).solve("service"))
    assert "utilization" in payload["elements"][0]


def test_singular_structure_raises_validation_error():
    unstable = {
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 0.0, "y": 1.0},
        ],
        "elements": [{"id": "AB", "start": "A", "end": "B", "E": 1.0, "A": 1.0}],
        "supports": [{"node": "A", "fix": [True, True]}, {"node": "B", "fix": [False, True]}],
    }
    with pytest.raises(ValidationError):
        TrussSolver(TrussModel.from_dict(unstable)).solve()
