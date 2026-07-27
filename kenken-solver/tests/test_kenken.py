"""Basic smoke tests for the KenKen engine."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenken import Cage, KenKenPuzzle, KenKenSolver, KenKenGenerator, render_puzzle, render_solution


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


def test_puzzle_validation():
    # Missing cell should raise
    try:
        KenKenPuzzle(3, [Cage([(0, 0)], "=", 1)])
        assert False, "Should have raised"
    except ValueError:
        pass


def test_solver_4x4():
    gen = KenKenGenerator(size=4, seed=1)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1, "Generated puzzle should be unique"


def test_generator_uniqueness_5x5():
    gen = KenKenGenerator(size=5, seed=10)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    assert len(solver.solutions) == 1


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


def test_solution_matches_generator():
    gen = KenKenGenerator(size=5, seed=7)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)
    grid = solver.solve_grid()
    assert grid == gen.solution


def test_render_puzzle():
    gen = KenKenGenerator(size=3, seed=1)
    puzzle = gen.generate()
    s = render_puzzle(puzzle)
    assert "+" in s and "|" in s


if __name__ == "__main__":
    test_cage_single_cell()
    test_cage_addition()
    test_cage_subtraction()
    test_cage_multiplication()
    test_cage_division()
    test_puzzle_validation()
    test_solver_4x4()
    test_generator_uniqueness_5x5()
    test_json_roundtrip()
    test_solution_matches_generator()
    test_render_puzzle()
    print("All tests passed!")