"""
Example: Graph coloring and cryptarithm puzzles.

Demonstrates:
- Australia and US map coloring
- Cryptarithm solving
- Pretty rendering of results
"""

from csp_solver import (
    CSPSolver,
    graph_coloring_csp,
    cryptarithm_csp,
    format_cryptarithm_solution,
    render_graph_coloring,
    render_cryptarithm,
    AUSTRALIA_EDGES,
    US_REGIONS_EDGES,
)


def main():
    print("=" * 60)
    print("Graph Coloring Example")
    print("=" * 60)

    # Australia map coloring with 3 colors
    print("\n--- Australia Map (3 colors) ---")
    csp = graph_coloring_csp(AUSTRALIA_EDGES, num_colors=3)
    solver = CSPSolver(use_mac=True)
    result = solver.solve(csp)

    if result.is_satisfiable:
        print(f"✓ Solution found: {result.method}")
        print(render_graph_coloring(result.assignment, AUSTRALIA_EDGES, "Australia"))
    else:
        print("✗ No solution found")

    # US regions coloring with 4 colors
    print("\n--- US Regions (4 colors) ---")
    csp = graph_coloring_csp(US_REGIONS_EDGES, num_colors=4)
    result = solver.solve(csp)

    if result.is_satisfiable:
        print(f"✓ Solution found: {result.method}")
        # Show just the first 15 nodes
        print(f"  Found colors for {len(result.assignment)} regions")
        for i, (node, color) in enumerate(sorted(result.assignment.items())):
            if i >= 10:
                print(f"  ... and {len(result.assignment) - 10} more")
                break
            from csp_solver.visualization import COLOR_NAMES
            print(f"    {node:>3} → {COLOR_NAMES.get(color, f'Color{color}')}")

    # Cryptarithm: SEND + MORE = MONEY
    print("\n" + "=" * 60)
    print("Cryptarithm Example")
    print("=" * 60)

    print("\n--- SEND + MORE = MONEY ---")
    csp = cryptarithm_csp(["SEND", "MORE"], "MONEY")
    result = solver.solve(csp)

    if result.is_satisfiable:
        print(f"✓ Solution found: {result.method}")
        print(render_cryptarithm(result.assignment, ["SEND", "MORE"], "MONEY"))
    else:
        print("✗ No solution found")

    # Another cryptarithm: TWO + TWO = FOUR
    print("\n--- TWO + TWO = FOUR ---")
    csp = cryptarithm_csp(["TWO", "TWO"], "FOUR")
    result = solver.solve(csp)

    if result.is_satisfiable:
        print(f"✓ Solution found: {result.method}")
        print(render_cryptarithm(result.assignment, ["TWO", "TWO"], "FOUR"))
    else:
        print("✗ No solution found")


if __name__ == "__main__":
    main()