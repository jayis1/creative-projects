"""
CNF Instance Generator for testing the CDCL SAT solver.

Generates various classic SAT benchmark instances:
- Pigeonhole Principle (PHP): Unsatisfiable
- Random k-SAT: Variable difficulty
- Chain formulas: Simple satisfiable
- Tseitin formulas: Structured unsatisfiable
- Mutilated chessboard: Structured UNSAT
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import List, Tuple


def generate_php(n: int, m: int) -> Tuple[int, List[List[int]]]:
    """Generate Pigeonhole Principle instance: n pigeons, m holes (n > m → UNSAT).

    Args:
        n: Number of pigeons.
        m: Number of holes.

    Returns:
        Tuple of (num_vars, clauses).
    """
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


def generate_random_cnf(
    num_vars: int, num_clauses: int, k: int = 3, seed: int = None
) -> Tuple[int, List[List[int]]]:
    """Generate a random k-SAT instance.

    Args:
        num_vars: Number of variables.
        num_clauses: Number of clauses.
        k: Clause length (default: 3).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (num_vars, clauses).
    """
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


def generate_chain(num_vars: int) -> Tuple[int, List[List[int]]]:
    """Generate a simple satisfiable chain formula.

    (x1) AND (x1 → x2) AND (x2 → x3) AND ... AND (x_{n-1} → x_n)

    Args:
        num_vars: Number of variables in the chain.

    Returns:
        Tuple of (num_vars, clauses).
    """
    clauses = []
    # x1 must be true
    clauses.append([1])
    # Implications: x_i → x_{i+1}  ≡  ¬x_i ∨ x_{i+1}
    for i in range(1, num_vars):
        clauses.append([-i, i + 1])

    return num_vars, clauses


def generate_tseitin(num_vars: int) -> Tuple[int, List[List[int]]]:
    """Generate a Tseitin-encoded parity formula.

    Encodes XOR constraints: x1 ⊕ x2 ⊕ ... ⊕ xn = True.
    For odd number of input variables, this is UNSAT.

    Args:
        num_vars: Number of input variables.

    Returns:
        Tuple of (total_vars, clauses).
    """
    n = num_vars
    clauses = []
    total_vars = n

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
    clauses.append([prev_t])

    return total_vars, clauses


def generate_mutilated_chessboard(n: int) -> Tuple[int, List[List[int]]]:
    """Generate the mutilated chessboard problem.

    An n×n board with opposite corners removed cannot be tiled with dominos.
    UNSAT for even n.

    Args:
        n: Board size.

    Returns:
        Tuple of (total_vars, clauses).
    """
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
                clauses.append([-domino_var, cell_var[(i, j)]])
                clauses.append([-domino_var, cell_var[(i, j + 1)]])

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
                clauses.append([cell_var[(i, j)]])

            # No two dominos can overlap (at most one domino per cell)
            for a_idx in range(len(placements)):
                for b_idx in range(a_idx + 1, len(placements)):
                    clauses.append([-placements[a_idx], -placements[b_idx]])

    return total_vars, clauses


def generate_graph_coloring(
    num_nodes: int, num_colors: int, edge_prob: float = 0.5, seed: int = None
) -> Tuple[int, List[List[int]]]:
    """Generate a graph coloring SAT instance.

    Each node must be assigned exactly one color, and adjacent nodes
    must have different colors.

    Args:
        num_nodes: Number of nodes in the graph.
        num_colors: Number of available colors.
        edge_prob: Probability of an edge between any two nodes.
        seed: Random seed.

    Returns:
        Tuple of (num_vars, clauses).
    """
    if seed is not None:
        random.seed(seed)

    # Variable x_{i,c} = 1 iff node i has color c
    # Encoded as variable (i * num_colors + c + 1)
    num_vars = num_nodes * num_colors
    clauses = []

    # Each node must have at least one color
    for i in range(num_nodes):
        clause = [(i * num_colors + c + 1) for c in range(num_colors)]
        clauses.append(clause)

    # Each node has at most one color
    for i in range(num_nodes):
        for c1 in range(num_colors):
            for c2 in range(c1 + 1, num_colors):
                clauses.append(
                    [-(i * num_colors + c1 + 1), -(i * num_colors + c2 + 1)]
                )

    # Adjacent nodes must have different colors
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            if random.random() < edge_prob:
                for c in range(num_colors):
                    clauses.append(
                        [-(i * num_colors + c + 1), -(j * num_colors + c + 1)]
                    )

    return num_vars, clauses


def write_dimacs(num_vars: int, clauses: List[List[int]], filename: str = None) -> str:
    """Write DIMACS CNF format.

    Args:
        num_vars: Number of variables.
        clauses: List of clauses.
        filename: Output file path (None for stdout).

    Returns:
        The DIMACS string content.
    """
    lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        lines.append(" ".join(str(l) for l in clause) + " 0")

    content = "\n".join(lines) + "\n"

    if filename:
        with open(filename, "w") as f:
            f.write(content)

    return content


def main():
    """CLI entry point for the CNF instance generator."""
    parser = argparse.ArgumentParser(
        description="CNF Instance Generator for SAT solver benchmarking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pigeonhole principle (UNSAT)
  python -m cdcl_sat.generator --type php --n 4 --m 3 -o php_4_3.cnf

  # Random 3-SAT
  python -m cdcl_sat.generator --type random --vars 50 --clauses 200 --seed 42 -o random_50.cnf

  # Graph coloring
  python -m cdcl_sat.generator --type coloring --nodes 10 --colors 3 --seed 7 -o color_10.cnf
        """,
    )
    parser.add_argument(
        "--type",
        choices=["php", "random", "chain", "tseitin", "chessboard", "coloring"],
        required=True,
        help="Type of instance to generate",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None, help="Output file (default: stdout)"
    )

    # PHP parameters
    parser.add_argument("--n", type=int, default=4, help="Number of pigeons (PHP) or board size")
    parser.add_argument("--m", type=int, default=3, help="Number of holes (PHP)")

    # Random SAT parameters
    parser.add_argument(
        "--vars", type=int, default=50, help="Number of variables (random)"
    )
    parser.add_argument(
        "--clauses", type=int, default=200, help="Number of clauses (random)"
    )
    parser.add_argument("--k", type=int, default=3, help="Clause length (random)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")

    # Graph coloring parameters
    parser.add_argument(
        "--nodes", type=int, default=10, help="Number of nodes (coloring)"
    )
    parser.add_argument(
        "--colors", type=int, default=3, help="Number of colors (coloring)"
    )
    parser.add_argument(
        "--edge-prob", type=float, default=0.5, help="Edge probability (coloring)"
    )

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
    elif args.type == "coloring":
        num_vars, clauses = generate_graph_coloring(
            args.nodes, args.colors, args.edge_prob, args.seed
        )
    else:
        print(f"Unknown type: {args.type}", file=sys.stderr)
        sys.exit(1)

    write_dimacs(num_vars, clauses, args.output)
    if args.output:
        print(
            f"c Generated {args.type}: {num_vars} vars, {len(clauses)} clauses → {args.output}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()