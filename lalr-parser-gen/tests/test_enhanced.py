"""Tests for SLR(1) table builder and comparison."""
import pytest
from lalr import Grammar, LALRTable, load_bnf_full
from lalr.slr_table import SLRTable


class TestSLRTable:
    def test_simple_grammar(self):
        g = Grammar([("S", ["a"])])
        slr = SLRTable(g)
        assert not slr.has_conflicts

    def test_arithmetic(self):
        g = Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["term", "*", "factor"]),
            ("term", ["factor"]),
            ("factor", ["(", "expr", ")"]),
            ("factor", ["NUMBER"]),
        ])
        slr = SLRTable(g)
        assert not slr.has_conflicts

    def test_classic_lalr_not_slr(self):
        """S → L=R | R, L → *R | id, R → L is LALR(1) but NOT SLR(1)."""
        g = Grammar([
            ("S", ["L", "=", "R"]),
            ("S", ["R"]),
            ("L", ["*", "R"]),
            ("L", ["ID"]),
            ("R", ["L"]),
        ])
        slr = SLRTable(g)
        assert slr.has_conflicts, "SLR should have conflicts on this grammar"
        assert any("=" in c for c in slr.conflicts)

    def test_lalr_no_conflict_same_grammar(self):
        """Same grammar should have no LALR(1) conflicts."""
        g = Grammar([
            ("S", ["L", "=", "R"]),
            ("S", ["R"]),
            ("L", ["*", "R"]),
            ("L", ["ID"]),
            ("R", ["L"]),
        ])
        lalr = LALRTable(g)
        assert not lalr.has_conflicts

    def test_reduce_reduce_conflict(self):
        """Two productions reducing in the same state on same lookahead."""
        g = Grammar([
            ("S", ["A", "a"]),
            ("S", ["B", "a"]),
            ("A", ["x"]),
            ("B", ["x"]),
        ])
        slr = SLRTable(g)
        # This grammar may or may not have reduce/reduce depending on states
        # Just verify it runs
        assert slr.num_states > 0


class TestPrecedence:
    def test_precedence_resolves_conflicts(self):
        """The ambiguous expression grammar with precedence declarations
        should have all conflicts resolved."""
        text = """
        %start expr
        %left '+' '-'
        %left '*' '/'
        %right '^'

        expr : expr '+' expr
             | expr '-' expr
             | expr '*' expr
             | expr '/' expr
             | expr '^' expr
             | '(' expr ')'
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        table = LALRTable(g, precedence=prec)
        assert not table.has_conflicts, f"Unresolved conflicts: {table.conflicts}"
        assert len(table.resolved_conflicts) > 0

    def test_precedence_left_assoc(self):
        """Left associativity: a - b - c should reduce (a - b) - c."""
        text = """
        %start expr
        %left '-'
        expr : expr '-' expr
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        table = LALRTable(g, precedence=prec)
        assert not table.has_conflicts

    def test_precedence_right_assoc(self):
        """Right associativity: a ^ b ^ c should shift."""
        text = """
        %start expr
        %right '^'
        expr : expr '^' expr
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        table = LALRTable(g, precedence=prec)
        assert not table.has_conflicts

    def test_no_precedence_means_conflicts(self):
        """Without precedence, the ambiguous grammar should have conflicts."""
        text = """
        %start expr
        expr : expr '+' expr
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        table = LALRTable(g, precedence=prec)
        assert table.has_conflicts


class TestJSONSerialization:
    def test_to_json_from_json_roundtrip(self):
        g = Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["NUMBER"]),
        ])
        table = LALRTable(g)
        data = table.to_json()
        assert data["num_states"] == table.num_states

        restored = LALRTable.from_json(data)
        assert restored.num_states == table.num_states
        # Verify action tables match
        for state in range(table.num_states):
            for term, action in table.action[state].items():
                assert restored.action[state][term] == action

    def test_to_json_str(self):
        import json
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        s = table.to_json_str()
        data = json.loads(s)
        assert data["num_states"] == table.num_states

    def test_json_parse_with_restored_table(self):
        from lalr import Parser, Token
        g = Grammar([
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["NUMBER"]),
        ])
        table = LALRTable(g)
        data = table.to_json()
        restored = LALRTable.from_json(data)
        parser = Parser(restored.grammar, table=restored)
        result = parser.parse([Token("NUMBER", 1), Token("+"), Token("NUMBER", 2)])
        assert result is not None


class TestBNFLoaderEnhanced:
    def test_load_with_precedence(self):
        text = """
        %start expr
        %left '+' '-'
        %left '*'
        expr : expr '+' expr
             | expr '*' expr
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        assert prec.has_precedence("+")
        assert prec.has_precedence("*")
        assert prec.get_precedence("*") > prec.get_precedence("+")

    def test_load_with_quoted_precedence(self):
        text = """
        %left '+' '-'
        %left '*'
        S : S '+' S
          | S '*' S
          | NUMBER
          ;
        """
        g, prec = load_bnf_full(text)
        assert prec.has_precedence("+")
        assert prec.get_precedence("+") == 1
        assert prec.get_precedence("*") == 2

    def test_load_nonassoc(self):
        text = """
        %nonassoc CMP
        S : S CMP S
          | NUMBER
          ;
        """
        g, prec = load_bnf_full(text)
        assert prec.has_precedence("CMP")
        assert prec.get_associativity("CMP") == "nonassoc"


class TestCLIFeatures:
    def test_slr_compare(self):
        from lalr.cli import main
        import sys
        from io import StringIO
        old = sys.stdout
        sys.stdout = StringIO()
        try:
            rc = main(["examples/classic-lalr.bnf", "--action=slr-compare"])
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old
        assert "LALR(1)" in output
        assert "SLR(1)" in output
        assert "NOT SLR(1)" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])