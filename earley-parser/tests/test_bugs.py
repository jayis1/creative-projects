"""Tests verifying the original bug fixes are maintained in v2.0."""
import pytest
from earley_parser import (
    Grammar, EarleyParser, ParseError, Tokenizer, TokenSpec,
    GrammarLoader, GrammarError,
)


class TestBugFixes:
    """Tests for the 6 bugs found and fixed in the original Phase 3."""

    def test_bug1_memo_truncation(self):
        """Memo should not cache truncated tree lists."""
        g = Grammar.from_rules("S", [
            ("S", ("A", "A")),
            ("A", ("a",)),
            ("A", ("B",)),
            ("B", ("a",)),
        ])
        p = EarleyParser(g)
        trees_small = p.trees(["a", "a"], max_trees=3)
        assert len(trees_small) == 3
        trees_full = p.trees(["a", "a"], max_trees=50)
        assert len(trees_full) == 4

    def test_bug2_tokenizer_zero_length(self):
        """Zero-length regex matches should not cause infinite loops."""
        tok = Tokenizer([
            TokenSpec("NUM", r"[0-9]*"),
            TokenSpec("PLUS", r"\+"),
        ])
        try:
            tok.tokenize("a+")
        except Exception:
            pass  # Acceptable: raises error
        tok2 = Tokenizer([
            TokenSpec("NUM", r"[0-9]+"),
            TokenSpec("PLUS", r"\+"),
        ])
        assert tok2.tokenize("12+34") == ["NUM", "PLUS", "NUM"]

    def test_bug3_empty_grammar(self):
        """Loading an empty grammar should raise a clear error."""
        with pytest.raises((GrammarError, ValueError)):
            GrammarLoader.load("")

    def test_bug4_tree_node_sharing(self):
        """Parse trees should not share ParseNode objects."""
        g = Grammar.from_rules("S", [
            ("S", ("A", "A")),
            ("A", ("a",)),
            ("A", ("B",)),
            ("B", ("a",)),
        ])
        p = EarleyParser(g)
        trees = p.trees(["a", "a"], max_trees=50)
        assert len(trees) == 4
        for i in range(len(trees)):
            for j in range(i + 1, len(trees)):
                assert trees[i] is not trees[j]
                for ci in trees[i].children:
                    for cj in trees[j].children:
                        assert ci is not cj

    def test_bug5_empty_input_non_nullable(self):
        """Empty input with non-nullable start should produce ParseError."""
        g = Grammar.from_rules("E", [
            ("E", ("E", "+", "E")),
            ("E", ("id",)),
        ])
        p = EarleyParser(g)
        result = p.parse_or_error([])
        assert isinstance(result, ParseError)
        assert result.position == 0

    def test_furthest_position_works(self):
        """_furthest_position should work without tokens param."""
        g = Grammar.from_rules("E", [
            ("E", ("E", "+", "E")),
            ("E", ("id",)),
        ])
        p = EarleyParser(g)
        p.parse(["id", "+"])
        pos = p._furthest_position()
        assert pos == 2