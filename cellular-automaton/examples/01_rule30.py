"""Example: Wolfram's Rule 30 — chaotic pattern from a single seed cell."""

from cellular_automaton import CellularAutomaton, ElementaryRule, render_ascii


def main():
    ca = CellularAutomaton(ElementaryRule(30), width=61)
    ca.center_seed()
    for _ in range(30):
        line = render_ascii(ca.grid, on_char="█", off_char=" ")
        print(line)
        ca.step()


if __name__ == "__main__":
    main()