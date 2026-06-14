"""
Example: Solving N-Queens and analyzing solver behavior.

Demonstrates:
- Solving N-Queens for various board sizes
- Finding all solutions
- Using progress callbacks
- Comparing strategies
"""

from csp_solver import (
    CSPSolver,
    n_queens_csp,
    count_n_queens_solutions,
    format_queens_solution,
    render_queens,
    SolverProgress,
)


def main():
    print("=" * 60)
    print("N-Queens Solver Example")
    print("=" * 60)

    # Solve 8-Queens
    print("\n--- 8-Queens ---")
    csp = n_queens_csp(8)
    solver = CSPSolver(use_mac=True)
    result = solver.solve(csp)

    if result.is_satisfiable:
        print(f"✓ Solution found using {result.method}")
        print(f"  Time: {result.stats.elapsed:.4f}s")
        print(f"  Assignments: {result.stats.assignments_tried}")
        print(f"  Backtracks: {result.stats.backtracks}")
        print()
        print(format_queens_solution(result.assignment, 8))
        print()
        print(render_queens(result.assignment, 8))

    # Count all solutions for small N
    print("\n--- Counting solutions ---")
    for n in range(4, 9):
        count = count_n_queens_solutions(n, timeout=30)
        print(f"  N={n}: {count} solutions")

    # Progress tracking
    print("\n--- Progress tracking (10-Queens) ---")
    csp10 = n_queens_csp(10)
    progress = SolverProgress(log_interval=500)
    progress.start(csp10)
    solver_with_progress = CSPSolver(use_mac=True)
    bt_solver = solver_with_progress._method_string()

    # Use BacktrackingSolver directly with callback
    from csp_solver import BacktrackingSolver
    bt = BacktrackingSolver(use_mrv=True, use_degree=True, use_lcv=True,
                            use_mac=True, progress_callback=progress.callback)
    bt.solve(csp10)

    summary = progress.summary()
    print(f"  Total steps: {summary['total_steps']}")
    print(f"  Max depth: {summary['max_depth']}")
    print(f"  Total time: {summary['total_time']:.4f}s")


if __name__ == "__main__":
    main()