from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from finite_element_solver.cli import EXAMPLE_MODEL
from finite_element_solver.core import TrussModel, TrussSolver, ValidationError


ROOT = Path(__file__).resolve().parents[1]


def solve_example():
    model = TrussModel.from_dict(EXAMPLE_MODEL)
    return TrussSolver(model).solve()


def test_example_solves_with_expected_vertical_displacement():
    result = solve_example()
    dx, dy = result.displacements["C"]
    assert dx == pytest.approx(1.5873015873015874e-06)
    assert dy == pytest.approx(-1.5873015873015874e-06)
    assert result.max_displacement > 0.0


def test_support_reactions_balance_applied_load():
    result = solve_example()
    total_ry = sum(ry for _, ry in result.reactions.values())
    assert total_ry == pytest.approx(1000.0)


def test_invalid_duplicate_node_ids_are_rejected():
    bad = {
        "nodes": [{"id": "A", "x": 0, "y": 0}, {"id": "A", "x": 1, "y": 0}],
        "elements": [{"id": "E1", "start": "A", "end": "A", "E": 1.0, "A": 1.0}],
        "supports": [{"node": "A", "fix": [True, True]}],
    }
    with pytest.raises(ValidationError):
        TrussModel.from_dict(bad).validate()


def test_cli_json_output_round_trips():
    input_path = ROOT / "tests" / "tmp_example.json"
    input_path.write_text(json.dumps(EXAMPLE_MODEL))
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "finite_element_solver", "solve", str(input_path), "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        input_path.unlink(missing_ok=True)
    payload = json.loads(proc.stdout)
    assert payload["max_displacement"] > 0.0
    assert set(payload["displacements"]) == {"A", "B", "C"}


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
