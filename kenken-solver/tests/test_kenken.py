"""Comprehensive tests for the KenKen engine."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenken import (
    Cage, KenKenPuzzle, KenKenSolver, KenKenGenerator,
    PuzzleAnalyzer, render_puzzle, render_solution,
    render_cage_map, render_solved_puzzle,
)


# ---------------------------------------------------------------------------
# Cage tests
# ---------------------------------------------------------------------------

def test_cage_single_cell():
    c = Cage([(0, 0)], "=", 3)
    assert c.satisfied({(0, 0): 3})
    assert not c.satisfied({(0, 0): 2})


def test_cage_addition():
    c = Cage([(0, 0), (0, 1)], "+", 5)
    assert c.satisfied({(0, 0): 2, (0, 1): 3})
    assert not c.satisfied({(0, 0): 2, (0, 1): 2})


def test_cage_subtraction():
    c = Cage([(0, 0), (0, 1)], "-", 2)
    assert c.satisfied({(0, 0): 5, (0, 1): 3})
    assert c.satisfied({(0, 0): 3, (0, 1): 5})  # order-independent for 2-cell
    assert not c.satisfied({(0, 0): 3, (0, 1): 4})


def test_cage_multiplication():
    c = Cage([(0, 0), (0, 1), (0, 2)], "*", 24)
    assert c.satisfied({(0, 0): 2, (0, 1): 3, (0, 2): 4})


def test_cage_division():
    c = Cage([(0, 0), (0, 1)], "/", 3)
    assert c.satisfied({(0, 0): 6, (0, 1): 2})
    assert c.satisfied({(0, 0): 2, (0, 1): 6})  # order-independent
    assert not c.satisfied({(0, 0): 5, (0, 1): 2})


def test_cage_subtraction_three_cells():
    """Three-cell subtraction: 5 - 1 - 2 = 2."""
    c = Cage([(0, 0), (0, 1), (0, 2)], "-", 2)
    assert c.satisfied({(0, 0): 5, (0, 1): 1, (0, 2): 2})
    assert c.satisfied({(0, 0): 5, (0, 1): 2, (0, 2): 1})


def test_cage_invalid_operator():
    try:
        Cage([(0, 0)], "%", 3)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_cage_equals_requires_single_cell():
    try:
        Cage([(0, 0), (0, 1)], "=", 3)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_cage_hash_and_eq():
    c1 = Cage([(0, 0), (0, 1)], "+", 5)
    c2 = Cage([(0, 1), (0, 0)], "+", 5)  # same cells, different order
    assert c1 == c2
    assert hash(c1) == hash(c2)


# ---------------------------------------------------------------------------
# Puzzle validation tests
# ---------------------------------------------------------------------------

def test_puzzle_missing_cell():
    try:
        KenKenPuzzle(3, [Cage([(0, 0)], "=", 1)])
        assert False, "Should have raised"
    except ValueError:
        pass


def test_puzzle_overlapping_cages():
    try:
        cages = [Cage([(0, 0), (0, 1)], "+", 3), Cage([(0, 1), (0, 2)], "+", 5)]
        KenKenPuzzle(3, cages)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_puzzle_noncontiguous_cage():
    # Cells (0,0) and (2,2) are not adjacent
    cages = [
        Cage([(0, 0), (2, 2)], "+", 3),
        Cage([(0, 1)], "=", 1),
        Cage([(0, 2)], "=", 1),
        Cage([(1, 0)], "=", 1),
        Cage([(1, 1)], "=", 1),
        Cage([(1, 2)], "=", 1),
        Cage([(2, 0)], "=", 1),
        Cage([(2, 1)], "=", 1),
    ]
    try:
        KenKenPuzzle(3, cages)
        assert False, "Should have raised for non-contiguous cage"
    except ValueError:
        pass


def test_puzzle_out_of_bounds():
    try:
        KenKenPuzzle(2, [Cage([(0, 0), (0, 5)], "+", 3), Cage([(0, 1)], "=", 1),
                         Cage([(1, 0)], "=", 1), Cage([(1, 1)], "=", 1)])
        assert False, "Should have raised"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Solver tests
# ---------------------------------------------------------------------------

def test_solver_4x4():
    gen = KenKenGenerator(size=4, seed=1)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1, "Generated puzzle should be unique"


def test_solver_finds_solution():
    gen = KenKenGenerator(size=5, seed=10)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    grid = solver.solve_grid()
    assert grid is not None
    # Verify Latin square property
    n = 5
    for r in range(n):
        assert sorted(grid[r]) == list(range(1, n + 1))
    for c in range(n):
        assert sorted(grid[r][c] for r in range(n)) == list(range(1, n + 1))


def test_generator_uniqueness_5x5():
    gen = KenKenGenerator(size=5, seed=10)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1


def test_generator_uniqueness_6x6_hard():
    gen = KenKenGenerator(size=6, seed=42, difficulty="hard")
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1


def test_solution_matches_generator():
    gen = KenKenGenerator(size=5, seed=7)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    grid = solver.solve_grid()
    assert grid == gen.solution


def test_count_solutions_unique():
    gen = KenKenGenerator(size=4, seed=3)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    count = solver.count_solutions()
    assert count == 1


def test_count_solutions_multiple():
    """A puzzle with minimal constraints should have multiple solutions."""
    # 2x2 with one cage: sum=6. Both Latin squares [[1,2],[2,1]] and
    # [[2,1],[1,2]] have all cells summing to 6, so both are valid.
    cages = [Cage([(0, 0), (0, 1), (1, 0), (1, 1)], "+", 6)]
    puzzle = KenKenPuzzle(2, cages)
    solver = KenKenSolver(puzzle)
    count = solver.count_solutions()
    assert count == 2


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------

def test_json_roundtrip():
    gen = KenKenGenerator(size=4, seed=3)
    puzzle = gen.generate()
    j = puzzle.to_json()
    puzzle2 = KenKenPuzzle.from_json(j)
    assert puzzle.size == puzzle2.size
    assert len(puzzle.cages) == len(puzzle2.cages)
    solver = KenKenSolver(puzzle2)
    grid = solver.solve_grid()
    assert grid is not None


def test_text_roundtrip():
    gen = KenKenGenerator(size=4, seed=5)
    puzzle = gen.generate()
    text = puzzle.to_text()
    puzzle2 = KenKenPuzzle.from_text(text)
    assert puzzle.size == puzzle2.size
    assert len(puzzle.cages) == len(puzzle2.cages)
    solver = KenKenSolver(puzzle2)
    grid = solver.solve_grid()
    assert grid is not None


def test_text_format_with_comments():
    text = """# This is a comment
size: 3
0,0 0,1 + 3
0,2 = 1
1,0 1,1 + 5
1,2 = 1
2,0 2,1 + 5
2,2 = 1
"""
    puzzle = KenKenPuzzle.from_text(text)
    assert puzzle.size == 3
    assert len(puzzle.cages) == 6


# ---------------------------------------------------------------------------
# Hint tests
# ---------------------------------------------------------------------------

def test_hint_basic():
    gen = KenKenGenerator(size=4, seed=8)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    # Get a hint with no pre-filled cells
    hints = solver.get_hint({}, num=2)
    assert len(hints) <= 2
    assert len(hints) > 0


def test_hint_with_partial():
    gen = KenKenGenerator(size=4, seed=8)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    sol = solver.solve_grid()
    # Give one cell as partial
    partial = {(0, 0): sol[0][0]}
    hints = solver.get_hint(partial, num=1)
    assert len(hints) == 1
    # The hint should be consistent with the solution
    cell, val = hints[0]
    assert sol[cell[0]][cell[1]] == val


def test_hint_detects_conflict():
    gen = KenKenGenerator(size=4, seed=8)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    # Put conflicting values in same row
    try:
        solver.get_hint({(0, 0): 1, (0, 1): 1}, num=1)
        assert False, "Should have raised"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Analyzer tests
# ---------------------------------------------------------------------------

def test_analyzer():
    gen = KenKenGenerator(size=5, seed=20)
    puzzle = gen.generate()
    analyzer = PuzzleAnalyzer(puzzle)
    results = analyzer.analyze()
    assert results["size"] == 5
    assert results["num_cages"] > 0
    assert "difficulty_score" in results
    assert results["difficulty_category"] in ("easy", "medium", "hard")
    assert results["solver_nodes"] > 0


# ---------------------------------------------------------------------------
# Generator option tests
# ---------------------------------------------------------------------------

def test_generator_no_singletons():
    gen = KenKenGenerator(size=5, seed=30, allow_singletons=False)
    puzzle = gen.generate()
    for cage in puzzle.cages:
        assert cage.size >= 2, f"Found singleton cage: {cage}"


def test_generator_difficulty_easy():
    gen = KenKenGenerator(size=4, seed=40, difficulty="easy")
    puzzle = gen.generate()
    # Easy puzzles should have no division cages
    ops = {c.op for c in puzzle.cages}
    # Not guaranteed but very likely
    # Just verify it's solvable and unique
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1


def test_generator_max_cage_size():
    gen = KenKenGenerator(size=6, seed=50, max_cage_size=2)
    puzzle = gen.generate()
    for cage in puzzle.cages:
        assert cage.size <= 2


# ---------------------------------------------------------------------------
# Rendering tests
# ---------------------------------------------------------------------------

def test_render_puzzle():
    gen = KenKenGenerator(size=3, seed=1)
    puzzle = gen.generate()
    s = render_puzzle(puzzle)
    assert "+" in s and "|" in s


def test_render_cage_map():
    gen = KenKenGenerator(size=3, seed=1)
    puzzle = gen.generate()
    s = render_cage_map(puzzle)
    assert "+" in s and "|" in s


def test_render_solved_puzzle():
    gen = KenKenGenerator(size=3, seed=1)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    grid = solver.solve_grid()
    s = render_solved_puzzle(puzzle, grid)
    assert "+" in s and "|" in s


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_2x2_puzzle():
    """Smallest valid KenKen puzzle."""
    gen = KenKenGenerator(size=2, seed=100)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1


def test_solver_unsolvable():
    """A puzzle with contradictory cage constraints should have no solution."""
    # 2x2 where a cage requires sum 100 (impossible with values 1-2)
    cages = [
        Cage([(0, 0), (0, 1)], "+", 100),
        Cage([(1, 0)], "=", 1),
        Cage([(1, 1)], "=", 1),
    ]
    puzzle = KenKenPuzzle(2, cages)
    solver = KenKenSolver(puzzle)
    assert solver.solve_grid() is None


def test_cage_pretty_repr():
    c = Cage([(0, 0)], "=", 3)
    r = repr(c)
    assert "Cage" in r and "=" in r


if __name__ == "__main__":
    # Run all test functions
    test_funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for tf in test_funcs:
        try:
            tf()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {tf.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed, {len(test_funcs)} total")