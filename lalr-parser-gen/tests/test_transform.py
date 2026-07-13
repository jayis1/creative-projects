"""Tests for grammar transformation utilities."""
import pytest
from lalr.transform import (
    remove_left_recursion,
    left_factor,
    remove_unreachable,
    eliminate_useless_symbols,
    grammar_summary,
)
from lalr import Grammar, LALRTable


class TestRemoveLeftRecursion:
    def test_simple_left_recursion(self):
        prods = [("A", ["A", "a"]), ("A", ["b"])]
        result, start = remove_left_recursion(prods, "A")
        # Should have A -> b A' and A' -> a A' | epsilon
        heads = [h for h, _ in result]
        assert "A'" in heads or "A'" in [h for h, _ in result]
        # Check that no direct left recursion remains on A
        for h, body in result:
            if h == "A":
                assert body[0] != "A"

    def test_no_left_recursion(self):
        """Grammars without left recursion should be unchanged."""
        prods = [("S", ["a", "S"]), ("S", ["a"])]
        result, start = remove_left_recursion(prods, "S")
        # S has no left recursion, so should be kept as-is
        assert ("S", ["a", "S"]) in result
        assert ("S", ["a"]) in result

    def test_multiple_recursive_alts(self):
        prods = [("E", ["E", "+", "T"]), ("E", ["E", "-", "T"]), ("E", ["T"])]
        result, start = remove_left_recursion(prods, "E")
        # Should introduce E'
        assert any(h.endswith("'") for h, _ in result)

    def test_transformed_grammar_is_lalr(self):
        """The transformed grammar should still be parseable."""
        original = [
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["NUMBER"]),
        ]
        transformed, start = remove_left_recursion(original, "expr")
        g = Grammar(transformed, start=start)
        table = LALRTable(g)
        assert not table.has_conflicts

    def test_empty_grammar(self):
        result, start = remove_left_recursion([], "")
        assert result == []


class TestLeftFactoring:
    def test_common_prefix(self):
        prods = [
            ("A", ["a", "b"]),
            ("A", ["a", "c"]),
            ("A", ["d"]),
        ]
        result = left_factor(prods)
        # Should introduce a factored non-terminal
        assert len(result) > len(prods)

    def test_no_common_prefix(self):
        """No common prefix — should be unchanged."""
        prods = [("A", ["a"]), ("A", ["b"]), ("A", ["c"])]
        result = left_factor(prods)
        assert len(result) == 3

    def test_single_production(self):
        prods = [("A", ["a", "b"])]
        result = left_factor(prods)
        assert result == prods

    def test_full_prefix(self):
        """When all alternatives are identical — edge case."""
        prods = [("A", ["a"]), ("A", ["a"])]
        result = left_factor(prods)
        # Should factor out 'a'
        assert len(result) >= 2


class TestRemoveUnreachable:
    def test_remove_unreachable(self):
        prods = [("S", ["a"]), ("X", ["b"]), ("Y", ["c"])]
        result = remove_unreachable(prods, "S")
        heads = set(h for h, _ in result)
        assert "S" in heads
        assert "X" not in heads
        assert "Y" not in heads

    def test_all_reachable(self):
        prods = [("S", ["A", "a"]), ("A", ["b"])]
        result = remove_unreachable(prods, "S")
        assert len(result) == 2


class TestEliminateUseless:
    def test_useless_nonterminal(self):
        """B -> B b never derives terminal string."""
        prods = [("S", ["A", "a"]), ("A", ["a"]), ("B", ["B", "b"])]
        result = eliminate_useless_symbols(prods, "S")
        heads = set(h for h, _ in result)
        assert "B" not in heads

    def test_unreachable_removed(self):
        prods = [("S", ["a"]), ("C", ["c"])]
        result = eliminate_useless_symbols(prods, "S")
        assert ("C", ["c"]) not in result


class TestGrammarSummary:
    def test_summary_basic(self):
        prods = [("S", ["a", "S"]), ("S", ["a"])]
        s = grammar_summary(prods, "S")
        assert "S" in s
        assert "2" in s  # 2 productions

    def test_summary_empty(self):
        s = grammar_summary([])
        assert "Empty" in s