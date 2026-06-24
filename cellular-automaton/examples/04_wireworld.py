"""Example: Wireworld — a simulated electronic circuit.

Wireworld models current flow through conductors. This example sets up a
simple diode circuit and steps through it.

States: 0=empty, 1=electron head (red), 2=electron tail (orange), 3=conductor (blue).
"""
from cellular_automaton import CellularAutomaton, WireworldRule


def main():
    rule = WireworldRule()
    ca = CellularAutomaton(rule, width=40, height=10, boundary="zero")

    # Build a simple wire: a row of conductors with an electron head and tail.
    for x in range(5, 35):
        ca.set_cell(x, 5, 3)  # conductor
    ca.set_cell(8, 5, 1)     # electron head
    ca.set_cell(7, 5, 2)     # electron tail

    print("Wireworld — electron flowing through a wire:\n")
    for i in range(20):
        # Render with state characters.
        row = ca.grid[5]
        chars = {0: ".", 1: "H", 2: "T", 3: "#"}
        line = "".join(chars.get(int(c), "?") for c in row)
        print(f"  Step {i:2d}: {line}")
        ca.step()


if __name__ == "__main__":
    main()