#!/usr/bin/env python3
"""Example: Using a tokenizer with a grammar.

Demonstrates:
- Defining token specifications
- Tokenizing raw text
- Parsing the resulting token stream
- Error handling for invalid input
"""
from earley_parser import (
    Grammar, EarleyParser, Tokenizer, TokenSpec,
    GrammarLoader, ParseError,
)


def main() -> None:
    # Load grammar from BNF file
    with open("examples/expr.bnf") as f:
        grammar = GrammarLoader.load(f.read(), name="expr")

    # Define a tokenizer for arithmetic expressions
    tokenizer = Tokenizer([
        TokenSpec("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        TokenSpec("LPAREN", r"\("),
        TokenSpec("RPAREN", r"\)"),
        TokenSpec("PLUS", r"\+"),
        TokenSpec("STAR", r"\*"),
        TokenSpec("WS", r"\s+", skip=True),
    ])

    parser = EarleyParser(grammar)

    # Map tokenizer output to grammar terminals
    # The grammar uses terminals: id, (, ), +, *
    token_map = {
        "ID": "id",
        "LPAREN": "(",
        "RPAREN": ")",
        "PLUS": "+",
        "STAR": "*",
    }

    test_expressions = [
        "id",
        "id + id",
        "id + id * id",
        "(id + id) * id",
        "x + y * (z + w)",
        "id +",            # invalid
        "* id",            # invalid
    ]

    print("=== Tokenizer + Parser Demo ===\n")
    for expr in test_expressions:
        # Tokenize
        try:
            token_types = tokenizer.tokenize(expr)
            # Map to grammar terminals
            tokens = [token_map.get(t, t) for t in token_types]
        except Exception as e:
            print(f"  Tokenizer error: {expr!r} → {e}")
            continue

        # Parse
        try:
            trees = parser.trees(tokens, max_trees=5)
            print(f"  {expr!r} → {len(trees)} tree(s)")
            if len(trees) > 1:
                print(f"    (ambiguous: {len(trees)} interpretations)")
        except ParseError as e:
            print(f"  {expr!r} → Parse error: {e}")


if __name__ == "__main__":
    main()