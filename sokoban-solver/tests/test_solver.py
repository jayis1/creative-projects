from __future__ import annotations

import json

from sokoban_solver import (
    Board,
    SokobanSolver,
    assignment_lower_bound,
    get_level,
    list_levels,
    load_config,
    parse_level,
    parse_level_pack,
    solve_level_pack,
)
from sokoban_solver.cli import main

SIMPLE = """
#####
#@$.#
#####
"""

UNSOLVABLE = """
######
#@ $ #
#  . #
######
"""

PACK = """
; simple-one
#####
#@$.#
#####

; simple-two
#####
#@$.#
#####
"""


def test_parse_and_render_round_trip():
    board = parse_level(SIMPLE, title="simple")
    rendered = board.render()
    assert "@$." in rendered
    assert board.title == "simple"


def test_solver_solves_simple_level():
    board = parse_level(SIMPLE)
    result = SokobanSolver(board).solve()
    assert result.solved is True
    assert result.move_sequence == "R"
    assert result.push_sequence == "R"
    assert result.pushes == 1


def test_unsolvable_corner_level_reports_failure():
    board = parse_level(UNSOLVABLE)
    result = SokobanSolver(board).solve(max_states=2000)
    assert result.solved is False
    assert result.reason in {"no solution found", "search limit reached (2000)"}


def test_analyze_reports_dead_square_information():
    board = parse_level(UNSOLVABLE)
    analysis = SokobanSolver(board).analyze()
    assert analysis["boxes"] == 1
    assert isinstance(analysis["corner_deadlocks"], list)
    assert isinstance(analysis["dead_squares"], list)
    heuristic = analysis["heuristic_lower_bound"]
    assert isinstance(heuristic, int)
    assert heuristic >= 0


def test_builtin_levels_are_available_and_solvable():
    assert "tiny-one" in list_levels()
    board = parse_level(get_level("tiny-one"), title="tiny-one")
    result = SokobanSolver(board).solve()
    assert result.solved is True


def test_replay_contains_initial_and_final_frames():
    board = parse_level(SIMPLE)
    solver = SokobanSolver(board)
    result = solver.solve()
    frames = solver.replay(result)
    assert frames[0].startswith("#####")
    assert "*" in frames[-1]


def test_ragged_level_does_not_create_phantom_floor_tiles():
    board = parse_level("#####\n#@$.#\n###")
    assert (2, 3) not in board.floor
    assert (2, 4) not in board.floor


def test_render_preserves_rectangular_width():
    board = Board(
        width=4,
        height=2,
        walls=frozenset({(0, 0)}),
        goals=frozenset({(1, 3)}),
        boxes=frozenset(),
        player=(1, 1),
        floor=frozenset({(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3)}),
    )
    lines = board.render().splitlines()
    assert all(len(line) == board.width for line in lines)


def test_assignment_lower_bound_matches_expected_distance():
    boxes = ((1, 1), (2, 2))
    goals = ((1, 3), (2, 4))
    assert assignment_lower_bound(boxes, goals) == 4


def test_parse_level_pack_and_solve_many():
    entries = parse_level_pack(PACK)
    assert [entry.title for entry in entries] == ["simple-one", "simple-two"]
    rows = solve_level_pack(entries, max_states=1000)
    assert all(row["solved"] for row in rows)


def test_cli_solve_pack_json(tmp_path, capsys):
    pack_path = tmp_path / "pack.txt"
    pack_path.write_text(PACK, encoding="utf-8")
    exit_code = main(["solve-pack", "--file", str(pack_path), "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert len(data) == 2
    assert data[0]["solved"] is True


def test_cli_config_drives_defaults(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[solver]
max_states = 1000
[output]
json = true
show_frames = true
[logging]
level = \"INFO\"
""".strip(),
        encoding="utf-8",
    )
    output_path = tmp_path / "solution.json"
    exit_code = main([
        "--config",
        str(config_path),
        "solve",
        "--builtin",
        "tiny-one",
        "--output",
        str(output_path),
    ])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    exported = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["solved"] is True
    assert "frames" in payload
    assert exported["solved"] is True


def test_load_config_supports_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"solver": {"max_states": 1234}}', encoding="utf-8")
    assert load_config(str(path))["solver"]["max_states"] == 1234


def test_cli_explain_overlay_contains_annotations(capsys):
    exit_code = main(["explain", "--builtin", "corridor"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "overlay:" in captured.out
    assert any(ch in captured.out for ch in ("x", "c", "·"))


def test_cli_rejects_invalid_max_states(capsys):
    exit_code = main(["solve", "--builtin", "tiny-one", "--max-states", "0"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "max_states must be positive" in captured.out
