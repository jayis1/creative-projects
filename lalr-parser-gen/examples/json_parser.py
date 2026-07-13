"""Example: JSON parser using the LALR parser generator.

Demonstrates parsing a JSON-like grammar with semantic actions that
build a Python dict/list/str/num structure.
"""
from lalr import Grammar, LALRTable, Parser, Token
import re


def build_json_parser():
    grammar = Grammar([
        ("json", ["value"]),

        ("value", ["object"]),
        ("value", ["array"]),
        ("value", ["STRING"]),
        ("value", ["NUMBER"]),
        ("value", ["TRUE"]),
        ("value", ["FALSE"]),
        ("value", ["NULL"]),

        ("object", ["{", "}"]),
        ("object", ["{", "members", "}"]),

        ("members", ["pair"]),
        ("members", ["members", ",", "pair"]),

        ("pair", ["STRING", ":", "value"]),

        ("array", ["[", "]"]),
        ("array", ["[", "elements", "]"]),

        ("elements", ["value"]),
        ("elements", ["elements", ",", "value"]),
    ])

    table = LALRTable(grammar)
    assert not table.has_conflicts, f"Conflicts: {table.conflicts}"

    # Production indices (1-based after augmented production at 0)
    actions = {
        1: lambda c: c[0],           # json -> value
        2: lambda c: c[0],           # value -> object
        3: lambda c: c[0],           # value -> array
        4: lambda c: c[0],           # value -> STRING
        5: lambda c: c[0],           # value -> NUMBER
        6: lambda c: True,           # value -> TRUE
        7: lambda c: False,          # value -> FALSE
        8: lambda c: None,           # value -> NULL
        9: lambda c: {},             # object -> { }
        10: lambda c: dict(c[1]),    # object -> { members }
        11: lambda c: [c[0]],        # members -> pair
        12: lambda c: c[0] + [c[2]], # members -> members , pair
        13: lambda c: (c[0], c[2]),  # pair -> STRING : value
        14: lambda c: [],            # array -> [ ]
        15: lambda c: c[1],          # array -> [ elements ]
        16: lambda c: [c[0]],        # elements -> value
        17: lambda c: c[0] + [c[2]], # elements -> elements , value
    }

    return Parser(grammar, table=table, actions=actions)


def lex_json(text):
    tokens = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        c = text[i]
        if c in '{}[]:,':
            tokens.append(Token(c, c, i))
            i += 1
        elif c == '"':
            end = text.index('"', i + 1)
            tokens.append(Token("STRING", text[i+1:end], i))
            i = end + 1
        elif c.isdigit() or (c == '-' and i+1 < len(text) and text[i+1].isdigit()):
            m = re.match(r'-?\d+(\.\d+)?', text[i:])
            tokens.append(Token("NUMBER", float(m.group()) if '.' in m.group() else int(m.group()), i))
            i += len(m.group())
        elif text[i:i+4] == "true":
            tokens.append(Token("TRUE", True, i))
            i += 4
        elif text[i:i+5] == "false":
            tokens.append(Token("FALSE", False, i))
            i += 5
        elif text[i:i+4] == "null":
            tokens.append(Token("NULL", None, i))
            i += 4
        else:
            raise ValueError(f"Unknown character '{c}' at position {i}")
    return tokens


if __name__ == "__main__":
    parser = build_json_parser()
    tests = [
        ('{"name": "hello", "value": 42}', {"name": "hello", "value": 42}),
        ('[1, 2, 3]', [1, 2, 3]),
        ('{"nested": {"a": 1}}', {"nested": {"a": 1}}),
        ('[]', []),
        ('{}', {}),
        ('[true, false, null]', [True, False, None]),
        ('{"list": [1, [2, 3], {"x": 4}]}', {"list": [1, [2, 3], {"x": 4}]}),
    ]
    all_ok = True
    for text, expected in tests:
        try:
            result = parser.parse(lex_json(text))
            ok = result == expected
            status = "OK" if ok else "FAIL"
            if not ok:
                all_ok = False
            print(f"  {status}: {text} -> {result}")
        except Exception as e:
            print(f"  ERROR: {text} -> {e}")
            all_ok = False
    if all_ok:
        print("\nAll JSON tests passed!")
    else:
        print("\nSome tests failed!")