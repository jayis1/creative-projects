"""Tests for grammar analysis: LL(1) tables, ambiguity detection, comparison."""
import pytest
from earley_parser import (
    Grammar, LL1Table, is_ll1, detect_ambiguity, is_ambiguous,
    GrammarComparator, compute_bracket_depth, grammar_summary,
)


# -- Fixtures ---------------------------------------------------------------- #

@pytest.fixture
def ambiguous_expr():
    return Grammar.from_rules("E", [
        ("E", ("E", "+", "E")),
        ("E", ("E", "*", "E")),
        ("E", ("(", "E", ")")),
        ("E", ("id",)),
    ])


@pytest.fixture
def ll1_grammar():
    """A simple LL(1) grammar."""
    return Grammar.from_rules("S", [
        ("S", ("a", "A")),
        ("S", ("b", "B")),
        ("A", ("c",)),
        ("B", ("d",)),
    ])


@pytest.fixture
def unambiguous_expr():
    return Grammar.from_rules("E", [
        ("E", ("E", "+", "T")),
        ("E", ("T",)),
        ("T", ("T", "*", "F")),
        ("T", ("F",)),
        ("F", ("(", "E", ")")),
        ("F", ("id",)),
    ])


# -- LL(1) Table ------------------------------------------------------------- #

class TestLL1Table:
    def test_ll1_grammar(self, ll1_grammar):
        table = LL1Table(ll1_grammar).build()
        assert table.is_ll1
        assert len(table.conflicts) == 0

    def test_non_ll1_ambiguous(self, ambiguous_expr):
        table = LL1Table(ambiguous_expr).build()
        assert not table.is_ll1
        assert len(table.conflicts) > 0

    def test_get_entry(self, ll1_grammar):
        table = LL1Table(ll1_grammar).build()
        prod = table.get("S", "a")
        assert prod == ("a", "A")
        prod = table.get("S", "b")
        assert prod == ("b", "B")

    def test_get_none(self, ll1_grammar):
        table = LL1Table(ll1_grammar).build()
        assert table.get("S", "x") is None

    def test_get_all(self, ambiguous_expr):
        table = LL1Table(ambiguous_expr).build()
        entries = table.get_all("E", "id")
        assert len(entries) >= 1

    def test_terminals(self, ll1_grammar):
        table = LL1Table(ll1_grammar).build()
        terms = table.terminals()
        assert "a" in terms
        assert "b" in terms

    def test_nonterminals(self, ll1_grammar):
        table = LL1Table(ll1_grammar).build()
        nts = table.nonterminals()
        assert "S" in nts

    def test_pretty(self, ll1_grammar):
        table = LL1Table(ll1_grammar).build()
        s = table.pretty()
        assert "S" in s
        assert "a" in s

    def test_repr(self, ll1_grammar):
        table = LL1Table(ll1_grammar)
        assert "LL1Table" in repr(table)

    def test_is_ll1_function(self, ll1_grammar):
        assert is_ll1(ll1_grammar)

    def test_is_not_ll1_function(self, ambiguous_expr):
        assert not is_ll1(ambiguous_expr)

    def test_unambiguous_non_ll1(self, unambiguous_expr):
        """Left-recursive grammars are never LL(1)."""
        assert not is_ll1(unambiguous_expr)


# -- Ambiguity Detection ----------------------------------------------------- #

class TestAmbiguityDetection:
    def test_detects_ambiguity(self, ambiguous_expr):
        ambiguous = detect_ambiguity(ambiguous_expr, max_length=5,
                                     alphabet=["id", "+", "*"])
        assert len(ambiguous) > 0

    def test_no_ambiguity_unambiguous(self, unambiguous_expr):
        ambiguous = detect_ambiguity(unambiguous_expr, max_length=4,
                                     alphabet=["id", "+", "*"])
        assert len(ambiguous) == 0

    def test_is_ambiguous_true(self, ambiguous_expr):
        assert is_ambiguous(ambiguous_expr, max_length=5,
                            alphabet=["id", "+", "*"])

    def test_is_ambiguous_false(self, unambiguous_expr):
        assert not is_ambiguous(unambiguous_expr, max_length=4,
                                alphabet=["id", "+", "*"])


# -- Grammar Comparison ------------------------------------------------------ #

class TestGrammarComparator:
    def test_identical_grammars(self):
        g1 = Grammar.from_rules("S", [("S", ("a",))])
        g2 = Grammar.from_rules("S", [("S", ("a",))])
        cmp = GrammarComparator(g1, g2)
        result = cmp.compare(max_length=3, alphabet=["a"])
        assert result["match"]

    def test_different_grammars(self):
        g1 = Grammar.from_rules("S", [("S", ("a",))])
        g2 = Grammar.from_rules("S", [("S", ("b",))])
        cmp = GrammarComparator(g1, g2)
        result = cmp.compare(max_length=3, alphabet=["a", "b"])
        assert not result["match"]
        assert len(result["in_1_not_2"]) > 0
        assert len(result["in_2_not_1"]) > 0

    def test_equivalent_grammars(self):
        """Two grammars for the same language: a*."""
        g1 = Grammar.from_rules("S", [
            ("S", ("S", "a")),
            ("S", ()),
        ])
        g2 = Grammar.from_rules("S", [
            ("S", ("a", "S")),
            ("S", ()),
        ])
        cmp = GrammarComparator(g1, g2)
        result = cmp.compare(max_length=4, alphabet=["a"])
        assert result["match"]


# -- Utility Functions ------------------------------------------------------- #

class TestUtilities:
    def test_compute_bracket_depth(self):
        g = Grammar.from_rules("S", [
            ("S", ("A",)),
            ("A", ("B",)),
            ("B", ("C",)),
            ("C", ("x",)),
        ])
        # S -> A -> B -> C -> x : 3 non-terminal transitions
        assert compute_bracket_depth(g) == 3

    def test_compute_bracket_depth_cycle(self):
        g = Grammar.from_rules("S", [
            ("S", ("A",)),
            ("A", ("S",)),
        ])
        # Should not hang
        depth = compute_bracket_depth(g)
        assert depth >= 1

    def test_grammar_summary(self, ambiguous_expr):
        s = grammar_summary(ambiguous_expr)
        assert "Grammar:" in s
        assert "Start symbol:" in s
        assert "LL(1):" in s
        assert "FOLLOW" in s