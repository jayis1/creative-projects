#!/usr/bin/env python3
"""Example: Parse forest export formats.

Demonstrates exporting parse trees to:
- JSON (for programmatic use)
- Graphviz DOT (for visualization)
- Lisp S-expressions (for compact display)
- Pretty text (for human reading)
"""
from earley_parser import Grammar, EarleyParser


def main() -> None:
    g = Grammar.from_rules("E", [
        ("E", ("E", "+", "E")),
        ("E", ("E", "*", "E")),
        ("E", ("(", "E", ")")),
        ("E", ("id",)),
    ], name="expr")

    parser = EarleyParser(g)
    forest = parser.forest(["id", "+", "id", "*", "id"], max_trees=10)

    print(f"Parse forest: {forest.ambiguity_count} tree(s)\n")

    # --- Pretty text ---
    print("=== Pretty Text (Tree 1) ===")
    print(forest.trees[0].pretty())

    # --- JSON ---
    print("\n=== JSON (Tree 1) ===")
    print(forest.trees[0].to_json(indent=2))

    # --- Lisp S-expression ---
    print("\n=== Lisp S-expression (Tree 1) ===")
    print(forest.to_lisp())

    # --- Graphviz DOT ---
    print("\n=== Graphviz DOT (Tree 1) ===")
    dot = forest.to_dot()
    print(dot)
    print(f"\n(To render: save to file and run: dot -Tpng tree.dot -o tree.png)")

    # --- Full forest JSON ---
    print("\n=== Full Forest JSON ===")
    print(forest.to_json()[:500] + "...")


if __name__ == "__main__":
    main()