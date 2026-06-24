"""Example: Conway's Game of Life with a Gosper glider gun."""

from cellular_automaton import CellularAutomaton, GameOfLifeRule, get_pattern, place_pattern, render_ascii


def main():
    ca = CellularAutomaton(GameOfLifeRule(), width=60, height=40)
    place_pattern(ca, get_pattern("gosper_gun"), x=5, y=10)
    for i in range(120):
        ca.step()
    print(f"After {ca.step_count} steps — alive cells: {ca.alive_count()}")
    print(render_ascii(ca.grid, on_char="█", off_char=" "))


if __name__ == "__main__":
    main()