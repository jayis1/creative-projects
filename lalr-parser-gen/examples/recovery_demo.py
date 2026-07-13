"""Example: error recovery with the LALR parser.

Demonstrates using RecoveringParser to continue parsing after syntax
errors, collecting multiple errors in a single pass.
"""
from lalr import Grammar, LALRTable, Token
from lalr.error_recovery import RecoveringParser, ParseErrorEntry


def build_grammar():
    """Simple statement grammar for error recovery demo."""
    return Grammar([
        ("stmts", ["stmts", "stmt"]),
        ("stmts", ["stmt"]),
        ("stmt", ["ID", "=", "expr", ";"]),
        ("stmt", ["IF", "expr", "THEN", "stmt"]),
        ("stmt", ["ID", ";"]),
        ("expr", ["expr", "+", "term"]),
        ("expr", ["term"]),
        ("term", ["NUMBER"]),
        ("term", ["ID"]),
    ])


def main():
    grammar = build_grammar()
    table = LALRTable(grammar)
    if table.has_conflicts:
        print(f"Warning: grammar has conflicts: {table.conflicts}")

    parser = RecoveringParser(
        grammar, table=table,
        sync_tokens={";", "THEN"},
        max_errors=20,
    )

    # Input with intentional errors:
    # - Missing semicolon after first statement
    # - Extra '+' token
    # - Missing THEN
    tokens = [
        Token("ID", "x", 0),
        Token("=", "=", 1),
        Token("NUMBER", 42, 2),
        # Missing ; here
        Token("ID", "y", 3),
        Token("=", "=", 4),
        Token("NUMBER", 10, 5),
        Token(";", ";", 6),
        # Now an IF without THEN
        Token("IF", "if", 7),
        Token("NUMBER", 1, 8),
        # Missing THEN
        Token("ID", "z", 9),
        Token(";", ";", 10),
    ]

    errors: list[ParseErrorEntry] = []
    print("Parsing input with intentional errors...\n")
    print("Token stream: " + " ".join(t.type for t in tokens) + "\n")

    result = parser.parse(tokens, on_error=errors.append)

    if errors:
        print(f"Found {len(errors)} error(s):\n")
        for i, e in enumerate(errors, 1):
            print(f"  Error {i}: {e}")
    else:
        print("No errors detected (unexpected).")

    print(f"\nFinal parse result: {result}")
    print("\nError recovery demonstration complete.")


if __name__ == "__main__":
    main()