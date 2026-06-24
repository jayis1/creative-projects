"""Example: HighLife (B36/S23) — known for its replicator pattern."""

from cellular_automaton import CellularAutomaton, get_rule, render_ascii


def main():
    # HighLife supports a famous replicator pattern that copies itself.
    rule = get_rule("HighLife")
    ca = CellularAutomaton(rule, width=40, height=20)
    # Place a small seed
    ca.set_cell(20, 10, 1)
    ca.set_cell(21, 10, 1)
    ca.set_cell(19, 11, 1)
    ca.set_cell(20, 11, 1)
    ca.set_cell(20, 12, 1)
    for _ in range(24):
        ca.step()
    print(f"HighLife after {ca.step_count} steps — alive: {ca.alive_count()}")
    print(render_ascii(ca.grid, on_char="█", off_char=" "))


if __name__ == "__main__":
    main()