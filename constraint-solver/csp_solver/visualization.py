"""
Visualization and rendering utilities for CSP Solver.

Provides ASCII/text-based visualization of solutions for various
CSP problem types, and optional rich-based visualization.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .problems import (
    AUSTRALIA_EDGES,
    US_REGIONS_EDGES,
)


# ─── Color maps for graph coloring ───────────────────────────────

COLOR_NAMES = {
    0: "Red",
    1: "Green",
    2: "Blue",
    3: "Yellow",
    4: "Purple",
    5: "Orange",
    6: "Cyan",
    7: "Pink",
    8: "Brown",
    9: "Gray",
}

COLOR_SYMBOLS = {
    0: "🟥",
    1: "🟩",
    2: "🟦",
    3: "🟨",
    4: "🟪",
    5: "🟧",
    6: "🩵",
    7: "🩷",
    8: "🟫",
    9: "⬜",
}


def render_sudoku(assignment: Dict[str, int], style: str = "box") -> str:
    """Render a Sudoku solution as an ASCII grid.

    Args:
        assignment: Variable assignment from the solver.
        style: 'box' for bordered grid, 'compact' for minimal spacing.

    Returns:
        Formatted string representation.
    """
    if style == "compact":
        lines = []
        for i in range(9):
            row = " ".join(str(assignment.get(f"R{i}C{j}", ".")) for j in range(9))
            lines.append(row)
        return "\n".join(lines)

    # Box style with separators
    lines = []
    for i in range(9):
        row = ""
        for j in range(9):
            val = assignment.get(f"R{i}C{j}", ".")
            row += f" {val} "
            if j in (2, 5):
                row += "│"
        lines.append(row.rstrip())
        if i in (2, 5):
            lines.append("─" * 21)
    return "\n".join(lines)


def render_queens(assignment: Dict[str, int], n: int = 8) -> str:
    """Render an N-Queens solution as a board.

    Uses chess Unicode characters for a nice display.

    Args:
        assignment: Variable assignment from the solver.
        n: Board size.

    Returns:
        Formatted string representation.
    """
    # Determine column labels
    col_labels = "  " + " ".join(str(j) for j in range(n))
    top_border = "  " + "─" * (2 * n - 1)

    lines = [top_border]
    for i in range(n):
        queen_col = assignment.get(f"Q{i}", -1)
        row_chars = []
        for j in range(n):
            row_chars.append("♛ " if j == queen_col else "· ")
        row = f"{i}│" + "".join(row_chars).rstrip()
        lines.append(row)
    lines.append(top_border)
    lines.append(col_labels)

    return "\n".join(lines)


def render_graph_coloring(
    assignment: Dict[str, int],
    edges: List[Tuple[str, str]],
    title: str = "Graph Coloring",
) -> str:
    """Render a graph coloring solution showing nodes and their colors.

    Args:
        assignment: Variable assignment mapping node names to color indices.
        edges: Edge list defining the graph.
        title: Title for the visualization.

    Returns:
        Formatted string representation.
    """
    lines = [f"  {title}", "  " + "=" * (len(title) + 4), ""]

    # Node colors
    lines.append("  Node assignments:")
    for node in sorted(assignment.keys()):
        color_idx = assignment[node]
        color_name = COLOR_NAMES.get(color_idx, f"Color{color_idx}")
        symbol = COLOR_SYMBOLS.get(color_idx, "●")
        lines.append(f"    {node:>3} → {color_name} {symbol}")

    # Verify constraints
    lines.append("")
    lines.append("  Constraint verification:")
    violations = 0
    for a, b in edges:
        if a in assignment and b in assignment:
            ok = assignment[a] != assignment[b]
            status = "✓" if ok else "✗"
            if not ok:
                violations += 1
            a_color = COLOR_NAMES.get(assignment[a], f"C{assignment[a]}")
            b_color = COLOR_NAMES.get(assignment[b], f"C{assignment[b]}")
            lines.append(f"    {a}({a_color}) — {b}({b_color})  {status}")

    if violations > 0:
        lines.append(f"\n  ⚠ {violations} constraint violations!")
    else:
        lines.append("\n  ✓ All constraints satisfied!")

    return "\n".join(lines)


def render_cryptarithm(
    assignment: Dict[str, int],
    words: List[str],
    result: str,
) -> str:
    """Render a cryptarithm solution in aligned arithmetic format.

    Args:
        assignment: Variable assignment mapping letters to digits.
        words: List of addend words.
        result: Result word.

    Returns:
        Formatted string representation.
    """
    def word_value(word: str) -> int:
        val = 0
        for ch in word:
            val = val * 10 + assignment[ch]
        return val

    max_len = max(len(w) for w in words + [result])
    max_num_len = len(str(word_value(result))) if assignment else 0
    width = max(max_len, max_num_len) + 2

    lines = []
    for i, word in enumerate(words):
        num = word_value(word)
        prefix = "  " if i == 0 else " +"
        lines.append(f"{prefix} {word:>{width}} = {num}")

    lines.append(f"  {'─' * width}{'─' * len(str(word_value(result)))}")
    res_num = word_value(result)
    lines.append(f"  = {result:>{width}} = {res_num}")

    total = sum(word_value(w) for w in words)
    lines.append(f"\n  Check: {' + '.join(str(word_value(w)) for w in words)} = {total}")
    lines.append(f"  Verify: {total} == {res_num} → {'✓' if total == res_num else '✗'}")

    lines.append("\n  Letter assignments:")
    for letter in sorted(assignment):
        lines.append(f"    {letter} = {assignment[letter]}")

    return "\n".join(lines)


def render_latin_square(assignment: Dict[str, int], n: int) -> str:
    """Render a Latin Square solution.

    Args:
        assignment: Variable assignment.
        n: Size of the square.

    Returns:
        Formatted string representation.
    """
    # Calculate column width based on max value
    max_val = n - 1
    width = len(str(max_val)) + 1

    lines = []
    lines.append("  ┌" + "─" * (width * n) + "┐")
    for i in range(n):
        row = "  │"
        for j in range(n):
            val = assignment.get(f"L{i}_{j}", "?")
            row += f"{val:>{width}}"
        row += " │"
        lines.append(row)
    lines.append("  └" + "─" * (width * n) + "┘")

    return "\n".join(lines)


def render_magic_square(assignment: Dict[str, int], n: int) -> str:
    """Render a Magic Square solution.

    Args:
        assignment: Variable assignment.
        n: Size of the square.

    Returns:
        Formatted string representation.
    """
    target = n * (n * n + 1) // 2
    max_val = n * n
    width = len(str(max_val)) + 1

    lines = []
    lines.append(f"  Magic Square {n}×{n}  (target sum: {target})")
    lines.append("")

    # Top border
    lines.append("  ┌" + "─" * (width * n + n - 1) + "┐")
    for i in range(n):
        row = "  │"
        for j in range(n):
            val = assignment.get(f"M{i}_{j}", "?")
            row += f"{val:>{width}}"
            if j < n - 1:
                row += " "
        row += " │"

        # Row sum annotation
        row_sum = sum(assignment.get(f"M{i}_{j}", 0) for j in range(n))
        check = "✓" if row_sum == target else "✗"
        lines.append(f"{row}  = {row_sum} {check}")

    lines.append("  └" + "─" * (width * n + n - 1) + "┘")

    # Column sums
    col_sums = []
    for j in range(n):
        cs = sum(assignment.get(f"M{i}_{j}", 0) for i in range(n))
        col_sums.append(cs)
    lines.append(f"  Col sums: {', '.join(str(s) for s in col_sums)}")

    # Diagonal sums
    d1 = sum(assignment.get(f"M{i}_{i}", 0) for i in range(n))
    d2 = sum(assignment.get(f"M{i}_{n-1-i}", 0) for i in range(n))
    lines.append(f"  Diagonals: {d1}, {d2}")

    return "\n".join(lines)


def render_search_tree(
    steps: List[Dict[str, int]],
    max_depth: int = 10,
) -> str:
    """Render a simplified view of the search tree progression.

    Args:
        steps: List of assignment dictionaries from progress tracking.
        max_depth: Maximum depth to display.

    Returns:
        Formatted string representation of search progression.
    """
    if not steps:
        return "  (no steps recorded)"

    lines = []
    lines.append(f"  Search progression ({len(steps)} steps):")
    lines.append(f"  Max depth reached: {max(len(s) for s in steps) if steps else 0}")

    # Show depth histogram
    depth_counts: Dict[int, int] = {}
    for step in steps:
        depth = len(step)
        depth_counts[depth] = depth_counts.get(depth, 0) + 1

    lines.append("  Depth distribution:")
    for depth in sorted(depth_counts.keys()):
        count = depth_counts[depth]
        bar = "█" * min(count // max(1, len(steps) // 40), 40)
        lines.append(f"    {depth:3d}: {count:6d} {bar}")

    return "\n".join(lines)