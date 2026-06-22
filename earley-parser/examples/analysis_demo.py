#!/usr/bin/env python3
"""Example: Grammar analysis — LL(1) checking, FOLLOW sets, ambiguity.

Demonstrates:
- Computing FIRST and FOLLOW sets
- Building an LL(1) parsing table
- Detecting grammar ambiguity
- Comparing two grammars
- Getting a grammar summary
"""
from earley_parser import (
    Grammar, LL1Table, is_ll1, detect_ambiguity,
    GrammarComparator, grammar_summary,
)


def main() -> None:
    # --- Ambiguous expression grammar ---
    ambiguous = Grammar.from_rules("E", [
        ("E", ("E", "+", "E")),
        ("E", ("E", "*", "E")),
        ("E", ("(", "E", ")")),
        ("E", ("id",)),
    ], name="ambiguous-expr")

    # --- Unambiguous expression grammar (with precedence) ---
    unambiguous = Grammar.from_rules("E", [
        ("E", ("E", "+", "T")),
        ("E", ("T",)),
        ("T", ("T", "*", "F")),
        ("T", ("F",)),
        ("F", ("(", "E", ")")),
        ("F", ("id",)),
    ], name="unambiguous-expr")

    print("=== Grammar Summary: Ambiguous ===")
    print(grammar_summary(ambiguous))

    print("\n=== Grammar Summary: Unambiguous ===")
    print(grammar_summary(unambiguous))

    print("\n=== LL(1) Analysis ===")
    for name, g in [("Ambiguous", ambiguous), ("Unambiguous", unambiguous)]:
        table = LL1Table(g).build()
        print(f"\n{name} grammar:")
        print(f"  LL(1): {'yes' if table.is_ll1 else 'NO'}")
        if table.conflicts:
            print(f"  Conflicts: {len(table.conflicts)}")
            for c in table.conflicts[:3]:
                print(f"    - {c}")

    print("\n=== LL(1) Table for Simple Grammar ===")
    simple = Grammar.from_rules("S", [
        ("S", ("a", "A")),
        ("S", ("b", "B")),
        ("A", ("c",)),
        ("B", ("d",)),
    ], name="simple-ll1")
    table = LL1Table(simple).build()
    print(f"  is_ll1: {table.is_ll1}")
    print(table.pretty())

    print("\n=== Ambiguity Detection ===")
    amb = detect_ambiguity(ambiguous, max_length=5, alphabet=["id", "+", "*"])
    print(f"  Ambiguous inputs found: {len(amb)}")
    for tokens in amb[:5]:
        print(f"    {' '.join(tokens)}")
    if len(amb) > 5:
        print(f"    ... and {len(amb) - 5} more")

    print("\n=== Grammar Comparison ===")
    cmp = GrammarComparator(ambiguous, unambiguous)
    result = cmp.compare(max_length=4, alphabet=["id", "+", "*"])
    print(f"  Languages match: {result['match']}")
    if not result["match"]:
        print(f"  In ambiguous only: {len(result['in_1_not_2'])} strings")
        print(f"  In unambiguous only: {len(result['in_2_not_1'])} strings")
        print(f"  In both: {len(result['in_both'])} strings")


if __name__ == "__main__":
    main()