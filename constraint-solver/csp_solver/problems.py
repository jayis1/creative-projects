"""
Built-in problem generators for common CSP problems.

Includes:
- Sudoku (9x9)
- N-Queens
- Graph Coloring
- Cryptarithm (SEND+MORE=MONEY, etc.)
- Latin Square
- Magic Square
- Map Coloring (Australia, USA regions)
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .csp import CSP, Variable, Constraint


# ─── Sudoku ────────────────────────────────────────────────────────

def sudoku_csp(grid: Optional[List[List[int]]] = None) -> CSP:
    """Create a CSP for a 9x9 Sudoku puzzle.

    Each cell is a variable R{i}C{j} with domain {1..9}.
    Constraints enforce that each row, column, and 3x3 box
    contains all different values.

    Args:
        grid: Optional 9x9 grid where 0 represents empty cells.
              Row-major order: grid[row][col].
              If None, creates an empty puzzle.

    Returns:
        A CSP whose solution is the completed Sudoku grid.

    Raises:
        ValueError: If grid is not 9x9.
    """
    if grid is None:
        grid = [[0] * 9 for _ in range(9)]
    elif len(grid) != 9 or any(len(row) != 9 for row in grid):
        raise ValueError("Grid must be 9x9")

    # Validate grid values
    for i in range(9):
        for j in range(9):
            val = grid[i][j]
            if val < 0 or val > 9:
                raise ValueError(f"Invalid grid value {val} at ({i},{j})")

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
            name=f"{var_i}≠{var_j}",
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


def generate_sudoku(
    difficulty: str = "medium",
    seed: Optional[int] = None,
) -> Tuple[List[List[int]], List[List[int]]]:
    """Generate a random Sudoku puzzle and its solution.

    Args:
        difficulty: "easy" (30-35 blanks), "medium" (36-45 blanks),
                   "hard" (46-52 blanks).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (puzzle_grid, solution_grid).
    """
    if seed is not None:
        random.seed(seed)

    # Solve an empty Sudoku to get a complete grid
    empty_csp = sudoku_csp()
    from .solver import CSPSolver  # noqa: avoid circular import at module level
    solver = CSPSolver(use_mac=True)
    result = solver.solve(empty_csp)

    if result.assignment is None:
        # Should never happen with an empty grid
        raise RuntimeError("Failed to generate base Sudoku solution")

    # Build solution grid
    solution = [[0] * 9 for _ in range(9)]
    for i in range(9):
        for j in range(9):
            solution[i][j] = result.assignment[f"R{i}C{j}"]

    # Determine number of blanks
    if difficulty == "easy":
        n_blanks = random.randint(30, 35)
    elif difficulty == "medium":
        n_blanks = random.randint(36, 45)
    elif difficulty == "hard":
        n_blanks = random.randint(46, 52)
    else:
        raise ValueError(f"Unknown difficulty: {difficulty}")

    # Remove cells randomly
    puzzle = [row[:] for row in solution]
    cells = [(i, j) for i in range(9) for j in range(9)]
    random.shuffle(cells)
    for k in range(min(n_blanks, 64)):
        i, j = cells[k]
        puzzle[i][j] = 0

    return puzzle, solution


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

    Uses the standard row-indexed encoding where variable Qi represents
    the column position of the queen in row i. This reduces the search
    space from N^(N×N) to N^N, since the row constraint is implicit.

    Constraints:
    - No two queens share the same column (Qi ≠ Qj)
    - No two queens share the same diagonal (|Qi - Qj| ≠ |i - j|)

    Args:
        n: Board size (default 8 for the classic 8-Queens).

    Returns:
        A CSP for the N-Queens problem.

    Raises:
        ValueError: If n < 1.
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
                name=f"{queens[i]}≠{queens[j]}",
            ))
            # Different diagonals
            csp.add_constraint(Constraint(
                (queens[i], queens[j]),
                lambda a, qi=queens[i], qj=queens[j], ri=i, rj=j: abs(a[qi] - a[qj]) != abs(ri - rj),
                pair_check=lambda x, y, ri=i, rj=j: abs(x - y) != abs(ri - rj),
                name=f"{queens[i]}≁{queens[j]}(diag)",
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


def count_n_queens_solutions(n: int, timeout: float = 60.0) -> int:
    """Count all solutions to the N-Queens problem.

    Args:
        n: Board size.
        timeout: Maximum time in seconds.

    Returns:
        Number of distinct solutions.
    """
    csp = n_queens_csp(n)
    from .solver import CSPSolver  # noqa: avoid circular import at module level
    solver = CSPSolver(use_mac=True, preprocess_ac3=True, timeout=timeout)
    solutions = solver.solve_all(csp, max_solutions=100000)
    return len(solutions)


# ─── Graph Coloring ────────────────────────────────────────────────

# Pre-defined maps
AUSTRALIA_EDGES = [
    ("WA", "NT"), ("WA", "SA"), ("NT", "SA"),
    ("NT", "Q"), ("SA", "Q"), ("SA", "NSW"),
    ("SA", "V"), ("Q", "NSW"), ("NSW", "V"),
]

# US map: contiguous 48 states (simplified adjacency)
US_REGIONS_EDGES = [
    # West
    ("WA", "OR"), ("OR", "CA"), ("OR", "NV"), ("OR", "ID"),
    ("CA", "NV"), ("CA", "AZ"),
    ("NV", "AZ"), ("NV", "UT"), ("NV", "ID"),
    ("ID", "UT"), ("ID", "MT"), ("ID", "WY"), ("ID", "NV"),
    ("MT", "ND"), ("MT", "WY"), ("MT", "SD"),
    ("WY", "SD"), ("WY", "NE"), ("WY", "CO"), ("WY", "UT"),
    ("UT", "CO"), ("UT", "AZ"), ("UT", "NM"),
    ("CO", "NM"), ("CO", "OK"), ("CO", "KS"), ("CO", "NE"),
    ("AZ", "NM"),
    # Central
    ("ND", "SD"), ("ND", "MN"),
    ("SD", "MN"), ("SD", "IA"), ("SD", "NE"),
    ("NE", "IA"), ("NE", "MO"), ("NE", "KS"),
    ("KS", "MO"), ("KS", "OK"),
    ("OK", "TX"), ("OK", "NM"), ("OK", "AR"), ("OK", "MO"),
    ("TX", "NM"), ("TX", "AR"), ("TX", "LA"),
    ("MN", "IA"), ("MN", "WI"),
    ("IA", "WI"), ("IA", "IL"), ("IA", "MO"),
    ("MO", "AR"), ("MO", "IL"), ("MO", "TN"), ("MO", "KY"),
    ("AR", "LA"), ("AR", "MS"), ("AR", "TN"),
    ("LA", "MS"),
    # East
    ("WI", "IL"), ("WI", "MI"),
    ("IL", "IN"), ("IL", "KY"),
    ("IN", "OH"), ("IN", "KY"), ("IN", "MI"),
    ("MI", "OH"),
    ("OH", "PA"), ("OH", "WV"), ("OH", "KY"),
    ("PA", "NY"), ("PA", "NJ"), ("PA", "DE"), ("PA", "MD"), ("PA", "WV"),
    ("NY", "NJ"), ("NY", "CT"), ("NY", "MA"), ("NY", "VT"), ("NY", "PA"),
    ("NJ", "DE"),
    ("DE", "MD"),
    ("MD", "WV"), ("MD", "VA"), ("MD", "DC"),
    ("CT", "MA"), ("CT", "RI"),
    ("RI", "MA"),
    ("MA", "VT"), ("MA", "NH"),
    ("VT", "NH"),
    ("NH", "ME"),
    ("WV", "VA"), ("WV", "KY"),
    ("VA", "KY"), ("VA", "TN"), ("VA", "NC"), ("VA", "DC"),
    ("NC", "TN"), ("NC", "SC"), ("NC", "GA"),
    ("SC", "GA"),
    ("GA", "FL"), ("GA", "AL"), ("GA", "TN"),
    ("FL", "AL"),
    ("AL", "MS"), ("AL", "TN"),
    ("MS", "TN"),
    ("KY", "TN"),
    ("ME", "NH"),
]


def graph_coloring_csp(
    edges: List[Tuple[str, str]],
    num_colors: int = 3,
) -> CSP:
    """Create a CSP for graph coloring.

    Given a graph defined by edges, find an assignment of colors
    to nodes such that no two adjacent nodes share a color.

    Args:
        edges: List of (node1, node2) pairs defining the graph.
        num_colors: Number of available colors (default 3).

    Returns:
        A CSP whose solution is a valid coloring.

    Raises:
        ValueError: If num_colors < 1.
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
            name=f"{a}≠{b}",
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

    Raises:
        ValueError: If more than 10 unique letters (impossible in base-10)
            or if any word is empty.
    """
    # Validate inputs
    if not words:
        raise ValueError("At least one word is required")
    if not result:
        raise ValueError("Result word is required")
    for word in words:
        if not word:
            raise ValueError("All words must be non-empty")

    # Collect all unique letters
    letters_set = set()
    leading_letters = set()

    for word in words + [result]:
        for i, ch in enumerate(word):
            if not ch.isalpha():
                raise ValueError(f"Invalid character {ch!r} in word {word!r}")
            letters_set.add(ch)
            if i == 0 and len(word) > 1:
                leading_letters.add(ch)

    letters = sorted(letters_set)
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
                name=f"{letters[i]}≠{letters[j]}",
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

    csp.add_constraint(Constraint(all_vars, arithmetic_check, name="arithmetic"))

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
    max_word_len = max(len(w) for w in words + [result])
    for word in words:
        num = word_value(word)
        lines.append(f"  {word:>{max_word_len}} = {num}")
    lines.append(f"  {'+' * max_word_len}")
    res_num = word_value(result)
    lines.append(f"  {result:>{max_word_len}} = {res_num}")
    total = sum(word_value(w) for w in words)
    lines.append(f"  Check: {total} == {res_num} → {total == res_num}")
    lines.append("")
    for letter in sorted(assignment):
        lines.append(f"  {letter} = {assignment[letter]}")
    return "\n".join(lines)


# ─── Latin Square ──────────────────────────────────────────────────

def latin_square_csp(n: int = 4) -> CSP:
    """Create a CSP for an n×n Latin Square.

    A Latin Square is an n×n grid filled with n different symbols,
    each occurring exactly once in each row and column.

    Args:
        n: Size of the square (default 4).

    Returns:
        A CSP whose solution is a valid Latin Square.

    Raises:
        ValueError: If n < 1.
    """
    if n < 1:
        raise ValueError("n must be at least 1")

    csp = CSP()

    # Variables: L{i}_{j} for each cell, domain {0, ..., n-1}
    for i in range(n):
        for j in range(n):
            csp.add_variable(Variable(f"L{i}_{j}", domain=set(range(n))))

    # Row constraints: all different in each row
    for i in range(n):
        row_vars = [f"L{i}_{j}" for j in range(n)]
        for j1 in range(n):
            for j2 in range(j1 + 1, n):
                csp.add_constraint(Constraint(
                    (row_vars[j1], row_vars[j2]),
                    lambda a, v1=row_vars[j1], v2=row_vars[j2]: a[v1] != a[v2],
                    pair_check=lambda x, y: x != y,
                ))

    # Column constraints: all different in each column
    for j in range(n):
        col_vars = [f"L{i}_{j}" for i in range(n)]
        for i1 in range(n):
            for i2 in range(i1 + 1, n):
                csp.add_constraint(Constraint(
                    (col_vars[i1], col_vars[i2]),
                    lambda a, v1=col_vars[i1], v2=col_vars[i2]: a[v1] != a[v2],
                    pair_check=lambda x, y: x != y,
                ))

    return csp


def format_latin_square(assignment: Dict[str, int], n: int) -> str:
    """Format a Latin Square solution."""
    lines = []
    for i in range(n):
        row = " ".join(str(assignment[f"L{i}_{j}"]) for j in range(n))
        lines.append(row)
    return "\n".join(lines)


# ─── Magic Square ──────────────────────────────────────────────────

def magic_square_csp(n: int = 3) -> CSP:
    """Create a CSP for an n×n Magic Square.

    A Magic Square has all numbers 1..n² placed so each row, column,
    and main diagonal sums to the same target (n(n²+1)/2).

    Args:
        n: Size of the square (default 3 for 3×3).

    Returns:
        A CSP whose solution is a valid Magic Square.

    Raises:
        ValueError: If n < 1.
    """
    if n < 1:
        raise ValueError("n must be at least 1")

    target_sum = n * (n * n + 1) // 2
    nums = set(range(1, n * n + 1))

    csp = CSP()

    # Variables: M{i}_{j} for each cell
    for i in range(n):
        for j in range(n):
            csp.add_variable(Variable(f"M{i}_{j}", domain=set(nums)))

    # All-different constraint (each number used exactly once)
    var_names = [f"M{i}_{j}" for i in range(n) for j in range(n)]
    for i in range(len(var_names)):
        for j in range(i + 1, len(var_names)):
            csp.add_constraint(Constraint(
                (var_names[i], var_names[j]),
                lambda a, v1=var_names[i], v2=var_names[j]: a[v1] != a[v2],
                pair_check=lambda x, y: x != y,
            ))

    # Row sum constraints
    for i in range(n):
        row_vars = [f"M{i}_{j}" for j in range(n)]
        csp.add_constraint(Constraint(
            row_vars,
            lambda a, rv=row_vars, t=target_sum: sum(a[v] for v in rv) == t,
            name=f"row{i}_sum",
        ))

    # Column sum constraints
    for j in range(n):
        col_vars = [f"M{i}_{j}" for i in range(n)]
        csp.add_constraint(Constraint(
            col_vars,
            lambda a, cv=col_vars, t=target_sum: sum(a[v] for v in cv) == t,
            name=f"col{j}_sum",
        ))

    # Diagonal sum constraints
    diag1 = [f"M{i}_{i}" for i in range(n)]
    csp.add_constraint(Constraint(
        diag1,
        lambda a, d=diag1, t=target_sum: sum(a[v] for v in d) == t,
        name="diag1_sum",
    ))

    diag2 = [f"M{i}_{n-1-i}" for i in range(n)]
    csp.add_constraint(Constraint(
        diag2,
        lambda a, d=diag2, t=target_sum: sum(a[v] for v in d) == t,
        name="diag2_sum",
    ))

    return csp


def format_magic_square(assignment: Dict[str, int], n: int) -> str:
    """Format a Magic Square solution."""
    target_sum = n * (n * n + 1) // 2
    lines = []
    for i in range(n):
        row = " ".join(f"{assignment[f'M{i}_{j}']:3d}" for j in range(n))
        lines.append(f"| {row} |")
    lines.append(f"Target sum: {target_sum}")
    return "\n".join(lines)