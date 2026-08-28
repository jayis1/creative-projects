from sokoban_solver import SokobanSolver, get_level, list_levels, parse_level

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
