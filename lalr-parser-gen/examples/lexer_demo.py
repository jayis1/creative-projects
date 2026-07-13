"""Example: using the configurable Lexer with the LALR parser.

Demonstrates building a lexer with the Lexer framework and parsing
arithmetic expressions with proper token value conversion.
"""
from lalr import Grammar, LALRTable, Parser, Token
from lalr.lexer import Lexer, TokenSpec


def build_lexer() -> Lexer:
    """Build a lexer for arithmetic expressions."""
    lexer = Lexer()
    lexer.add_spec(TokenSpec("NUMBER", r"\d+", action=int))
    lexer.add_spec(TokenSpec("PLUS", r"\+"))
    lexer.add_spec(TokenSpec("MINUS", r"-"))
    lexer.add_spec(TokenSpec("TIMES", r"\*"))
    lexer.add_spec(TokenSpec("DIVIDE", r"/"))
    lexer.add_spec(TokenSpec("LPAREN", r"\("))
    lexer.add_spec(TokenSpec("RPAREN", r"\)"))
    lexer.set_skip(r"[ \t\n]+")
    return lexer


def build_parser():
    """Build a parser for arithmetic expressions."""
    grammar = Grammar([
        ("expr", ["expr", "PLUS", "term"]),
        ("expr", ["expr", "MINUS", "term"]),
        ("expr", ["term"]),
        ("term", ["term", "TIMES", "factor"]),
        ("term", ["term", "DIVIDE", "factor"]),
        ("term", ["factor"]),
        ("factor", ["LPAREN", "expr", "RPAREN"]),
        ("factor", ["MINUS", "factor"]),
        ("factor", ["NUMBER"]),
    ])
    table = LALRTable(grammar)
    assert not table.has_conflicts, f"Grammar has conflicts: {table.conflicts}"

    actions = {
        1: lambda c: c[0] + c[2],   # expr -> expr + term
        2: lambda c: c[0] - c[2],   # expr -> expr - term
        3: lambda c: c[0],           # expr -> term
        4: lambda c: c[0] * c[2],   # term -> term * factor
        5: lambda c: c[0] / c[2],   # term -> term / factor
        6: lambda c: c[0],           # term -> factor
        7: lambda c: c[1],           # factor -> ( expr )
        8: lambda c: -c[1],          # factor -> - factor
        9: lambda c: c[0],           # factor -> NUMBER
    }
    return Parser(grammar, table=table, actions=actions)


def main():
    # The lexer produces token types matching the grammar's terminal names
    # directly (PLUS, MINUS, TIMES, DIVIDE, LPAREN, RPAREN, NUMBER)
    # No remapping needed.

    lexer = build_lexer()
    parser = build_parser()

    expressions = [
        "2 + 3",
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "10 - 2 - 3",
        "100 / 5 / 2",
        "-5 + 3",
        "-(2 + 3)",
        "2 * -3",
        "3 + 4 * 2 - 1",
    ]

    all_ok = True
    for expr in expressions:
        try:
            tokens = lexer.lex(expr)
            result = parser.parse(tokens)
            # Evaluate to verify
            expected = eval(expr)  # noqa: S307 — safe for demo
            status = "OK" if result == expected else "FAIL"
            if status == "FAIL":
                all_ok = False
            print(f"  {status}: {expr} = {result} (expected {expected})")
        except Exception as e:
            print(f"  ERROR: {expr} -> {e}")
            all_ok = False

    if all_ok:
        print("\nAll lexer demo tests passed!")
    else:
        print("\nSome tests failed!")


if __name__ == "__main__":
    main()