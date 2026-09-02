from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from finite_element_solver.examples import EXAMPLE_MODELS
from finite_element_solver.io import dump_model, load_model
from finite_element_solver.model import TrussModel, ValidationError
from finite_element_solver.reporting import build_envelope, format_summary, serialize_result, summarize_model
from finite_element_solver.solver import TrussSolver

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


def test_load_combination_combines_case_responses_without_double_counting_base_loads():
    payload = EXAMPLE_MODELS["triangle"] | {
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 1.0, "y": 0.0},
            {"id": "C", "x": 1.0, "y": 1.0, "load": [0.0, -100.0]},
        ]
    }
    model = TrussModel.from_dict(payload)
    solver = TrussSolver(model)
    service = solver.solve("service")
    gravity = solver.solve("gravity")
    combo = solver.solve_combination("service_plus_gravity")
    assert sum(ry for _, ry in combo.reactions.values()) == pytest.approx(
        sum(ry for _, ry in service.reactions.values()) + sum(ry for _, ry in gravity.reactions.values()) - 100.0
    )


def test_summary_reports_expected_counts_and_combinations():
    model = TrussModel.from_dict(EXAMPLE_MODELS["roof"])
    summary = summarize_model(model)
    assert summary["node_count"] == 5
    assert summary["element_count"] == 7
    assert summary["load_combination_count"] == 2
    assert "Load combinations" in format_summary(summary)


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
    assert payload["name"] == "service"
    assert payload["result_kind"] == "load_case"
    assert payload["max_displacement"] > 0.0
    assert payload["elements"][0]["mass"] > 0.0


def test_cli_lists_load_cases_and_combinations():
    input_path = ROOT / "tests" / "tmp_roof.json"
    input_path.write_text(json.dumps(EXAMPLE_MODELS["roof"]))
    try:
        cases = subprocess.run(
            [sys.executable, "-m", "finite_element_solver", "list-load-cases", str(input_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        combinations = subprocess.run(
            [sys.executable, "-m", "finite_element_solver", "list-load-combinations", str(input_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        input_path.unlink(missing_ok=True)
    assert cases.stdout.strip().splitlines() == ["snow", "self-weight", "wind-uplift"]
    assert combinations.stdout.strip().splitlines() == ["ultimate-down", "ultimate-uplift"]


def test_load_model_accepts_toml_and_yaml(tmp_path: Path):
    json_payload = EXAMPLE_MODELS["triangle"]
    yaml_path = tmp_path / "model.yaml"
    yaml_path.write_text(yaml.safe_dump(json_payload, sort_keys=False))
    loaded_yaml = load_model(yaml_path)
    assert loaded_yaml["metadata"]["title"] == "Cantilever triangle"

    toml_path = tmp_path / "model.toml"
    dump_model(toml_path, json_payload)
    loaded_toml = load_model(toml_path)
    assert loaded_toml["metadata"]["title"] == "Cantilever triangle"


def test_unknown_load_case_is_rejected():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    with pytest.raises(ValidationError):
        TrussSolver(model).solve("missing")


def test_unknown_load_combination_is_rejected():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    with pytest.raises(ValidationError):
        TrussSolver(model).solve_combination("missing")


def test_serialized_result_contains_utilization_field():
    model = TrussModel.from_dict(EXAMPLE_MODELS["triangle"])
    payload = serialize_result(TrussSolver(model).solve("service"))
    assert "utilization" in payload["elements"][0]


def test_duplicate_material_ids_are_rejected():
    bad = {
        "materials": [
            {"id": "steel", "E": 200000000000.0},
            {"id": "steel", "E": 210000000000.0},
        ],
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 1.0, "y": 0.0},
            {"id": "C", "x": 1.0, "y": 1.0},
        ],
        "elements": [
            {"id": "AB", "start": "A", "end": "B", "material": "steel", "A": 0.003},
            {"id": "BC", "start": "B", "end": "C", "material": "steel", "A": 0.003},
            {"id": "AC", "start": "A", "end": "C", "material": "steel", "A": 0.003},
        ],
        "supports": [{"node": "A", "fix": [True, True]}, {"node": "B", "fix": [False, True]}],
    }
    with pytest.raises(ValidationError):
        TrussModel.from_dict(bad)


def test_duplicate_section_ids_are_rejected():
    bad = {
        "sections": [
            {"id": "rod", "A": 0.003},
            {"id": "rod", "A": 0.004},
        ],
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 1.0, "y": 0.0},
            {"id": "C", "x": 1.0, "y": 1.0},
        ],
        "elements": [
            {"id": "AB", "start": "A", "end": "B", "E": 210000000000.0, "section": "rod"},
            {"id": "BC", "start": "B", "end": "C", "E": 210000000000.0, "section": "rod"},
            {"id": "AC", "start": "A", "end": "C", "E": 210000000000.0, "section": "rod"},
        ],
        "supports": [{"node": "A", "fix": [True, True]}, {"node": "B", "fix": [False, True]}],
    }
    with pytest.raises(ValidationError):
        TrussModel.from_dict(bad)


def test_duplicate_node_load_entries_are_combined():
    model_data = {
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 1.0, "y": 0.0},
            {"id": "C", "x": 1.0, "y": 1.0},
        ],
        "elements": [
            {"id": "AB", "start": "A", "end": "B", "E": 210000000000.0, "A": 0.003},
            {"id": "BC", "start": "B", "end": "C", "E": 210000000000.0, "A": 0.003},
            {"id": "AC", "start": "A", "end": "C", "E": 210000000000.0, "A": 0.003},
        ],
        "supports": [{"node": "A", "fix": [True, True]}, {"node": "B", "fix": [False, True]}],
        "load_cases": [
            {
                "name": "combo",
                "node_loads": [
                    {"node": "C", "load": [100.0, -1000.0]},
                    {"node": "C", "load": [50.0, -200.0]},
                ],
            }
        ],
    }
    model = TrussModel.from_dict(model_data)
    result = TrussSolver(model).solve("combo")
    assert sum(rx for rx, _ in result.reactions.values()) == pytest.approx(-150.0)
    assert sum(ry for _, ry in result.reactions.values()) == pytest.approx(1200.0)


def test_write_example_supports_toml_and_yaml_output(tmp_path: Path):
    toml_path = tmp_path / "example.toml"
    yaml_path = tmp_path / "example.yaml"
    toml_proc = subprocess.run(
        [sys.executable, "-m", "finite_element_solver", "write-example", str(toml_path), "--preset", "triangle"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    yaml_proc = subprocess.run(
        [sys.executable, "-m", "finite_element_solver", "write-example", str(yaml_path), "--preset", "roof"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "wrote triangle example model" in toml_proc.stdout
    assert load_model(toml_path)["metadata"]["title"] == "Cantilever triangle"
    assert "wrote roof example model" in yaml_proc.stdout
    assert load_model(yaml_path)["metadata"]["title"] == "Roof truss"


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


def test_build_envelope_reports_governing_sources():
    model = TrussModel.from_dict(EXAMPLE_MODELS["roof"])
    solver = TrussSolver(model)
    envelope = build_envelope(solver.solve_all_cases() + solver.solve_all_combinations())
    assert envelope["result_count"] == 5
    assert envelope["global_max_displacement"]["source"] in {"snow", "self-weight", "wind-uplift", "ultimate-down", "ultimate-uplift"}
    assert envelope["elements"]["DE"]["max_abs_stress"]["source"] is not None


def test_cli_envelope_and_validate_commands(tmp_path: Path):
    input_path = tmp_path / "roof.yaml"
    input_path.write_text(yaml.safe_dump(EXAMPLE_MODELS["roof"], sort_keys=False))
    validate = subprocess.run(
        [sys.executable, "-m", "finite_element_solver", "validate", str(input_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    envelope = subprocess.run(
        [sys.executable, "-m", "finite_element_solver", "envelope", str(input_path), "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(envelope.stdout)
    assert "model valid" in validate.stdout
    assert payload["result_count"] == 5
    assert payload["global_max_displacement"]["node"] in {"A", "B", "C", "D", "E"}


def test_cli_can_write_log_file(tmp_path: Path):
    input_path = tmp_path / "triangle.json"
    log_path = tmp_path / "run.log"
    input_path.write_text(json.dumps(EXAMPLE_MODELS["triangle"]))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "finite_element_solver",
            "--log-level",
            "INFO",
            "--log-file",
            str(log_path),
            "summary",
            str(input_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Loading model" in log_path.read_text()
