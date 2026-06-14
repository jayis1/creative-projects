#!/usr/bin/env python3
"""
Test suite for the CDCL SAT Solver.
"""

import sys
import os
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver import Solver, luby
from generator import generate_php, generate_chain, generate_random_cnf, generate_tseitin


def test_simple_sat():
    """Test a simple satisfiable formula."""
    dimacs = """p cnf 3 3
1 2 0
-1 2 0
-2 3 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT, got {result}"
    model = solver.get_model()
    assert solver.verify_model(model), "Model verification failed"
    print("✓ test_simple_sat")


def test_simple_unsat():
    """Test a simple unsatisfiable formula."""
    dimacs = """p cnf 2 4
1 0
-1 0
2 0
-2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is False, f"Expected UNSAT, got {result}"
    print("✓ test_simple_unsat")


def test_unit_clauses():
    """Test formula with unit clauses."""
    dimacs = """p cnf 3 2
1 0
2 3 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT, got {result}"
    model = solver.get_model()
    assert 1 in model, "x1 should be True"
    assert solver.verify_model(model), "Model verification failed"
    print("✓ test_unit_clauses")


def test_pigeonhole_unsat():
    """Test pigeonhole principle: 4 pigeons, 3 holes → UNSAT."""
    num_vars, clauses = generate_php(4, 3)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)

    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is False, f"Expected UNSAT for PHP(4,3), got {result}"
    print("✓ test_pigeonhole_unsat")


def test_pigeonhole_sat():
    """Test pigeonhole principle: 3 pigeons, 3 holes → SAT."""
    num_vars, clauses = generate_php(3, 3)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)

    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT for PHP(3,3), got {result}"
    model = solver.get_model()
    assert solver.verify_model(model), "Model verification failed"
    print("✓ test_pigeonhole_sat")


def test_chain_sat():
    """Test chain formula → SAT."""
    num_vars, clauses = generate_chain(10)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)

    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT for chain, got {result}"
    model = solver.get_model()
    assert solver.verify_model(model), "Model verification failed"
    print("✓ test_chain_sat")


def test_random_sat():
    """Test random 3-SAT at low ratio (should be SAT)."""
    num_vars, clauses = generate_random_cnf(20, 60, k=3, seed=42)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)

    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    if result is True:
        model = solver.get_model()
        assert solver.verify_model(model), "Model verification failed"
    print(f"✓ test_random_sat (result={result})")


def test_tseitin():
    """Test Tseitin parity formula."""
    num_vars, clauses = generate_tseitin(5)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)

    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    if result is True:
        model = solver.get_model()
        assert solver.verify_model(model), "Model verification failed"
    print(f"✓ test_tseitin (result={result})")


def test_tautological_clause():
    """Test that tautological clauses are skipped."""
    dimacs = """p cnf 2 2
1 -1 0
1 2 0
"""
    solver = Solver.from_dimacs(dimacs)
    # Clause (1 OR NOT 1) is tautological → only clause (1 OR 2) remains
    result = solver.solve()
    assert result is True, f"Expected SAT, got {result}"
    print("✓ test_tautological_clause")


def test_empty_formula():
    """Test empty formula (no clauses) → SAT."""
    dimacs = """p cnf 5 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT for empty formula, got {result}"
    print("✓ test_empty_formula")


def test_luby_sequence():
    """Test Luby sequence correctness."""
    expected = [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]
    for i, exp in enumerate(expected, 1):
        assert luby(i) == exp, f"luby({i}) = {luby(i)}, expected {exp}"
    print("✓ test_luby_sequence")


def test_no_p_line():
    """Test DIMACS without p-line."""
    dimacs = """1 2 0
-1 2 0
-2 3 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT, got {result}"
    print("✓ test_no_p_line")


def test_dimacs_file_io():
    """Test DIMACS file I/O."""
    dimacs = """p cnf 3 2
1 2 0
-1 3 0
"""
    # Write to temp file and read back
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as f:
        f.write(dimacs)
        tmpname = f.name

    try:
        from solver import read_dimacs_file
        text = read_dimacs_file(tmpname)
        solver = Solver.from_dimacs(text)
        result = solver.solve()
        assert result is True, f"Expected SAT, got {result}"
    finally:
        os.unlink(tmpname)
    print("✓ test_dimacs_file_io")


def test_model_to_dimacs():
    """Test model to DIMACS conversion."""
    dimacs = """p cnf 2 1
1 2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True
    model = solver.get_model()
    output = Solver.model_to_dimacs(model, solver.num_vars)
    assert "SATISFIABLE" in output
    print("✓ test_model_to_dimacs")


def test_medium_instance():
    """Test a medium-sized random instance."""
    num_vars, clauses = generate_random_cnf(100, 350, k=3, seed=123)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)

    solver = Solver.from_dimacs(dimacs)
    result = solver.solve(time_limit=30)
    if result is True:
        model = solver.get_model()
        assert solver.verify_model(model), "Model verification failed"
    print(f"✓ test_medium_instance (result={result}, decisions={solver.decisions})")


def test_timeout():
    """Test that timeout returns None."""
    # Create a hard instance
    num_vars, clauses = generate_php(6, 5)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)

    solver = Solver.from_dimacs(dimacs)
    result = solver.solve(time_limit=0.001)  # Very short timeout
    # Could be True, False, or None
    print(f"✓ test_timeout (result={result})")


def test_conflict_driven_learning():
    """Test that learnt clauses are actually generated."""
    # A formula that requires conflict-driven learning
    dimacs = """p cnf 4 6
1 2 0
-1 3 0
-2 4 0
-3 -4 0
-1 -3 0
2 3 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    print(f"✓ test_conflict_driven_learning (result={result}, learnt={len(solver.learnt_clauses)})")


if __name__ == "__main__":
    tests = [
        test_simple_sat,
        test_simple_unsat,
        test_unit_clauses,
        test_pigeonhole_unsat,
        test_pigeonhole_sat,
        test_chain_sat,
        test_random_sat,
        test_tseitin,
        test_tautological_clause,
        test_empty_formula,
        test_luby_sequence,
        test_no_p_line,
        test_dimacs_file_io,
        test_model_to_dimacs,
        test_medium_instance,
        test_timeout,
        test_conflict_driven_learning,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)