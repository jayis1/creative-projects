"""
Example: Solving Sudoku puzzles with the CSP Solver.

Demonstrates:
- Creating a Sudoku CSP from a grid
- Solving with different strategies
- Using pretty rendering
- Generating random puzzles
"""

from csp_solver import (
    CSPSolver,
    sudoku_csp,
    generate_sudoku,
    format_sudoku_solution,
    render_sudoku,
    compare_strategies,
)


def main():
    # Classic Sudoku puzzle (AI Escargot - one of the hardest known)
    grid = [
        [1, 0, 0, 0, 0, 7, 0, 9, 0],
        [0, 3, 0, 0, 2, 0, 0, 0, 8],
        [0, 0, 9, 6, 0, 0, 5, 0, 0],
        [0, 0, 5, 3, 0, 0, 9, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 2],
        [6, 0, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 4, 0, 0, 0, 2, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    print("=" * 60)
    print("Sudoku Solver Example")
    print("=" * 60)

    # Create CSP from grid
    csp = sudoku_csp(grid)

    print(f"\nCSP has {len(csp.variables)} variables and {len(csp.constraints)} constraints")

    # Solve with MAC (most powerful)
    solver = CSPSolver(use_mac=True)
    result = solver.solve(csp)

    if result.is_satisfiable:
        print("\n✓ Solution found!")
        print(f"  Method: {result.method}")
        print(f"  Time: {result.stats.elapsed:.4f}s")
        print(f"  Assignments: {result.stats.assignments_tried}")
        print(f"  Backtracks: {result.stats.backtracks}")

        print("\nCompact format:")
        print(format_sudoku_solution(result.assignment))

        print("\nBox format:")
        print(render_sudoku(result.assignment))
    else:
        print("\n✗ No solution found")

    # Compare strategies
    print("\n" + "=" * 60)
    print("Strategy Comparison on Easy Sudoku")
    print("=" * 60)

    easy_grid = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]

    easy_csp = sudoku_csp(easy_grid)
    results = compare_strategies(easy_csp, timeout=30)

    print(f"\n{'Strategy':<25} {'Time':>10} {'Assignments':>12} {'Backtracks':>12}")
    print("-" * 62)
    for r in results:
        t = f"{r['time'][0]:.4f}s" if r['time'] else "N/A"
        a = str(r['assignments']) if r['assignments'] else "N/A"
        b = str(r['backtracks']) if r['backtracks'] else "N/A"
        print(f"{r['strategy']:<25} {t:>10} {a:>12} {b:>12}")

    # Generate a random Sudoku
    print("\n" + "=" * 60)
    print("Random Sudoku Generation")
    print("=" * 60)

    puzzle, solution = generate_sudoku(difficulty="hard", seed=42)
    blanks = sum(1 for i in range(9) for j in range(9) if puzzle[i][j] == 0)
    print(f"\nGenerated hard Sudoku with {blanks} blank cells")


if __name__ == "__main__":
    main()