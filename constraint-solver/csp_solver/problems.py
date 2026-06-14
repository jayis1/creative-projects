"""
Built-in problem generators for common CSP problems.

Includes:
- Sudoku (9x9)
- N-Queens
- Graph Coloring
- Cryptarithm ( SEND+MORE=MONEY, etc.)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .csp import CSP, Variable, Constraint


# ─── Sudoku ────────────────────────────────────────────────────────

def sudoku_csp(grid: Optional[List[List[int]]] = None) -> CSP:
    """Create a CSP for a 9x9 Sudoku puzzle.

    Args:
        grid: Optional 9x9 grid where 0 represents empty cells.
              Row-major order: grid[row][col].
              If None, creates an empty puzzle.

    Returns:
        A CSP whose solution is the completed Sudoku grid.
    """
    if grid is None:
        grid = [[0] * 9 for _ in range(9)]
    elif len(grid) != 9 or any(len(row) != 9 for row in grid):
        raise ValueError("Grid must be 9x9")

    csp = CSP()

    # Create variables: R{i}C{j} for each cell
    for i in range(9):
        for j in range(9):
            var_name = f"R{i}C{j}"
            if grid[i][j] != 0:
                # Pre-filled cell: domain is the given value
                var = Variable(var_name, domain={grid[i][j]})
            else:
                var = Variable(var_name, domain=set(range(1, 10)))
            csp.add_variable(var)

    def ne_constraint(var_i: str, var_j: str) -> Constraint:
        """Create a not-equal constraint between two variables."""
        return Constraint(
            (var_i, var_j),
            lambda a, vi=var_i, vj=var_j: a[vi] != a[vj],
            pair_check=lambda x, y: x != y,
        )

    # Row constraints
    for i in range(9):
        row_vars = [f"R{i}C{j}" for j in range(9)]
        for j1 in range(9):
            for j2 in range(j1 + 1, 9):
                csp.add_constraint(ne_constraint(row_vars[j1], row_vars[j2]))

    # Column constraints
    for j in range(9):
        col_vars = [f"R{i}C{j}" for i in range(9)]
        for i1 in range(9):
            for i2 in range(i1 + 1, 9):
                csp.add_constraint(ne_constraint(col_vars[i1], col_vars[i2]))

    # 3x3 box constraints
    for box_r in range(3):
        for box_c in range(3):
            box_vars = []
            for dr in range(3):
                for dc in range(3):
                    r = box_r * 3 + dr
                    c = box_c * 3 + dc
                    box_vars.append(f"R{r}C{c}")
            for idx1 in range(len(box_vars)):
                for idx2 in range(idx1 + 1, len(box_vars)):
                    csp.add_constraint(ne_constraint(box_vars[idx1], box_vars[idx2]))

    return csp


def format_sudoku_solution(assignment: Dict[str, int]) -> str:
    """Format a Sudoku solution as a readable grid."""
    lines = []
    for i in range(9):
        row = ""
        for j in range(9):
            val = assignment.get(f"R{i}C{j}", ".")
            row += f"{val} "
            if j in (2, 5):
                row += "| "
        lines.append(row.strip())
        if i in (2, 5):
            lines.append("-" * 21)
    return "\n".join(lines)


# ─── N-Queens ──────────────────────────────────────────────────────

def n_queens_csp(n: int = 8) -> CSP:
    """Create a CSP for the N-Queens problem.

    Variables: Q0...Q(N-1), each representing the column position
    of the queen in that row. This uses the standard row-indexed
    encoding where Qi = j means a queen is at (row=i, col=j).

    Args:
        n: Board size (default 8).

    Returns:
        A CSP for the N-Queens problem.
    """
    if n < 1:
        raise ValueError("N must be at least 1")

    csp = CSP()
    queens = [f"Q{i}" for i in range(n)]

    # Each queen has a domain of columns 0..n-1
    for i in range(n):
        csp.add_variable(Variable(queens[i], domain=set(range(n))))

    # Constraints: no two queens attack each other
    for i in range(n):
        for j in range(i + 1, n):
            # Different columns
            csp.add_constraint(Constraint(
                (queens[i], queens[j]),
                lambda a, qi=queens[i], qj=queens[j]: a[qi] != a[qj],
                pair_check=lambda x, y: x != y,
            ))
            # Different diagonals
            csp.add_constraint(Constraint(
                (queens[i], queens[j]),
                lambda a, qi=queens[i], qj=queens[j], ri=i, rj=j: abs(a[qi] - a[qj]) != abs(ri - rj),
                pair_check=lambda x, y, ri=i, rj=j: abs(x - y) != abs(ri - rj),
            ))

    return csp


def format_queens_solution(assignment: Dict[str, int], n: int = 8) -> str:
    """Format an N-Queens solution as a board."""
    lines = []
    for i in range(n):
        queen_col = assignment.get(f"Q{i}", -1)
        row = ""
        for j in range(n):
            row += "♛ " if j == queen_col else "· "
        lines.append(row.strip())
    return "\n".join(lines)


# ─── Graph Coloring ────────────────────────────────────────────────

def graph_coloring_csp(
    edges: List[Tuple[str, str]],
    num_colors: int = 3,
) -> CSP:
    """Create a CSP for graph coloring.

    Args:
        edges: List of (node1, node2) pairs defining the graph.
        num_colors: Number of available colors (default 3).

    Returns:
        A CSP whose solution is a valid coloring.
    """
    if num_colors < 1:
        raise ValueError("num_colors must be at least 1")

    csp = CSP()
    colors = set(range(num_colors))

    # Collect all unique nodes
    nodes = set()
    for a, b in edges:
        nodes.add(a)
        nodes.add(b)

    # Create variables
    for node in sorted(nodes):
        csp.add_variable(Variable(node, domain=colors))

    # Add constraints: adjacent nodes must have different colors
    for a, b in edges:
        csp.add_constraint(Constraint(
            (a, b),
            lambda assign, na=a, nb=b: assign[na] != assign[nb],
            pair_check=lambda x, y: x != y,
        ))

    return csp


# ─── Cryptarithm ───────────────────────────────────────────────────

def cryptarithm_csp(
    words: List[str],
    result: str,
) -> CSP:
    """Create a CSP for a cryptarithm puzzle.

    Each letter maps to a digit 0-9, and the arithmetic equation
    must hold. Leading letters cannot be zero.

    Example: cryptarithm_csp(["SEND", "MORE"], "MONEY")
    represents SEND + MORE = MONEY.

    Args:
        words: List of addend words.
        result: The result word (right side of equation).

    Returns:
        A CSP whose solution maps each letter to a digit.
    """
    # Collect all unique letters
    letters = set()
    leading_letters = set()

    for word in words + [result]:
        for i, ch in enumerate(word):
            letters.add(ch)
            if i == 0 and len(word) > 1:
                leading_letters.add(ch)

    letters = sorted(letters)
    if len(letters) > 10:
        raise ValueError(
            f"Too many unique letters ({len(letters)}); "
            f"max 10 for base-10 digits"
        )

    csp = CSP()

    # Variables: one per letter, domain 0-9
    for letter in letters:
        if letter in leading_letters:
            domain = set(range(1, 10))  # No leading zeros
        else:
            domain = set(range(10))
        csp.add_variable(Variable(letter, domain=domain))

    # All-different constraint
    for i in range(len(letters)):
        for j in range(i + 1, len(letters)):
            csp.add_constraint(Constraint(
                (letters[i], letters[j]),
                lambda a, li=letters[i], lj=letters[j]: a[li] != a[lj],
                pair_check=lambda x, y: x != y,
            ))

    # Arithmetic constraint: sum(words) == result
    all_vars = letters  # all letters involved

    def arithmetic_check(assign: Dict) -> bool:
        """Verify the arithmetic equation holds."""
        def word_value(word: str) -> int:
            val = 0
            for ch in word:
                val = val * 10 + assign[ch]
            return val

        total = sum(word_value(w) for w in words)
        return total == word_value(result)

    csp.add_constraint(Constraint(all_vars, arithmetic_check))

    return csp


def format_cryptarithm_solution(
    assignment: Dict[str, int],
    words: List[str],
    result: str,
) -> str:
    """Format a cryptarithm solution."""
    def word_value(word: str) -> int:
        val = 0
        for ch in word:
            val = val * 10 + assignment[ch]
        return val

    lines = []
    for word in words:
        lines.append(f"  {word} = {word_value(word)}")
    total = sum(word_value(w) for w in words)
    lines.append(f"  {'+' * max(len(w) for w in words)}")
    lines.append(f"  {result} = {word_value(result)}")
    lines.append(f"  Check: {total} == {word_value(result)} → {total == word_value(result)}")
    lines.append("")
    for letter in sorted(assignment):
        lines.append(f"  {letter} = {assignment[letter]}")
    return "\n".join(lines)