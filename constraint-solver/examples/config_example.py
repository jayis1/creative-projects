"""
Example: Configuration file usage and progress tracking.

Demonstrates:
- Creating and using solver configuration files
- Progress tracking with callbacks
- JSON export of solutions
"""

from csp_solver import (
    CSPSolver,
    SolverConfig,
    SolverProgress,
    n_queens_csp,
    save_solution,
    export_csp,
    setup_logging,
)


def main():
    print("=" * 60)
    print("Configuration and Progress Tracking Example")
    print("=" * 60)

    # Create a config from defaults
    config = SolverConfig(
        use_mrv=True,
        use_degree=True,
        use_lcv=True,
        use_mac=True,
        preprocess_ac3=True,
        timeout=30.0,
    )

    print("\n--- Default Config ---")
    print(f"  use_mrv: {config.use_mrv}")
    print(f"  use_mac: {config.use_mac}")
    print(f"  timeout: {config.timeout}")

    # Save config to file
    config.to_file("/tmp/csp_config.json")
    print("\n  Config saved to /tmp/csp_config.json")

    # Load config from file
    loaded_config = SolverConfig.from_file("/tmp/csp_config.json")
    print(f"  Loaded config timeout: {loaded_config.timeout}")

    # Create solver from config
    solver = loaded_config.create_solver()

    # Setup logging
    setup_logging("INFO")

    # Solve with progress tracking
    print("\n--- Solving 8-Queens with Progress Tracking ---")
    csp = n_queens_csp(8)
    progress = SolverProgress(log_interval=100)
    progress.start(csp)

    from csp_solver import BacktrackingSolver
    bt = BacktrackingSolver(
        use_mrv=True,
        use_degree=True,
        use_lcv=True,
        use_mac=True,
        progress_callback=progress.callback,
    )
    result = bt.solve(csp)

    if result:
        print(f"  ✓ Solution found")
        print(f"  Steps tracked: {progress.total_steps}")
        summary = progress.summary()
        print(f"  Max depth: {summary['max_depth']}")
        print(f"  Time: {summary['total_time']:.4f}s")

    # Export CSP definition
    export_data = export_csp(csp)
    print(f"\n--- CSP Export ---")
    print(f"  Variables: {export_data['num_variables']}")
    print(f"  Constraints: {export_data['num_constraints']}")

    # Save solution
    if result:
        save_solution(result, "/tmp/queens_solution.json", method="MAC+MRV+DEG+LCV")
        print(f"  Solution saved to /tmp/queens_solution.json")


if __name__ == "__main__":
    main()