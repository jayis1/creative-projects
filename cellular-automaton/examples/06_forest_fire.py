"""Example: Forest Fire — an ecological CA model.

The forest fire CA simulates trees growing, catching fire (from neighbours
or spontaneously), and burning out. The parameters p (ignition probability)
and g (growth probability) control the dynamics.

States: 0=empty (brown), 1=tree (green), 2=burning (red).
"""
from cellular_automaton import CellularAutomaton, ForestFireRule


def main():
    import numpy as np

    rule = ForestFireRule(p=0.001, g=0.05)
    ca = CellularAutomaton(rule, width=50, height=25, boundary="zero")
    ca.set_rng(seed=42)
    ca.randomize(0.3, seed=42)

    print("Forest Fire Simulation (p=0.001, g=0.05)\n")

    for i in range(30):
        trees = int(np.sum(ca.grid == 1))
        burning = int(np.sum(ca.grid == 2))
        empty = int(np.sum(ca.grid == 0))
        print(f"  Step {i:2d}: {empty:4d} empty, {trees:4d} trees, {burning:3d} burning")
        ca.step()

    # Render final state.
    chars = {0: ".", 1: "T", 2: "F"}
    print("\nFinal state:")
    for row in ca.grid:
        print("  " + "".join(chars.get(int(c), "?") for c in row))


if __name__ == "__main__":
    main()