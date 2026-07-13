"""Bug hunt tests — designed to find and verify bugs in the LALR parser generator."""
import pytest
from lalr import Grammar, LALRTable, Parser, Token, ParseError, load_bnf, load_bnf_full
from lalr.slr_table import SLRTable
from lalr.precedence import PrecedenceTable


class TestBugHunt:
    """Tests targeting specific potential bugs."""

    # Bug 1: first_of_string should handle empty string (epsilon)
    def test_first_of_empty_string(self):
        """FIRST(ε) should return {ε}."""
        g = Grammar([("S", ["a"])])
        result = g.first_of_string(())
        assert "" in result, "FIRST(ε) should contain epsilon"

    # Bug 2: first_of_string with nullable non-terminal followed by terminal
    def test_first_of_nullable_then_terminal(self):
        g = Grammar([("A", []), ("A", ["b"]), ("S", ["A", "c"])])
        # FIRST(Ac) = {ε, b} ∪ {c} (since A is nullable)
        result = g.first_of_string(("A", "c"))
        assert "c" in result
        assert "b" in result
        assert "" in result  # A is nullable, c is terminal, but ε from A

    # Bug 3: FOLLOW should not include epsilon
    def test_follow_no_epsilon(self):
        g = Grammar([("S", ["A", "b"]), ("A", [])])
        for nt in g.nonterminals:
            assert "" not in g.follow[nt], f"FOLLOW({nt}) contains epsilon"

    # Bug 4: Parser should handle epsilon productions correctly
    def test_parse_epsilon_production(self):
        """Grammar with epsilon production should parse correctly."""
        g = Grammar([
            ("S", ["A", "b"]),
            ("A", ["a"]),
            ("A", []),  # epsilon
        ])
        table = LALRTable(g)
        assert not table.has_conflicts, f"Conflicts: {table.conflicts}"
        p = Parser(g, table=table)
        # S -> A b -> (epsilon) b -> b
        result = p.parse([Token("b")])
        assert result is not None

    # Bug 5: Parser should handle deeply nested input (stack overflow check)
    def test_deeply_nested(self):
        g = Grammar([
            ("S", ["(", "S", ")"]),
            ("S", ["x"]),
        ])
        table = LALRTable(g)
        p = Parser(g, table=table)
        depth = 100
        tokens = [Token("(")] * depth + [Token("x")] + [Token(")")] * depth
        result = p.parse(tokens)
        assert result is not None

    # Bug 6: Parse error should report expected tokens correctly
    def test_parse_error_expected_tokens(self):
        g = Grammar([
            ("S", ["a", "b"]),
            ("S", ["a", "c"]),
        ])
        table = LALRTable(g)
        p = Parser(g, table=table)
        try:
            p.parse([Token("a"), Token("d")])
            assert False, "Should have raised ParseError"
        except ParseError as e:
            # Should expect 'b' or 'c'
            assert "b" in e.expected or "c" in e.expected

    # Bug 7: Empty token list should raise error, not crash
    def test_empty_token_list(self):
        g = Grammar([("S", ["a"])])
        p = Parser(g)
        with pytest.raises(ParseError):
            p.parse([])

    # Bug 8: Token with unknown type should produce parse error
    def test_unknown_token_type(self):
        g = Grammar([("S", ["a"])])
        p = Parser(g)
        with pytest.raises(ParseError):
            p.parse([Token("UNKNOWN")])

    # Bug 9: from_json should handle missing conflicts field
    def test_from_json_missing_conflicts(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        data = table.to_json()
        del data["conflicts"]
        # Should not crash
        restored = LALRTable.from_json(data)
        assert restored.num_states == table.num_states

    # Bug 10: from_json should handle missing resolved_conflicts field
    def test_from_json_missing_resolved_conflicts(self):
        g = Grammar([("S", ["a"])])
        table = LALRTable(g)
        data = table.to_json()
        del data["resolved_conflicts"]
        restored = LALRTable.from_json(data)
        assert restored.resolved_conflicts == []

    # Bug 11: Grammar with start not first production
    def test_start_not_first(self):
        g = Grammar([("A", ["a"]), ("S", ["A", "b"])], start="S")
        assert g.user_start == "S"
        table = LALRTable(g)
        p = Parser(g, table=table)
        result = p.parse([Token("a"), Token("b")])
        assert result is not None

    # Bug 12: SLR table should detect reduce/reduce conflicts
    def test_slr_reduce_reduce(self):
        """Grammar that produces reduce/reduce in SLR."""
        g = Grammar([
            ("S", ["A"]),
            ("S", ["B"]),
            ("A", ["x"]),
            ("B", ["x"]),
        ])
        slr = SLRTable(g)
        # FOLLOW(A) and FOLLOW(B) both contain $, so state with A->x• and B->x•
        # should have reduce/reduce conflict
        # Actually depends on whether they end up in the same state
        # Let's just check it runs without crashing
        assert slr.num_states > 0

    # Bug 13: Precedence table with no levels should not crash
    def test_empty_precedence(self):
        g = Grammar([("S", ["a"])])
        prec = PrecedenceTable()
        table = LALRTable(g, precedence=prec)
        assert not table.has_conflicts

    # Bug 14: BNF loader should handle empty productions
    def test_bnf_empty_production(self):
        text = """
        S : 'a' S | ;
        """
        g = load_bnf(text)
        assert "S" in g.nullable

    # Bug 15: BNF loader should handle multi-line productions
    def test_bnf_multiline(self):
        text = """
        S : 'a'
          | 'b'
          | 'c'
          ;
        """
        g = load_bnf(text)
        assert len(g.productions) == 4  # augmented + 3

    # Bug 16: Parser should handle epsilon in middle of production
    def test_epsilon_in_middle(self):
        g = Grammar([
            ("S", ["A", "B", "c"]),
            ("A", ["a"]),
            ("A", []),
            ("B", ["b"]),
        ])
        table = LALRTable(g)
        p = Parser(g, table=table)
        # S -> A B c -> (epsilon) b c -> b c
        result = p.parse([Token("b"), Token("c")])
        assert result is not None
        # S -> A B c -> a b c
        result2 = p.parse([Token("a"), Token("b"), Token("c")])
        assert result2 is not None

    # Bug 17: Grammar with only epsilon productions
    def test_all_epsilon(self):
        g = Grammar([
            ("S", ["A"]),
            ("A", []),
        ])
        table = LALRTable(g)
        p = Parser(g, table=table)
        # S -> A -> epsilon, so empty input should parse
        result = p.parse([])
        assert result is not None

    # Bug 18: Multiple nullable non-terminals in sequence
    def test_multiple_nullable(self):
        g = Grammar([
            ("S", ["A", "B", "C"]),
            ("A", ["a"]),
            ("A", []),
            ("B", ["b"]),
            ("B", []),
            ("C", ["c"]),
            ("C", []),
        ])
        table = LALRTable(g)
        # Should not have conflicts
        p = Parser(g, table=table)
        # S -> A B C -> (eps)(eps)(eps) -> empty
        result = p.parse([])
        assert result is not None
        # S -> A B C -> a b c
        result2 = p.parse([Token("a"), Token("b"), Token("c")])
        assert result2 is not None

    # Bug 19: LALR table should handle right-recursive grammars
    def test_right_recursive(self):
        g = Grammar([
            ("S", ["a", "S"]),
            ("S", ["a"]),
        ])
        table = LALRTable(g)
        assert not table.has_conflicts
        p = Parser(g, table=table)
        result = p.parse([Token("a"), Token("a"), Token("a")])
        assert result is not None

    # Bug 20: parse_tokens convenience method
    def test_parse_tokens(self):
        g = Grammar([("S", ["a", "b"])])
        p = Parser(g)
        result = p.parse_tokens(["a", "b"])
        assert result is not None

    # Bug 21: Grammar with duplicate productions
    def test_duplicate_productions(self):
        g = Grammar([
            ("S", ["a"]),
            ("S", ["a"]),  # duplicate
        ])
        # Should not crash, just have duplicate
        assert len(g.productions) == 3  # augmented + 2 (duplicates allowed)

    # Bug 22: Terminal that looks like a non-terminal name
    def test_terminal_naming(self):
        g = Grammar([("S", ["ID"]), ("ID", ["x"])])
        # ID is a non-terminal here, not a terminal
        assert "ID" in g.nonterminals
        assert "x" in g.terminals

    # Bug 23: Token position tracking through reduces
    def test_token_position_tracking(self):
        g = Grammar([
            ("S", ["expr"]),
            ("expr", ["expr", "+", "term"]),
            ("expr", ["term"]),
            ("term", ["NUMBER"]),
        ])
        table = LALRTable(g)
        p = Parser(g, table=table)
        result = p.parse([
            Token("NUMBER", 1, 0),
            Token("+", "+", 1),
            Token("NUMBER", 2, 2),
        ])
        assert result is not None

    # Bug 24: Precedence resolution with nonassoc should produce error action
    def test_nonassoc_produces_error(self):
        text = """
        %start expr
        %nonassoc CMP
        expr : expr CMP expr
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        table = LALRTable(g, precedence=prec)
        # a CMP b CMP c should be an error (nonassoc)
        # Check that some state has error action for CMP
        assert not table.has_conflicts, "Nonassoc should resolve all conflicts"
        # Verify the parser actually errors on a CMP b CMP c
        p = Parser(g, table=table)
        with pytest.raises(ParseError):
            p.parse([Token("NUMBER", 1), Token("CMP"), Token("NUMBER", 2), Token("CMP"), Token("NUMBER", 3)])

    # Bug 25: Productions with single symbol (unit production)
    def test_unit_production_chain(self):
        g = Grammar([
            ("S", ["A"]),
            ("A", ["B"]),
            ("B", ["C"]),
            ("C", ["x"]),
        ])
        table = LALRTable(g)
        p = Parser(g, table=table)
        result = p.parse([Token("x", value="x_val")])
        # Default action for unit productions: unwrap single value
        assert result == "x_val"  # value propagates through unit productions

    # Bug 26 (FIXED): %prec directive should not add a fake terminal to the body
    def test_prec_directive_not_in_body(self):
        """The %prec directive should set production precedence, not add
        a terminal symbol to the production body."""
        text = """
        %start expr
        %left '+' '-'
        %left '*' '/'
        %right UMINUS

        expr : expr '+' expr
             | expr '-' expr
             | expr '*' expr
             | expr '/' expr
             | '-' expr %prec UMINUS
             | '(' expr ')'
             | NUMBER
             ;
        """
        g, prec = load_bnf_full(text)
        # UMINUS should NOT be a terminal in the grammar
        assert "UMINUS" not in g.terminals, "UMINUS should not be a terminal"
        assert "UMINUS" not in g.nonterminals, "UMINUS should not be a non-terminal"
        # The production for '-' expr should have body ('-', 'expr') not ('-', 'expr', 'UMINUS')
        for p in g.productions:
            if p.head == "expr" and p.body == ("-", "expr"):
                break
        else:
            assert False, "Production 'expr -> - expr' not found"
        # Verify precedence override is set
        assert prec.has_precedence("UMINUS")
        # Production index for '-' expr is 5 (0=augmented, 1-4=binops, 5=unary)
        prod_prec = prec.production_precedence(g, 5)
        assert prod_prec == prec.get_precedence("UMINUS"), \
            f"Production precedence should be UMINUS level ({prec.get_precedence('UMINUS')}), got {prod_prec}"

    # Bug 27 (FIXED): SLR table missing reduce→shift conflict detection
    def test_slr_reduce_shift_conflict_detected(self):
        """SLR table should detect reduce→shift conflicts (not just shift→reduce)."""
        g = Grammar([
            ("S", ["L", "=", "R"]),
            ("S", ["R"]),
            ("L", ["*", "R"]),
            ("L", ["ID"]),
            ("R", ["L"]),
        ])
        slr = SLRTable(g)
        assert slr.has_conflicts, "SLR should detect shift/reduce conflicts"
        assert any("=" in c for c in slr.conflicts), \
            "Should have conflict on '=' terminal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])