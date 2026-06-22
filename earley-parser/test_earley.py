"""Tests for the earley-parser project."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from earley import (
    Grammar, EarleyParser, ParseError, ParseNode,
    Tokenizer, TokenSpec, GrammarLoader,
)


# -- Grammar construction --------------------------------------------------- #

def make_expr_grammar():
    return Grammar.from_rules(
        start="E",
        rules=[
            ("E", ("E", "+", "E")),
            ("E", ("E", "*", "E")),
            ("E", ("(", "E", ")")),
            ("E", ("id",)),
        ],
    )


def make_balance_grammar():
    return Grammar.from_rules("S", [
        ("S", ("(", "S", ")")),
        ("S", ("S", "S")),
        ("S", ()),
    ])


# -- Recognition ------------------------------------------------------------ #

def test_basic_recognition():
    g = make_expr_grammar()
    p = EarleyParser(g)
    assert p.parse(["id"])
    assert p.parse(["id", "+", "id"])
    assert p.parse(["id", "+", "id", "*", "id"])
    assert p.parse(["(", "id", "+", "id", ")", "*", "id"])


def test_rejection():
    g = make_expr_grammar()
    p = EarleyParser(g)
    assert not p.parse(["id", "+"])
    assert not p.parse(["+", "id"])
    assert not p.parse([])
    assert not p.parse(["id", "id"])


def test_epsilon():
    g = make_balance_grammar()
    p = EarleyParser(g)
    assert p.parse([])
    assert p.parse(["(", ")"])
    assert p.parse(["(", "(", ")", ")"])
    assert not p.parse(["(", ")", ")"])


def test_nullable_midrule():
    g = Grammar.from_rules("A", [
        ("A", ("B", "C")),
        ("B", ("x",)),
        ("B", ()),
        ("C", ("c",)),
    ])
    p = EarleyParser(g)
    assert p.parse(["x", "c"])
    assert p.parse(["c"])
    assert not p.parse(["x"])


# -- Tree extraction -------------------------------------------------------- #

def test_tree_extraction():
    g = make_expr_grammar()
    p = EarleyParser(g)
    trees = p.trees_v2(["id"])
    assert len(trees) == 1
    assert trees[0].symbol == "E"
    assert trees[0].start == 0
    assert trees[0].end == 1


def test_ambiguous_trees():
    """The classic ambiguous grammar should produce multiple trees."""
    g = make_expr_grammar()
    p = EarleyParser(g)
    trees = p.trees_v2(["id", "+", "id", "*", "id"], max_trees=10)
    assert len(trees) >= 2, f"Expected >=2 trees, got {len(trees)}"


def test_unambiguous_grammar_one_tree():
    g = Grammar.from_rules("E", [
        ("E", ("E", "+", "T")),
        ("E", ("T",)),
        ("T", ("T", "*", "F")),
        ("T", ("F",)),
        ("F", ("(", "E", ")")),
        ("F", ("id",)),
    ])
    p = EarleyParser(g)
    trees = p.trees_v2(["id", "+", "id", "*", "id"], max_trees=10)
    assert len(trees) == 1, f"Expected 1 tree, got {len(trees)}"


def test_tree_spans():
    g = make_expr_grammar()
    p = EarleyParser(g)
    trees = p.trees_v2(["id", "+", "id"])
    assert len(trees) == 1
    t = trees[0]
    assert t.start == 0 and t.end == 3
    # Children: E[0:1], +[1:2], E[2:3]
    assert len(t.children) == 3
    assert t.children[0].start == 0 and t.children[0].end == 1
    assert t.children[1].symbol == "+"


# -- Error reporting -------------------------------------------------------- #

def test_parse_error():
    g = make_expr_grammar()
    p = EarleyParser(g)
    result = p.parse_or_error(["id", "+"])
    assert isinstance(result, ParseError)
    assert result.position == 2


def test_error_expected_set():
    g = make_expr_grammar()
    p = EarleyParser(g)
    result = p.parse_or_error(["id", "+"])
    assert isinstance(result, ParseError)
    assert "id" in result.expected or "(" in result.expected


# -- Grammar validation ----------------------------------------------------- #

def test_grammar_validation():
    g = make_expr_grammar()
    problems = g.validate()
    assert problems == []


def test_grammar_validation_unproductive():
    g = Grammar.from_rules("S", [
        ("S", ("A",)),
        ("A", ("B",)),
        ("B", ("A",)),
    ])
    problems = g.validate()
    assert any("unproductive" in p for p in problems)


def test_first_sets():
    g = make_expr_grammar()
    first = g.first()
    assert "id" in first.get("E", set())
    assert "(" in first.get("E", set())


# -- Tokenizer -------------------------------------------------------------- #

def test_tokenizer():
    tok = Tokenizer([
        TokenSpec("NUM", r"[0-9]+"),
        TokenSpec("PLUS", r"\+"),
        TokenSpec("WS", r"\s+", skip=True),
    ])
    tokens = tok.tokenize("12 + 34")
    assert tokens == ["NUM", "PLUS", "NUM"]


def test_tokenizer_error():
    tok = Tokenizer([
        TokenSpec("NUM", r"[0-9]+"),
    ])
    try:
        tok.tokenize("12abc")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# -- Grammar loader --------------------------------------------------------- #

def test_grammar_loader():
    text = """
# Expression grammar
start ::= <E>

<E> ::= <E> "+" <E>
      | <E> "*" <E>
      | "(" <E> ")"
      | "id"
"""
    g = GrammarLoader.load(text)
    assert g.start == "E"
    assert len(g.productions["E"]) == 4
    p = EarleyParser(g)
    assert p.parse(["id", "+", "id"])


def test_grammar_loader_epsilon():
    text = """start ::= <S>

<S> ::= "(" <S> ")"
      | <S> <S>
      |
"""
    g = GrammarLoader.load(text)
    assert g.start == "S"
    assert () in g.productions["S"]
    p = EarleyParser(g)
    assert p.parse([])
    assert p.parse(["(", ")"])


# -- ParseNode -------------------------------------------------------------- #

def test_parse_node_to_dict():
    node = ParseNode("E", 0, 3, [ParseNode("id", 0, 1, [])])
    d = node.to_dict()
    assert d["symbol"] == "E"
    assert d["span"] == [0, 3]
    assert len(d["children"]) == 1


def test_parse_node_pretty():
    node = ParseNode("E", 0, 1, [ParseNode("id", 0, 1, [])])
    s = node.pretty()
    assert "E" in s
    assert "id" in s


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    if failures:
        print(f"\n{failures} test(s) failed")
        sys.exit(1)
    else:
        print(f"\nAll tests passed")