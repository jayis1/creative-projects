"""
Utility functions for the CDCL SAT Solver.

Provides DIMACS file I/O, model output, convenience solving, and
a DIMACS validator.
"""

from __future__ import annotations

import sys
from typing import List, Optional

from cdcl_sat.solver import Solver


def read_dimacs_file(filename: str) -> str:
    """Read a DIMACS CNF file.

    Args:
        filename: Path to the DIMACS CNF file.

    Returns:
        The file content as a string.
    """
    with open(filename, "r") as f:
        return f.read()


def write_dimacs_model(model: List[int], num_vars: int, filename: str):
    """Write a satisfying assignment to a file in DIMACS format.

    Args:
        model: List of DIMACS literals.
        num_vars: Total number of variables.
        filename: Path to write the model file.
    """
    content = Solver.model_to_dimacs(model, num_vars)
    with open(filename, "w") as f:
        f.write(content)


def solve_file(filename: str, time_limit: float = 0, verbose: int = 0) -> Solver:
    """Solve a DIMACS CNF file and return the solver object.

    Args:
        filename: Path to the DIMACS CNF file.
        time_limit: Maximum solving time in seconds (0 = unlimited).
        verbose: Verbosity level (0=silent, 1=stats, 2=trace).

    Returns:
        The Solver object after solving.
    """
    solver = Solver.from_file(filename)
    solver.verbose = verbose
    solver.solve(time_limit=time_limit)
    return solver


def validate_dimacs(text: str) -> List[str]:
    """Validate a DIMACS CNF string and return a list of issues found.

    Checks for:
    - Missing or malformed problem line
    - Variable indices exceeding declared count
    - Empty clauses
    - Duplicate clauses
    - Tautological clauses (containing both x and -x)

    Args:
        text: DIMACS CNF string content.

    Returns:
        List of issue descriptions (empty if valid).
    """
    issues = []
    num_vars = 0
    expected_clauses = 0
    has_problem_line = False
    clauses_found = 0
    max_var_seen = 0
    current_clause: List[int] = []
    all_clauses = []

    for line_num, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith("c"):
            continue
        if line.startswith("p"):
            parts = line.split()
            if len(parts) < 4:
                issues.append(f"Line {line_num}: Malformed problem line: '{line}'")
                continue
            try:
                num_vars = int(parts[2])
                expected_clauses = int(parts[3])
                has_problem_line = True
            except ValueError:
                issues.append(f"Line {line_num}: Invalid problem line numbers: '{line}'")
            continue

        # Clause data
        tokens = line.split()
        for tok in tokens:
            try:
                lit = int(tok)
            except ValueError:
                issues.append(f"Line {line_num}: Non-integer token '{tok}'")
                continue
            if lit == 0:
                if current_clause:
                    clauses_found += 1
                    max_var_in_clause = max(abs(l) for l in current_clause)
                    max_var_seen = max(max_var_seen, max_var_in_clause)

                    # Check for empty literals
                    if len(current_clause) == 0:
                        issues.append(f"Clause {clauses_found}: Empty clause")

                    # Check for tautological clause
                    lit_set = set(current_clause)
                    for l in current_clause:
                        if -l in lit_set:
                            issues.append(
                                f"Clause {clauses_found}: Tautological (contains both {l} and {-l})"
                            )
                            break

                    all_clauses.append(tuple(sorted(current_clause)))
                    current_clause = []
            else:
                if abs(lit) > num_vars and has_problem_line:
                    issues.append(
                        f"Line {line_num}: Variable {abs(lit)} exceeds declared {num_vars}"
                    )
                current_clause.append(lit)

    # Handle last clause if file doesn't end with 0
    if current_clause:
        clauses_found += 1
        all_clauses.append(tuple(sorted(current_clause)))

    if not has_problem_line:
        issues.append("Missing problem line (p cnf ...)")

    if has_problem_line and clauses_found != expected_clauses:
        issues.append(
            f"Expected {expected_clauses} clauses but found {clauses_found}"
        )

    if has_problem_line and max_var_seen > num_vars:
        issues.append(
            f"Maximum variable {max_var_seen} exceeds declared {num_vars}"
        )

    # Check for duplicate clauses
    seen_clauses = set()
    for clause in all_clauses:
        if clause in seen_clauses:
            issues.append(f"Duplicate clause: {clause}")
        seen_clauses.add(clause)

    return issues


def count_satisfying_assignments(num_vars: int, clauses: list, max_count: int = 65536) -> int:
    """Count the number of satisfying assignments (for small instances).

    Brute-force enumeration — only suitable for small instances (<= 20 vars).

    Args:
        num_vars: Number of variables.
        clauses: List of clauses (each clause is a list of literals).
        max_count: Maximum count before stopping (to avoid long computations).

    Returns:
        Number of satisfying assignments (up to max_count).
    """
    if num_vars > 20:
        return -1  # Too large for brute force

    count = 0
    for assignment in range(1 << num_vars):
        satisfied = True
        for clause in clauses:
            clause_ok = False
            for lit in clause:
                var = abs(lit) - 1
                val = bool((assignment >> var) & 1)
                if (lit > 0 and val) or (lit < 0 and not val):
                    clause_ok = True
                    break
            if not clause_ok:
                satisfied = False
                break

        if satisfied:
            count += 1
            if count >= max_count:
                return count

    return count