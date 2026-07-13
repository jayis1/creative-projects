"""Example: generating Graphviz DOT visualization of the LR automaton.

Run this script to generate a .dot file, then render it with:
    dot -Tpng examples/automaton.dot -o examples/automaton.png
"""
from lalr import Grammar, LALRTable
from lalr.visualize import automaton_to_dot, conflict_report, table_to_html


def main():
    grammar = Grammar([
        ("expr", ["expr", "+", "term"]),
        ("expr", ["term"]),
        ("term", ["term", "*", "factor"]),
        ("term", ["factor"]),
        ("factor", ["(", "expr", ")"]),
        ("factor", ["NUMBER"]),
    ])
    table = LALRTable(grammar)

    # Generate DOT file
    dot = automaton_to_dot(table, title="Arithmetic Expression LR(0) Automaton",
                           show_lookaheads=True, horizontal=True)
    with open("examples/automaton.dot", "w") as f:
        f.write(dot)
    print("DOT file written to examples/automaton.dot")
    print("Render with: dot -Tpng examples/automaton.dot -o examples/automaton.png")

    # Generate HTML table
    html = table_to_html(table)
    with open("examples/table.html", "w") as f:
        f.write(html)
    print("HTML table written to examples/table.html")

    # Generate conflict report
    report = conflict_report(table)
    print(f"\n{report}")

    # Also try an ambiguous grammar to show conflicts
    print("\n" + "=" * 60)
    print("Ambiguous grammar example:")
    print("=" * 60)
    ambig = Grammar([
        ("S", ["S", "S"]),
        ("S", ["a"]),
    ])
    ambig_table = LALRTable(ambig)
    print(conflict_report(ambig_table))


if __name__ == "__main__":
    main()