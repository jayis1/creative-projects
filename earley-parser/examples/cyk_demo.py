#!/usr/bin/env python3
"""Example: CYK parser for CNF grammars.

Demonstrates:
- Building a CNF (Chomsky Normal Form) grammar
- Parsing with the CYK algorithm
- Tree extraction from CYK
- Comparing Earley and CYK on the same language
"""
from earley_parser import CNFGrammar, CYKParser, Grammar, EarleyParser


def main() -> None:
    # Build a CNF grammar for: S -> SS | a  (a+)
    cnf = CNFGrammar(start="S")
    cnf.add_binary("S", "S", "S")
    cnf.add_terminal("S", "a")

    cyk = CYKParser(cnf)

    print("=== CYK Parser Demo ===\n")
    print("Grammar: S -> S S | a  (accepts a+)\n")

    test_inputs = [
        ["a"],
        ["a", "a"],
        ["a", "a", "a"],
        ["a", "a", "a", "a", "a"],
        ["b"],          # rejected
        ["a", "b"],     # rejected
    ]

    for tokens in test_inputs:
        result = cyk.parse(tokens)
        print(f"  {'✓' if result else '✗'}  {' '.join(tokens)}")

    print("\n=== Tree Extraction ===")
    trees = cyk.trees(["a", "a", "a"], max_trees=5)
    print(f"  {len(trees)} tree(s) for 'a a a':")
    for i, t in enumerate(trees):
        print(f"\n  --- Tree {i + 1} ---")
        print(t.pretty())

    # Compare with Earley on an equivalent grammar
    print("\n=== Earley vs CYK Comparison ===")
    earley_g = Grammar.from_rules("S", [
        ("S", ("S", "S")),
        ("S", ("a",)),
    ])
    earley_p = EarleyParser(earley_g)

    test = ["a", "a", "a", "a"]
    earley_ok = earley_p.parse(test)
    cyk_ok = cyk.parse(test)
    print(f"  Input: {' '.join(test)}")
    print(f"  Earley: {'accept' if earley_ok else 'reject'}")
    print(f"  CYK:    {'accept' if cyk_ok else 'reject'}")
    print(f"  Match: {earley_ok == cyk_ok}")


if __name__ == "__main__":
    main()