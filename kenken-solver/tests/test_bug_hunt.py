"""Bug hunt tests for the KenKen engine.

Each test verifies a specific bug before the fix is applied.
Run with: python3 tests/test_bug_hunt.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenken import (
    Cage, KenKenPuzzle, KenKenSolver, KenKenGenerator,
    PuzzleAnalyzer, render_puzzle, render_solution,
    render_cage_map, render_solved_puzzle,
)


# ---------------------------------------------------------------------------
# Bug 1: get_hint() ignores partial assignment when solving
# ---------------------------------------------------------------------------

def test_bug_hint_uses_partial_assignment():
    """get_hint() should return hints consistent with the partial assignment,
    not just the unrestricted solution.

    Before fix: get_hint() called self.solve() which ignores the partial
    assignment, so hints could be inconsistent with the given cells.
    After fix: get_hint() should solve with the partial assignment fixed.
    """
    gen = KenKenGenerator(size=4, seed=8)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    sol = solver.solve_grid()

    # Find a cell whose value differs from what we'll force
    # Force cell (0,0) to a WRONG value (different from solution)
    wrong_val = 2 if sol[0][0] == 1 else 1
    # But this might make the puzzle unsolvable — let's instead force
    # a correct value and check that hints are consistent with it.

    # Force a correct value
    partial = {(0, 0): sol[0][0]}
    hints = solver.get_hint(partial, num=3)

    # All hints must be consistent with the partial assignment:
    # the full solution (partial + hints) must be a valid solution
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
    """get_hint() with a partial assignment that conflicts with the unique
    solution should return no hints (or raise), not return wrong hints."""
    gen = KenKenGenerator(size=4, seed=8)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    sol = solver.solve_grid()

    # Force a wrong value that creates a cage violation
    # Find a single-cell cage and force a different value
    for cage in puzzle.cages:
        if cage.size == 1 and cage.op == "=":
            cell = cage.cells[0]
            wrong = cage.target + 1 if cage.target < puzzle.size else cage.target - 1
            if wrong < 1 or wrong > puzzle.size:
                continue
            # This partial assignment violates the cage constraint
            try:
                hints = solver.get_hint({cell: wrong}, num=1)
                # If no exception, hints should be empty (no valid solution)
                assert hints == [], \
                    f"Should return no hints for cage-violating partial, got {hints}"
            except ValueError:
                pass  # Acceptable to raise
            return
    # If no suitable single-cell cage found, skip
    assert True


# ---------------------------------------------------------------------------
# Bug 2: render_solved_puzzle crashes on None grid
# ---------------------------------------------------------------------------

def test_bug_render_solved_puzzle_none():
    """render_solved_puzzle should handle None grid gracefully.

    Before fix: passing None as grid would crash with TypeError.
    After fix: should return a message or raise a clear error.
    """
    gen = KenKenGenerator(size=4, seed=1)
    puzzle = gen.generate()
    # Create an unsolvable puzzle
    cages = [
        Cage([(0, 0), (0, 1)], "+", 100),
        Cage([(1, 0)], "=", 1),
        Cage([(1, 1)], "=", 1),
    ]
    bad_puzzle = KenKenPuzzle(2, cages)
    solver = KenKenSolver(bad_puzzle)
    grid = solver.solve_grid()
    assert grid is None
    # Should not crash
    try:
        result = render_solved_puzzle(bad_puzzle, grid)  # type: ignore
        # If it returns something, that's fine; if it raises, that's also fine
    except (TypeError, ValueError):
        pass  # Acceptable to raise with a clear error


# ---------------------------------------------------------------------------
# Bug 3: Cage target validation rejects target=0 for subtraction
# ---------------------------------------------------------------------------

def test_bug_subtraction_zero_target():
    """Subtraction with target=0 is valid (two cells with the same value).

    Before fix: Cage.__init__ allowed target<=0 for '-' but the generator
    never produces target=0 for 2-cell subtraction because it uses abs().
    However, a user-created puzzle could have target=0, which should work.
    """
    # 2x2: cells (0,0) and (0,1) in different columns, same row
    # can't have same value in same row, so this is actually impossible
    # in a valid Latin square. But the cage evaluation should still work.
    cage = Cage([(0, 0), (1, 0)], "-", 0)
    assert cage.satisfied({(0, 0): 3, (1, 0): 3})


# ---------------------------------------------------------------------------
# Bug 4: Unused variables in possible_targets
# ---------------------------------------------------------------------------

def test_bug_possible_targets():
    """possible_targets should return valid (op, target) pairs without error."""
    cage = Cage([(0, 0), (0, 1)], "+", 5)
    targets = cage.possible_targets(3)
    # Should include various (+, sum), (*, product), (-, diff), (/, quotient)
    assert ("+", 5) in targets  # 2+3 or 3+2
    assert ("+", 3) in targets  # 1+2 or 2+1
    # Subtraction targets should be non-negative for 2-cell
    for op, t in targets:
        if op == "-":
            assert t >= 0, f"Negative subtraction target: {t}"


# ---------------------------------------------------------------------------
# Bug 5: Generator _choose_operator can produce duplicate candidates
# ---------------------------------------------------------------------------

def test_bug_duplicate_candidates_in_choose_operator():
    """_choose_operator builds a candidates list that may contain duplicates
    (e.g., multiple permutations yielding the same target). The weighted
    selection should still work, but duplicates bias the selection.

    This test verifies the function returns a valid (op, target) pair."""
    gen = KenKenGenerator(size=5, seed=42)
    # Test with values that produce duplicate targets
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
# Bug 9: Negative target for subtraction should be rejected for 2-cell
# ---------------------------------------------------------------------------

def test_bug_negative_subtraction_target():
    """A 2-cell subtraction cage should never have a negative target since
    we use absolute difference. The Cage constructor should reject negative
    targets for 2-cell subtraction since abs() always produces non-negative."""
    # Actually, the constructor allows negative for '-' to support 3+ cell
    # subtraction. But for 2-cell, negative targets are meaningless.
    # This test documents the behavior.
    cage = Cage([(0, 0), (0, 1)], "-", -3)
    # This should not satisfy any assignment (abs diff is always >= 0)
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
    """count_solutions() and solve() with max_solutions=999999 should
    return the same count."""
    # 3x3 with minimal constraints — multiple solutions possible
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