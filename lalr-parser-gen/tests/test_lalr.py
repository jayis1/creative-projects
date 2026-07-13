"""Comprehensive test suite for the LALR(1) parser generator."""
import pytest
from lalr import Grammar, LALRTable, Parser, Token, ParseError, load_bnf


# ---------------------------------------------------------------------------
# Grammar / FIRST / FOLLOW
# ---------------------------------------------------------------------------
class TestGrammar:
    def test_basic_construction(self):
        g = Grammar([("S", ["a"])])
        assert len(g.productions) == 2  # augmented + original
        assert g.productions[0].head == "$accept"
        assert g.user_start == "S"

    def test_terminals_nonterminals(self):
        g = Grammar([("S", ["A", "b"]), ("A", ["a"])])
        assert "A" in g.nonterminals
        assert "S" in g.nonterminals
        assert "a" in g.terminals
        assert "b" in g.terminals

    def test_nullable(self):
        g = Grammar([("S", ["A"]), ("A", [])])
        assert "A" in g.nullable
        assert "S" in g.nullable

    def test_first_set(self):
        g = Grammar([("S", ["A", "b"]), ("A", ["a"]), ("A", [])])
        assert g.first["A"] == {"a", ""}
        assert g.first["S"] == {"a", "b", ""}

    def test_follow_set(self):
        g = Grammar([("S", ["A", "b"]), ("A", ["a"])])
        assert "$" in g.follow["S"]
        assert "b" in g.follow["A"]

    def test_epsilon_production(self):
        g = Grammar([("S", []), ("S", ["a", "S"])])
        assert g.first["S"] == {"a", ""}

    def test_validate_unreachable(self):
        """Non-terminals with productions but unreachable from start."""
        g = Grammar([("S", ["a"]), ("X", ["b"])])  # X is unreachable
        warnings = g.validate()
        assert any("X" in w and "unreachable" in w for w in warnings)

    def test_start_symbol_explicit(self):
        g = Grammar([("A", ["a"]), ("S", ["A"])], start="S")
        assert g.user_start == "S"

    def test_empty_grammar_raises(self):
        with pytest.raises(ValueError):
            Grammar([])


# ---------------------------------------------------------------------------
# LALR Table construction
# ---------------------------------------------------------------------------
class TestLALRTable:
    def test_simple_grammar_no_conflicts(self):
        g = Grammar([("S", ["a"])])
        t = LALRTable(g)
        assert not t.has_conflicts

    def test_arithmetic_no_conflicts(self):
        g = Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["term", "*", "factor"]),
            ("term", ["factor"]),
            ("factor", ["(", "expr", ")"]),
            ("factor", ["NUMBER"]),
        ])
        t = LALRTable(g)
        assert not t.has_conflicts
        assert t.num_states > 0

    def test_classic_lalr_not_slr(self):
        """The classic grammar S→L=R | R, L→*R | id, R→L
        is LALR(1) but NOT SLR(1).  If our lookahead computation
        were wrong (using FOLLOW instead of LALR lookaheads), we'd
        get a shift/reduce conflict."""
        g = Grammar([
            ("S", ["L", "=", "R"]),
            ("S", ["R"]),
            ("L", ["*", "R"]),
            ("L", ["ID"]),
            ("R", ["L"]),
        ])
        t = LALRTable(g)
        assert not t.has_conflicts, f"Unexpected conflicts: {t.conflicts}"

    def test_ambiguous_grammar_has_conflicts(self):
        """Dangling-else grammar should produce a shift/reduce conflict."""
        g = Grammar([
            ("S", ["if", "E", "then", "S"]),
            ("S", ["if", "E", "then", "S", "else", "S"]),
            ("S", ["other"]),
            ("E", ["e"]),
        ])
        t = LALRTable(g)
        assert t.has_conflicts

    def test_action_shift(self):
        g = Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["NUMBER"]),
        ])
        t = LALRTable(g)
        # State 0 should have a shift on NUMBER
        assert t.action[0]["NUMBER"][0] == "shift"

    def test_action_accept(self):
        g = Grammar([("S", ["a"])])
        t = LALRTable(g)
        # Find the accept state
        found = False
        for s in range(t.num_states):
            if "$" in t.action[s] and t.action[s]["$"][0] == "accept":
                found = True
        assert found


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class TestParser:
    def _expr_grammar(self):
        return Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["term", "*", "factor"]),
            ("term", ["factor"]),
            ("factor", ["(", "expr", ")"]),
            ("factor", ["NUMBER"]),
        ])

    def test_parse_simple(self):
        g = self._expr_grammar()
        p = Parser(g)
        result = p.parse([Token("NUMBER", 42)])
        # factor -> NUMBER (unit prod returns single value) -> term -> expr
        assert result == 42

    def test_parse_addition(self):
        g = self._expr_grammar()
        p = Parser(g)
        result = p.parse([Token("NUMBER", 1), Token("+"), Token("NUMBER", 2)])
        # expr -> expr + term; unit productions unwrap, so:
        # [1 (from expr->term->factor->NUMBER), None ('+'), 2 (from term->factor->NUMBER)]
        assert result == [1, None, 2]

    def test_parse_with_actions(self):
        g = self._expr_grammar()
        actions = {
            1: lambda c: c[0] + c[2],   # expr + term
            2: lambda c: c[0],          # expr -> term
            3: lambda c: c[0] * c[2],   # term * factor
            4: lambda c: c[0],          # term -> factor
            5: lambda c: c[1],          # ( expr )
            6: lambda c: c[0],          # NUMBER
        }
        p = Parser(g, actions=actions)
        result = p.parse([
            Token("NUMBER", 2), Token("+"), Token("NUMBER", 3),
            Token("*"), Token("NUMBER", 4)
        ])
        assert result == 14

    def test_parse_parenthesized(self):
        g = self._expr_grammar()
        p = Parser(g)
        result = p.parse([
            Token("("), Token("NUMBER", 1), Token("+"), Token("NUMBER", 2), Token(")")
        ])
        # factor -> ( expr )  => [None, [1, None, 2], None]
        assert result[1] == [1, None, 2]

    def test_parse_error(self):
        g = self._expr_grammar()
        p = Parser(g)
        with pytest.raises(ParseError):
            p.parse([Token("+")])

    def test_parse_error_has_expected(self):
        g = self._expr_grammar()
        p = Parser(g)
        try:
            p.parse([Token("+")])
        except ParseError as e:
            assert "NUMBER" in e.expected or "(" in e.expected

    def test_parse_empty_input_error(self):
        g = self._expr_grammar()
        p = Parser(g)
        with pytest.raises(ParseError):
            p.parse([])

    def test_parse_unary_minus(self):
        g = Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["term", "*", "factor"]),
            ("term", ["factor"]),
            ("factor", ["(", "expr", ")"]),
            ("factor", ["NUMBER"]),
            ("factor", ["-", "factor"]),
        ])
        t = LALRTable(g)
        assert not t.has_conflicts
        p = Parser(g, table=t)
        result = p.parse([Token("-"), Token("NUMBER", 5)])
        assert result is not None


# ---------------------------------------------------------------------------
# BNF Loader
# ---------------------------------------------------------------------------
class TestBNFLoader:
    def test_load_simple(self):
        text = """
        %start S
        S : 'a' S | 'a' ;
        """
        g = load_bnf(text)
        assert g.user_start == "S"
        assert len(g.productions) == 3  # augmented + 2

    def test_load_with_directives(self):
        text = """
        %start expr
        %token NUMBER '+' '*' '(' ')'

        expr : expr '+' term
             | term
             ;

        term : NUMBER
             ;
        """
        g = load_bnf(text)
        assert g.user_start == "expr"
        assert "NUMBER" in g.terminals
        assert "+" in g.terminals

    def test_load_comments(self):
        text = """
        # This is a comment
        // Also a comment
        S : 'a' ;
        """
        g = load_bnf(text)
        assert len(g.productions) == 2

    def test_load_epsilon(self):
        text = """
        S : 'a' S | ε ;
        """
        g = load_bnf(text)
        assert g.nullable == {"S", "$accept"}

    def test_load_multiple_productions(self):
        text = """
        expr : term ;
        term : factor ;
        factor : NUMBER ;
        """
        g = load_bnf(text)
        assert len(g.productions) == 4

    def test_load_error_no_colon(self):
        with pytest.raises(Exception):
            load_bnf("S a b")

    def test_load_error_empty(self):
        with pytest.raises(Exception):
            load_bnf("")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])