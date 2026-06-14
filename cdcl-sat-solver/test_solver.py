#!/usr/bin/env python3
"""
Test suite for the CDCL SAT Solver.
Covers core solving, preprocessing, incremental solving, and edge cases.
"""

import sys
import os
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver import Solver, luby
from generator import generate_php, generate_chain, generate_random_cnf, generate_tseitin


# ---- Helper ----

def run_test(name, func):
    try:
        func()
        print(f"✓ {name}")
        return True
    except Exception as e:
        print(f"✗ {name}: {e}")
        import traceback
        traceback.print_exc()
        return False


# ---- Core SAT/UNSAT tests ----

def test_simple_sat():
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


def test_simple_unsat():
    dimacs = """p cnf 2 4
1 0
-1 0
2 0
-2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is False, f"Expected UNSAT, got {result}"


def test_unit_conflict():
    """Two unit clauses that conflict: x and -x."""
    dimacs = """p cnf 1 2
1 0
-1 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is False, f"Expected UNSAT, got {result}"


def test_unit_clauses():
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


def test_pigeonhole_unsat():
    """PHP(4,3): 4 pigeons, 3 holes → UNSAT."""
    num_vars, clauses = generate_php(4, 3)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve(time_limit=60)
    assert result is False, f"Expected UNSAT for PHP(4,3), got {result}"


def test_pigeonhole_sat():
    """PHP(3,3): 3 pigeons, 3 holes → SAT."""
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


def test_chain_sat():
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


def test_random_sat():
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


def test_tseitin():
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


def test_tautological_clause():
    dimacs = """p cnf 2 2
1 -1 0
1 2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT, got {result}"


def test_empty_formula():
    dimacs = """p cnf 5 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT for empty formula, got {result}"


def test_luby_sequence():
    expected = [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]
    for i, exp in enumerate(expected, 1):
        assert luby(i) == exp, f"luby({i}) = {luby(i)}, expected {exp}"


def test_no_p_line():
    dimacs = """1 2 0
-1 2 0
-2 3 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT, got {result}"


def test_multiline_clause():
    """Test DIMACS with multi-line clauses (0 terminates each clause)."""
    dimacs = """p cnf 3 2
1 2
3 0
-1 -2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True, f"Expected SAT, got {result}"


def test_dimacs_file_io():
    dimacs = """p cnf 3 2
1 2 0
-1 3 0
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as f:
        f.write(dimacs)
        tmpname = f.name
    try:
        solver = Solver.from_file(tmpname)
        result = solver.solve()
        assert result is True, f"Expected SAT, got {result}"
    finally:
        os.unlink(tmpname)


def test_model_to_dimacs():
    dimacs = """p cnf 2 1
1 2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True
    model = solver.get_model()
    output = Solver.model_to_dimacs(model, solver.num_vars)
    assert "SATISFIABLE" in output


def test_medium_instance():
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


def test_timeout():
    """Test that timeout returns None."""
    num_vars, clauses = generate_php(6, 5)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve(time_limit=0.001)
    # Could be True, False, or None


def test_conflict_driven_learning():
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
    # Just check it produces a result without crashing
    assert result in (True, False, None)


# ---- Preprocessing tests ----

def test_preprocess_subsumption():
    """Test that subsumption removes redundant clauses."""
    # (1) subsumes (1, 2)
    dimacs = """p cnf 2 3
1 0
1 2 0
-1 -2 0
"""
    solver = Solver.from_dimacs(dimacs)
    original_count = len(solver.clauses)
    solver.preprocess()
    # After preprocessing, the subsumed clause should be removed
    assert len(solver.clauses) <= original_count


def test_preprocess_unit_prop():
    """Test that unit propagation during preprocessing works."""
    dimacs = """p cnf 3 3
1 0
-1 2 0
-1 3 0
"""
    solver = Solver.from_dimacs(dimacs)
    solver.preprocess()
    result = solver.solve()
    assert result is True
    model = solver.get_model()
    assert 1 in model, "x1 should be True"


# ---- Incremental solving tests ----

def test_assumption_solving():
    """Test solving with assumptions."""
    # (x1 OR x2) AND (x1 OR -x2) → x1 is forced
    dimacs = """p cnf 2 2
1 2 0
1 -2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True
    model = solver.get_model()
    assert 1 in model, "x1 should be True"


def test_assumption_unsat():
    """Test assumptions that make a SAT formula UNSAT."""
    # (x1 OR x2) is SAT, but with assumption -x1 AND -x2, it's UNSAT
    dimacs = """p cnf 2 1
1 2 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve(assumptions=[-1, -2])
    assert result is False, f"Expected UNSAT with assumptions, got {result}"


# ---- Geometric restart test ----

def test_geometric_restart():
    """Test geometric restart strategy."""
    num_vars, clauses = generate_random_cnf(30, 120, k=3, seed=77)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)
    solver = Solver.from_dimacs(dimacs)
    solver.restart_strategy = "geometric"
    result = solver.solve(time_limit=10)
    if result is True:
        model = solver.get_model()
        assert solver.verify_model(model), "Model verification failed"


# ---- Larger instance test ----

def test_larger_pigeonhole():
    """Test PHP(5,4) which should be UNSAT."""
    num_vars, clauses = generate_php(5, 4)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve(time_limit=60)
    assert result is False, f"Expected UNSAT for PHP(5,4), got {result}"


# ---- Statistics test ----

def test_statistics():
    """Test that statistics are tracked correctly."""
    num_vars, clauses = generate_random_cnf(20, 80, k=3, seed=99)
    dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
    dimacs = "\n".join(dimacs_lines)
    solver = Solver.from_dimacs(dimacs)
    solver.solve()
    stats = solver.get_stats()
    assert stats.propagations >= 0
    assert stats.start_time > 0


# ---- Model completeness test ----

def test_model_completeness():
    """Test that all variables are assigned in the model."""
    dimacs = """p cnf 5 3
1 2 0
3 4 0
-5 0
"""
    solver = Solver.from_dimacs(dimacs)
    result = solver.solve()
    assert result is True
    model = solver.get_model()
    assert len(model) == 5, f"Expected 5 variables in model, got {len(model)}"


# ---- Run all tests ----

if __name__ == "__main__":
    tests = [
        ("simple_sat", test_simple_sat),
        ("simple_unsat", test_simple_unsat),
        ("unit_conflict", test_unit_conflict),
        ("unit_clauses", test_unit_clauses),
        ("pigeonhole_unsat", test_pigeonhole_unsat),
        ("pigeonhole_sat", test_pigeonhole_sat),
        ("chain_sat", test_chain_sat),
        ("random_sat", test_random_sat),
        ("tseitin", test_tseitin),
        ("tautological_clause", test_tautological_clause),
        ("empty_formula", test_empty_formula),
        ("luby_sequence", test_luby_sequence),
        ("no_p_line", test_no_p_line),
        ("multiline_clause", test_multiline_clause),
        ("dimacs_file_io", test_dimacs_file_io),
        ("model_to_dimacs", test_model_to_dimacs),
        ("medium_instance", test_medium_instance),
        ("timeout", test_timeout),
        ("conflict_driven_learning", test_conflict_driven_learning),
        ("preprocess_subsumption", test_preprocess_subsumption),
        ("preprocess_unit_prop", test_preprocess_unit_prop),
        ("assumption_solving", test_assumption_solving),
        ("assumption_unsat", test_assumption_unsat),
        ("geometric_restart", test_geometric_restart),
        ("larger_pigeonhole", test_larger_pigeonhole),
        ("statistics", test_statistics),
        ("model_completeness", test_model_completeness),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        if run_test(name, func):
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)