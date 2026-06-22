#!/usr/bin/env python3
"""Example: Basic recognition and tree extraction.

Demonstrates:
- Building a grammar programmatically
- Recognizing token sequences
- Extracting parse trees
- Working with ambiguous grammars
"""
from earley_parser import Grammar, EarleyParser, ParseForest


def main() -> None:
    # Build the classic ambiguous expression grammar
    g = Grammar.from_rules(
        start="E",
        rules=[
            ("E", ("E", "+", "E")),
            ("E", ("E", "*", "E")),
            ("E", ("(", "E", ")")),
            ("E", ("id",)),
        ],
        name="expr",
    )

    parser = EarleyParser(g)

    # --- Recognition ---
    print("=== Recognition ===")
    test_inputs = [
        ["id"],
        ["id", "+", "id"],
        ["id", "+", "id", "*", "id"],
        ["(", "id", "+", "id", ")", "*", "id"],
        ["id", "+"],          # incomplete
        ["+", "id"],          # starts with operator
        [],                   # empty
    ]
    for tokens in test_inputs:
        result = parser.parse_or_error(tokens)
        if result is True:
            print(f"  ✓  {' '.join(tokens)}")
        else:
            print(f"  ✗  {' '.join(tokens)}  →  {result}")

    # --- Tree extraction ---
    print("\n=== Parse Trees for 'id + id * id' ===")
    forest = parser.forest(["id", "+", "id", "*", "id"], max_trees=10)
    print(f"  {forest.ambiguity_count} parse tree(s) "
          f"(ambiguous: {forest.is_ambiguous})")
    print(forest.pretty())

    # --- Forest export ---
    print("=== JSON Export (first tree) ===")
    if forest.trees:
        print(forest.trees[0].to_json(indent=2))

    print("\n=== DOT Export ===")
    print(forest.to_dot()[:300] + "...")


if __name__ == "__main__":
    main()