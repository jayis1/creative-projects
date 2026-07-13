"""Example: grammar transformations.

Demonstrates left-recursion removal and left-factoring using the
transform module.
"""
from lalr.transform import (
    remove_left_recursion,
    left_factor,
    remove_unreachable,
    eliminate_useless_symbols,
    grammar_summary,
)


def main():
    print("=" * 60)
    print("Grammar Transformation Examples")
    print("=" * 60)

    # Example 1: Left recursion removal
    print("\n--- Left Recursion Removal ---\n")
    original = [
        ("expr", ["expr", "+", "term"]),
        ("expr", ["term"]),
        ("term", ["term", "*", "factor"]),
        ("term", ["factor"]),
        ("factor", ["NUMBER"]),
    ]
    print("Original grammar:")
    print(grammar_summary(original, "expr"))

    transformed, start = remove_left_recursion(original, "expr")
    print("\nAfter left recursion removal:")
    print(grammar_summary(transformed, start))

    # Example 2: Left factoring
    print("\n--- Left Factoring ---\n")
    original2 = [
        ("stmt", ["IF", "expr", "THEN", "stmt"]),
        ("stmt", ["IF", "expr", "THEN", "stmt", "ELSE", "stmt"]),
        ("stmt", ["expr"]),
    ]
    print("Original grammar:")
    print(grammar_summary(original2, "stmt"))

    factored = left_factor(original2)
    print("\nAfter left factoring:")
    print(grammar_summary(factored, "stmt"))

    # Example 3: Useless symbol elimination
    print("\n--- Useless Symbol Elimination ---\n")
    original3 = [
        ("S", ["A", "a"]),
        ("S", ["B"]),
        ("A", ["a"]),
        ("B", ["B", "b"]),  # B never derives terminal-only string
        ("C", ["c"]),      # C is unreachable
    ]
    print("Original grammar:")
    print(grammar_summary(original3, "S"))

    cleaned = eliminate_useless_symbols(original3, "S")
    print("\nAfter useless symbol elimination:")
    print(grammar_summary(cleaned, "S"))

    # Example 4: Combined transformations
    print("\n--- Combined: Left Recursion + Factoring ---\n")
    original4 = [
        ("S", ["S", "a"]),
        ("S", ["b"]),
        ("S", ["b", "c"]),
    ]
    print("Original grammar:")
    print(grammar_summary(original4, "S"))

    step1, start4 = remove_left_recursion(original4, "S")
    step2 = left_factor(step1)
    print("\nAfter left recursion removal + left factoring:")
    print(grammar_summary(step2, start4))


if __name__ == "__main__":
    main()