"""Tests for the CYK parser."""
import pytest
from earley_parser import CNFGrammar, CYKParser, CNFProduction, ParseError


class TestCNFGrammar:
    def test_add_binary(self):
        g = CNFGrammar(start="S")
        g.add_binary("S", "A", "B")
        assert len(g.binary_rules) == 1
        assert "S" in g.lhs_for_binary("A", "B")

    def test_add_terminal(self):
        g = CNFGrammar(start="S")
        g.add_terminal("S", "a")
        assert len(g.terminal_rules) == 1
        assert "S" in g.lhs_for_terminal("a")

    def test_start_nullable(self):
        g = CNFGrammar(start="S")
        g.set_start_nullable()
        assert g._start_nullable

    def test_repr(self):
        g = CNFGrammar(start="S")
        g.add_binary("S", "A", "B")
        g.add_terminal("A", "a")
        assert "CNFGrammar" in repr(g)


class TestCYKParser:
    def test_single_terminal(self):
        g = CNFGrammar(start="S")
        g.add_terminal("S", "a")
        p = CYKParser(g)
        assert p.parse(["a"])
        assert not p.parse(["b"])

    def test_binary_rule(self):
        g = CNFGrammar(start="S")
        g.add_binary("S", "A", "B")
        g.add_terminal("A", "a")
        g.add_terminal("B", "b")
        p = CYKParser(g)
        assert p.parse(["a", "b"])
        assert not p.parse(["a", "a"])

    def test_recursive_grammar(self):
        """S -> S S | a — palindromes of a's."""
        g = CNFGrammar(start="S")
        g.add_binary("S", "S", "S")
        g.add_terminal("S", "a")
        p = CYKParser(g)
        assert p.parse(["a"])
        assert p.parse(["a", "a"])
        assert p.parse(["a", "a", "a"])
        assert p.parse(["a", "a", "a", "a"])
        assert not p.parse(["b"])

    def test_empty_input_nullable(self):
        g = CNFGrammar(start="S")
        g.set_start_nullable()
        p = CYKParser(g)
        assert p.parse([])

    def test_empty_input_not_nullable(self):
        g = CNFGrammar(start="S")
        g.add_terminal("S", "a")
        p = CYKParser(g)
        assert not p.parse([])

    def test_tree_extraction(self):
        g = CNFGrammar(start="S")
        g.add_binary("S", "A", "B")
        g.add_terminal("A", "a")
        g.add_terminal("B", "b")
        p = CYKParser(g)
        trees = p.trees(["a", "b"])
        assert len(trees) == 1
        assert trees[0].symbol == "S"
        assert trees[0].start == 0
        assert trees[0].end == 2

    def test_trees_on_parse_error(self):
        g = CNFGrammar(start="S")
        g.add_terminal("S", "a")
        p = CYKParser(g)
        with pytest.raises(ParseError):
            p.trees(["b"])

    def test_trees_empty_nullable(self):
        g = CNFGrammar(start="S")
        g.set_start_nullable()
        p = CYKParser(g)
        trees = p.trees([])
        assert len(trees) == 1

    def test_parse_or_error_success(self):
        g = CNFGrammar(start="S")
        g.add_terminal("S", "a")
        p = CYKParser(g)
        assert p.parse_or_error(["a"]) is True

    def test_parse_or_error_failure(self):
        g = CNFGrammar(start="S")
        g.add_terminal("S", "a")
        p = CYKParser(g)
        result = p.parse_or_error(["b"])
        assert isinstance(result, ParseError)