#!/usr/bin/env python3
"""
CNF Instance Generator for testing the CDCL SAT solver.

Generates various classic SAT benchmark instances:
- Pigeonhole Principle (PHP): Unsatisfiable
- Random k-SAT: Variable difficulty
- Chain formulas: Simple satisfiable
- Tseitin formulas: Structured unsatisfiable
"""

import argparse
import random
import sys


def generate_php(n: int, m: int) -> tuple:
    """Generate Pigeonhole Principle instance: n pigeons, m holes (n > m → UNSAT)."""
    clauses = []
    num_vars = n * m

    # Each pigeon must go in at least one hole
    for i in range(n):
        clause = [(i * m + j + 1) for j in range(m)]
        clauses.append(clause)

    # No two pigeons in the same hole
    for j in range(m):
        for i1 in range(n):
            for i2 in range(i1 + 1, n):
                clauses.append([-(i1 * m + j + 1), -(i2 * m + j + 1)])

    return num_vars, clauses


def generate_random_cnf(num_vars: int, num_clauses: int, k: int = 3,
                        seed: int = None) -> tuple:
    """Generate a random k-SAT instance."""
    if seed is not None:
        random.seed(seed)

    clauses = []
    for _ in range(num_clauses):
        clause = []
        vars_used = set()
        while len(clause) < k:
            v = random.randint(1, num_vars)
            if v not in vars_used:
                vars_used.add(v)
                sign = random.choice([1, -1])
                clause.append(sign * v)
        clauses.append(clause)

    return num_vars, clauses


def generate_chain(num_vars: int) -> tuple:
    """
    Generate a simple satisfiable chain formula:
    (x1) AND (x1 → x2) AND (x2 → x3) AND ... AND (x_{n-1} → x_n)
    """
    clauses = []
    # x1 must be true
    clauses.append([1])
    # Implications: x_i → x_{i+1}  ≡  ¬x_i ∨ x_{i+1}
    for i in range(1, num_vars):
        clauses.append([-i, i + 1])

    return num_vars, clauses


def generate_tseitin(num_vars: int) -> tuple:
    """
    Generate a Tseitin-encoded parity formula.
    The parity of all variables must be even (UNSAT if odd number of vars).
    """
    # We encode XOR constraints: x1 ⊕ x2 ⊕ ... ⊕ xn = True
    # For each XOR(a, b) = c, we need 4 clauses:
    # ¬a ∨ ¬b ∨ c, a ∨ b ∨ c, a ∨ ¬b ∨ ¬c, ¬a ∨ b ∨ ¬c
    # We chain: x1 ⊕ x2 = t1, t1 ⊕ x3 = t2, ..., t_{n-2} ⊕ xn = True

    n = num_vars
    clauses = []
    total_vars = n

    # Auxiliary variables for intermediate XOR results
    # t_i represents XOR of x1..x_{i+1}, stored at variable n + i
    # So t1 = n+1, t2 = n+2, etc.

    # First: x1 ⊕ x2 = t1
    t1 = total_vars + 1
    total_vars += 1
    a, b, c = 1, 2, t1
    clauses.extend([[-a, -b, c], [a, b, c], [a, -b, -c], [-a, b, -c]])

    # Chain: t_i ⊕ x_{i+2} = t_{i+1}
    prev_t = t1
    for i in range(3, n + 1):
        new_t = total_vars + 1
        total_vars += 1
        a, b, c = prev_t, i, new_t
        clauses.extend([[-a, -b, c], [a, b, c], [a, -b, -c], [-a, b, -c]])
        prev_t = new_t

    # Final constraint: result must be True
    # So prev_t (the final XOR) must be True
    clauses.append([prev_t])

    return total_vars, clauses


def generate_mutilated_chessboard(n: int) -> tuple:
    """
    Generate the mutilated chessboard problem.
    An n×n board with opposite corners removed cannot be tiled with dominos.
    UNSAT for even n.
    """
    # Each cell (i,j) gets a variable
    # Horizontal dominos cover (i,j)-(i,j+1)
    # Vertical dominos cover (i,j)-(i+1,j)
    # Remove corners (0,0) and (n-1,n-1)

    total_vars = 0
    cell_var = {}
    for i in range(n):
        for j in range(n):
            total_vars += 1
            cell_var[(i, j)] = total_vars

    clauses = []

    # Removed cells cannot be covered
    removed = {(0, 0), (n - 1, n - 1)}

    # Every non-removed cell must be covered by exactly one domino
    for i in range(n):
        for j in range(n):
            if (i, j) in removed:
                continue

            # Possible domino placements covering (i,j)
            placements = []

            # Horizontal domino (i,j)-(i,j+1)
            if j + 1 < n and (i, j + 1) not in removed:
                domino_var = total_vars + 1
                total_vars += 1
                placements.append(domino_var)
                # If this domino is placed, both cells are covered
                clauses.append([-domino_var, cell_var[(i, j)]])
                clauses.append([-domino_var, cell_var[(i, j + 1)]])

            # Horizontal domino (i,j-1)-(i,j)
            if j - 1 >= 0 and (i, j - 1) not in removed:
                # This is the same domino as above, just from the other cell's perspective
                pass  # Will be handled when we process (i, j-1)

            # Vertical domino (i,j)-(i+1,j)
            if i + 1 < n and (i + 1, j) not in removed:
                domino_var = total_vars + 1
                total_vars += 1
                placements.append(domino_var)
                clauses.append([-domino_var, cell_var[(i, j)]])
                clauses.append([-domino_var, cell_var[(i + 1, j)]])

            # At least one domino must cover this cell
            if placements:
                clauses.append(placements)
            else:
                # Cell has no possible domino placement → UNSAT
                clauses.append([cell_var[(i, j)]])  # Must be covered but can't be

            # No two dominos can overlap (at most one domino per cell)
            for a_idx in range(len(placements)):
                for b_idx in range(a_idx + 1, len(placements)):
                    clauses.append([-placements[a_idx], -placements[b_idx]])

    return total_vars, clauses


def write_dimacs(num_vars: int, clauses: list, filename: str = None):
    """Write DIMACS CNF format."""
    lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        lines.append(" ".join(str(l) for l in clause) + " 0")

    content = "\n".join(lines) + "\n"

    if filename:
        with open(filename, "w") as f:
            f.write(content)
    else:
        print(content)


def main():
    parser = argparse.ArgumentParser(description="CNF Instance Generator")
    parser.add_argument("--type", choices=["php", "random", "chain", "tseitin", "chessboard"],
                        required=True, help="Type of instance to generate")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output file (default: stdout)")

    # PHP parameters
    parser.add_argument("--n", type=int, default=4, help="Number of pigeons (PHP)")
    parser.add_argument("--m", type=int, default=3, help="Number of holes (PHP)")

    # Random SAT parameters
    parser.add_argument("--vars", type=int, default=50, help="Number of variables (random)")
    parser.add_argument("--clauses", type=int, default=200, help="Number of clauses (random)")
    parser.add_argument("--k", type=int, default=3, help="Clause length (random)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")

    args = parser.parse_args()

    if args.type == "php":
        num_vars, clauses = generate_php(args.n, args.m)
    elif args.type == "random":
        num_vars, clauses = generate_random_cnf(args.vars, args.clauses, args.k, args.seed)
    elif args.type == "chain":
        num_vars, clauses = generate_chain(args.vars)
    elif args.type == "tseitin":
        num_vars, clauses = generate_tseitin(args.vars)
    elif args.type == "chessboard":
        num_vars, clauses = generate_mutilated_chessboard(args.n)
    else:
        print(f"Unknown type: {args.type}", file=sys.stderr)
        sys.exit(1)

    write_dimacs(num_vars, clauses, args.output)
    if args.output:
        print(f"c Generated {args.type}: {num_vars} vars, {len(clauses)} clauses → {args.output}",
              file=sys.stderr)


if __name__ == "__main__":
    main()