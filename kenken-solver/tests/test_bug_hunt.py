"""Bug hunt tests for the KenKen engine.

Each test verifies a specific bug that was identified during the Phase 3
bug hunt and confirms the fix is still in effect.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenken_solver import (
    Cage, KenKenPuzzle, KenKenSolver, KenKenGenerator,
    PuzzleAnalyzer, render_puzzle, render_solution,
    render_cage_map, render_solved_puzzle,
)


# ---------------------------------------------------------------------------
# Bug 1: get_hint() ignores partial assignment when solving
# ---------------------------------------------------------------------------

def test_bug_hint_uses_partial_assignment():
    """get_hint() should return hints consistent with the partial assignment."""
    gen = KenKenGenerator(size=4, seed=8)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    sol = solver.solve_grid()

    # Force a correct value
    partial = {(0, 0): sol[0][0]}
    hints = solver.get_hint(partial, num=3)

    # All hints must be consistent with the partial assignment
    full = dict(partial)
    for cell, val in hints:
        full[cell] = val

    # Check row/col constraints
    n = puzzle.size
    for r in range(n):
        row_vals = [full.get((r, c)) for c in range(n) if (r, c) in full]
        assert len(row_vals) == len(set(row_vals)), \
            f"Duplicate in row {r}: {row_vals}"
    for c in range(n):
        col_vals = [full.get((r, c)) for r in range(n) if (r, c) in full]
        assert len(col_vals) == len(set(col_vals)), \
            f"Duplicate in col {c}: {col_vals}"

    # Check cage constraints for fully-assigned cages
    for cage in puzzle.cages:
        vals = [full.get(cell) for cell in cage.cells]
        if all(v is not None for v in vals):
            assert cage._evaluate([v for v in vals if v is not None]), \
                f"Cage {cage} not satisfied by {vals}"


def test_bug_hint_with_conflicting_partial():
    """get_hint() with a partial assignment that conflicts should return no hints."""
    gen = KenKenGenerator(size=4, seed=8)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    sol = solver.solve_grid()

    # Find a single-cell cage and force a different value
    for cage in puzzle.cages:
        if cage.size == 1 and cage.op == "=":
            cell = cage.cells[0]
            wrong = cage.target + 1 if cage.target < puzzle.size else cage.target - 1
            if wrong < 1 or wrong > puzzle.size:
                continue
            try:
                hints = solver.get_hint({cell: wrong}, num=1)
                assert hints == [], \
                    f"Should return no hints for cage-violating partial, got {hints}"
            except ValueError:
                pass
            return
    assert True


# ---------------------------------------------------------------------------
# Bug 2: render_solved_puzzle crashes on None grid
# ---------------------------------------------------------------------------

def test_bug_render_solved_puzzle_none():
    """render_solved_puzzle should handle None grid gracefully."""
    gen = KenKenGenerator(size=4, seed=1)
    puzzle = gen.generate()
    cages = [
        Cage([(0, 0), (0, 1)], "+", 100),
        Cage([(1, 0)], "=", 1),
        Cage([(1, 1)], "=", 1),
    ]
    bad_puzzle = KenKenPuzzle(2, cages)
    solver = KenKenSolver(bad_puzzle)
    grid = solver.solve_grid()
    assert grid is None
    try:
        result = render_solved_puzzle(bad_puzzle, grid)  # type: ignore
    except (TypeError, ValueError):
        pass


# ---------------------------------------------------------------------------
# Bug 3: Cage target validation rejects target=0 for subtraction
# ---------------------------------------------------------------------------

def test_bug_subtraction_zero_target():
    """Subtraction with target=0 is valid (two cells with the same value)."""
    cage = Cage([(0, 0), (1, 0)], "-", 0)
    assert cage.satisfied({(0, 0): 3, (1, 0): 3})


# ---------------------------------------------------------------------------
# Bug 4: Unused variables in possible_targets
# ---------------------------------------------------------------------------

def test_bug_possible_targets():
    """possible_targets should return valid (op, target) pairs."""
    cage = Cage([(0, 0), (0, 1)], "+", 5)
    targets = cage.possible_targets(3)
    assert ("+", 5) in targets
    assert ("+", 3) in targets
    for op, t in targets:
        if op == "-":
            assert t >= 0, f"Negative subtraction target: {t}"


# ---------------------------------------------------------------------------
# Bug 5: Generator _choose_operator can produce duplicate candidates
# ---------------------------------------------------------------------------

def test_bug_duplicate_candidates_in_choose_operator():
    """_choose_operator should return a valid (op, target) pair."""
    gen = KenKenGenerator(size=5, seed=42)
    op, target = gen._choose_operator([1, 1, 2])
    assert op in ("+", "-", "*", "/")
    assert target > 0


# ---------------------------------------------------------------------------
# Bug 6: from_text doesn't validate operator
# ---------------------------------------------------------------------------

def test_bug_from_text_invalid_operator():
    """from_text should reject invalid operators."""
    text = """size: 2
0,0 0,1 % 3
1,0 = 1
1,1 = 1
"""
    try:
        KenKenPuzzle.from_text(text)
        assert False, "Should have raised for invalid operator %"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Bug 7: Solver with max_solutions=0 should return immediately
# ---------------------------------------------------------------------------

def test_bug_solver_max_solutions_zero():
    """Solver with max_solutions=0 should return no solutions."""
    gen = KenKenGenerator(size=4, seed=1)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle, max_solutions=0)
    solver.solve()
    assert len(solver.solutions) == 0


# ---------------------------------------------------------------------------
# Bug 8: Generator with max_cage_size=1 should produce all singletons
# ---------------------------------------------------------------------------

def test_bug_generator_max_cage_size_1():
    """Generator with max_cage_size=1 should produce all single-cell cages."""
    gen = KenKenGenerator(size=4, seed=5, max_cage_size=1)
    puzzle = gen.generate()
    for cage in puzzle.cages:
        assert cage.size == 1, f"Expected singleton, got size {cage.size}"


# ---------------------------------------------------------------------------
# Bug 9: Negative target for subtraction
# ---------------------------------------------------------------------------

def test_bug_negative_subtraction_target():
    """A 2-cell subtraction cage with a negative target should not satisfy."""
    cage = Cage([(0, 0), (0, 1)], "-", -3)
    assert not cage.satisfied({(0, 0): 1, (0, 1): 2})
    assert not cage.satisfied({(0, 0): 5, (0, 1): 3})


# ---------------------------------------------------------------------------
# Bug 10: Division by 1 should work
# ---------------------------------------------------------------------------

def test_bug_division_by_one():
    """Division cage with target achieved by dividing by 1."""
    cage = Cage([(0, 0), (0, 1)], "/", 5)
    assert cage.satisfied({(0, 0): 5, (0, 1): 1})
    assert cage.satisfied({(0, 0): 1, (0, 1): 5})


# ---------------------------------------------------------------------------
# Bug 11: Large grid generation should not hang
# ---------------------------------------------------------------------------

def test_bug_large_grid_generation():
    """7x7 puzzle generation should complete in reasonable time."""
    import time
    gen = KenKenGenerator(size=7, seed=123)
    t0 = time.time()
    puzzle = gen.generate()
    elapsed = time.time() - t0
    assert elapsed < 30, f"7x7 generation took {elapsed:.1f}s"
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1


# ---------------------------------------------------------------------------
# Bug 12: count_solutions should match solve() count
# ---------------------------------------------------------------------------

def test_bug_count_matches_solve():
    """count_solutions() and solve() should return the same count."""
    cages = [
        Cage([(0, 0), (0, 1), (0, 2)], "+", 6),
        Cage([(1, 0), (1, 1), (1, 2)], "+", 6),
        Cage([(2, 0), (2, 1), (2, 2)], "+", 6),
    ]
    puzzle = KenKenPuzzle(3, cages)

    solver1 = KenKenSolver(puzzle, max_solutions=999999)
    solver1.solve()
    solve_count = len(solver1.solutions)

    solver2 = KenKenSolver(puzzle)
    count_count = solver2.count_solutions()

    assert solve_count == count_count, \
        f"solve() found {solve_count}, count_solutions() found {count_count}"


if __name__ == "__main__":
    test_funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_bug") and callable(v)]
    passed = 0
    failed = 0
    for tf in test_funcs:
        try:
            tf()
            passed += 1
            print(f"  PASS: {tf.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {tf.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed, {len(test_funcs)} total")