"""Tests for the earley-parser project."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from earley import Grammar, EarleyParser


def make_grammar():
    return Grammar.from_rules(
        start="E",
        rules=[
            ("E", ("E", "+", "E")),
            ("E", ("E", "*", "E")),
            ("E", ("(", "E", ")")),
            ("E", ("id",)),
        ],
    )


def test_basic():
    g = make_grammar()
    p = EarleyParser(g)
    assert p.parse(["id"])
    assert p.parse(["id", "+", "id"])
    assert p.parse(["id", "+", "id", "*", "id"])
    assert p.parse(["(", "id", "+", "id", ")", "*", "id"])


def test_reject():
    g = make_grammar()
    p = EarleyParser(g)
    assert not p.parse(["id", "+"])
    assert not p.parse(["+", "id"])
    assert not p.parse([])
    assert not p.parse(["id", "id"])


def test_epsilon():
    g = Grammar.from_rules("S", [("S", ("a", "S", "b")), ("S", ())])
    p = EarleyParser(g)
    assert p.parse([])
    assert p.parse(["a", "b"])
    assert p.parse(["a", "a", "b", "b"])
    assert not p.parse(["a", "b", "b"])


def test_nullable_midrule():
    # A -> B C, B nullable, C terminal
    g = Grammar.from_rules("A", [("A", ("B", "C")), ("B", ("x",)), ("B", ()), ("C", ("c",))])
    p = EarleyParser(g)
    assert p.parse(["x", "c"])
    assert p.parse(["c"])
    assert not p.parse(["x"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")