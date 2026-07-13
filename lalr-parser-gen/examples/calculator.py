"""Example: build a calculator using the LALR parser generator.

This demonstrates defining a grammar, building the LALR(1) table, and
attaching semantic actions to evaluate arithmetic expressions.
"""
from lalr import Grammar, LALRTable, Parser, Token


def build_calculator():
    grammar = Grammar([
        ("expr",   ["expr", "+", "term"]),
        ("expr",   ["expr", "-", "term"]),
        ("expr",   ["term"]),
        ("term",   ["term", "*", "factor"]),
        ("term",   ["term", "/", "factor"]),
        ("term",   ["factor"]),
        ("factor", ["(", "expr", ")"]),
        ("factor", ["NUMBER"]),
        ("factor", ["-", "factor"]),  # unary minus
    ])

    table = LALRTable(grammar)
    assert not table.has_conflicts, f"Grammar has conflicts: {table.conflicts}"

    actions = {
        # expr -> expr + term
        1: lambda c: c[0] + c[2],
        # expr -> expr - term
        2: lambda c: c[0] - c[2],
        # expr -> term
        3: lambda c: c[0],
        # term -> term * factor
        4: lambda c: c[0] * c[2],
        # term -> term / factor
        5: lambda c: c[0] / c[2],
        # term -> factor
        6: lambda c: c[0],
        # factor -> ( expr )
        7: lambda c: c[1],
        # factor -> NUMBER
        8: lambda c: c[0],
        # factor -> - factor
        9: lambda c: -c[1],
    }

    return Parser(grammar, table=table, actions=actions)


def lex(text: str):
    import re
    tokens = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text[i].isdigit():
            m = re.match(r"\d+", text[i:])
            tokens.append(Token("NUMBER", int(m.group()), i))
            i += len(m.group())
        elif text[i] in "+-*/()":
            tokens.append(Token(text[i], text[i], i))
            i += 1
        else:
            raise ValueError(f"Unknown character '{text[i]}' at position {i}")
    return tokens


if __name__ == "__main__":
    calc = build_calculator()
    tests = [
        ("2 + 3", 5),
        ("2 + 3 * 4", 14),
        ("(2 + 3) * 4", 20),
        ("10 - 2 - 3", 5),       # left associative
        ("100 / 5 / 2", 10),     # left associative
        ("-5 + 3", -2),
        ("-(2 + 3)", -5),
        ("2 * -3", -6),
    ]
    all_ok = True
    for expr, expected in tests:
        try:
            result = calc.parse(lex(expr))
            status = "OK" if result == expected else "FAIL"
            if status == "FAIL":
                all_ok = False
            print(f"  {status}: {expr} = {result} (expected {expected})")
        except Exception as e:
            print(f"  ERROR: {expr} -> {e}")
            all_ok = False
    if all_ok:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed!")