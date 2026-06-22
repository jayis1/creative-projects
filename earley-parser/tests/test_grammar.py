"""Tests for the Grammar class and related functionality."""
import pytest
from earley_parser import Grammar, GrammarLoader, GrammarStats, GrammarError, EMPTY


# -- Fixtures ---------------------------------------------------------------- #

@pytest.fixture
def expr_grammar():
    return Grammar.from_rules(
        start="E",
        rules=[
            ("E", ("E", "+", "E")),
            ("E", ("E", "*", "E")),
            ("E", ("(", "E", ")")),
            ("E", ("id",)),
        ],
        name="expr",
    )


@pytest.fixture
def balance_grammar():
    return Grammar.from_rules("S", [
        ("S", ("(", "S", ")")),
        ("S", ("S", "S")),
        ("S", ()),
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


# -- Construction ------------------------------------------------------------ #

class TestGrammarConstruction:
    def test_from_rules_basic(self, expr_grammar):
        assert expr_grammar.start == "E"
        assert len(expr_grammar.productions) == 1
        assert len(expr_grammar.productions["E"]) == 4

    def test_from_rules_accumulates(self):
        rules = [("A", ("a",)), ("A", ("b",)), ("A", ("c",))]
        g = Grammar.from_rules("A", rules)
        assert len(g.productions["A"]) == 3

    def test_add_rule(self, expr_grammar):
        before = len(expr_grammar.productions["E"])
        expr_grammar.add_rule("E", ("E", "-", "E"))
        assert len(expr_grammar.productions["E"]) == before + 1

    def test_add_rule_resets_caches(self, expr_grammar):
        expr_grammar.nullable()
        assert expr_grammar._nullable_cache is not None
        expr_grammar.add_rule("E", ("E", "-", "E"))
        assert expr_grammar._nullable_cache is None

    def test_terminals_inferred(self, expr_grammar):
        assert expr_grammar.is_terminal("id")
        assert expr_grammar.is_terminal("+")
        assert expr_grammar.is_terminal("*")
        assert expr_grammar.is_terminal("(")
        assert expr_grammar.is_terminal(")")

    def test_nonterminals_identified(self, expr_grammar):
        assert expr_grammar.is_nonterminal("E")
        assert not expr_grammar.is_nonterminal("id")

    def test_rhs_options(self, expr_grammar):
        opts = expr_grammar.rhs_options("E")
        assert ("id",) in opts
        assert ("E", "+", "E") in opts

    def test_all_symbols(self, expr_grammar):
        syms = expr_grammar.all_symbols()
        assert "E" in syms
        assert "id" in syms
        assert "+" in syms

    def test_terminal_set(self, expr_grammar):
        terms = expr_grammar.terminal_set()
        assert "id" in terms
        assert "E" not in terms

    def test_repr(self, expr_grammar):
        assert "Grammar(" in repr(expr_grammar)
        assert "nonterminals=1" in repr(expr_grammar)


# -- Nullable ---------------------------------------------------------------- #

class TestNullable:
    def test_no_nullable(self, expr_grammar):
        assert expr_grammar.nullable() == set()

    def test_nullable_epsilon(self, balance_grammar):
        assert "S" in balance_grammar.nullable()

    def test_nullable_midrule(self):
        g = Grammar.from_rules("A", [
            ("A", ("B", "C")),
            ("B", ("x",)),
            ("B", ()),
            ("C", ("c",)),
        ])
        nullable = g.nullable()
        # B is nullable (has epsilon), C is not (only derives "c"),
        # A is not nullable (C is not nullable)
        assert "B" in nullable
        assert "C" not in nullable
        assert "A" not in nullable

    def test_nullable_midrule_all_nullable(self):
        g = Grammar.from_rules("A", [
            ("A", ("B", "C")),
            ("B", ("x",)),
            ("B", ()),
            ("C", ("c",)),
            ("C", ()),
        ])
        nullable = g.nullable()
        assert "A" in nullable
        assert "B" in nullable
        assert "C" in nullable

    def test_is_nullable_symbol(self, balance_grammar):
        assert balance_grammar.is_nullable_symbol("S")
        assert not balance_grammar.is_nullable_symbol("(")

    def test_is_nullable_sequence(self):
        g = Grammar.from_rules("A", [
            ("A", ("B", "C")),
            ("B", ()),
            ("C", ()),
        ])
        assert g.is_nullable_sequence(("B", "C"))
        assert not g.is_nullable_sequence(("B", "x"))

    def test_nullable_caching(self, expr_grammar):
        result1 = expr_grammar.nullable()
        result2 = expr_grammar.nullable()
        assert result1 is result2  # same cached object


# -- FIRST Sets -------------------------------------------------------------- #

class TestFirstSets:
    def test_first_terminals(self, expr_grammar):
        first = expr_grammar.first()
        assert first["id"] == {"id"}
        assert first["+"] == {"+"}

    def test_first_nonterminal(self, expr_grammar):
        first = expr_grammar.first()
        assert "id" in first["E"]
        assert "(" in first["E"]

    def test_first_with_epsilon(self, balance_grammar):
        first = balance_grammar.first()
        assert EMPTY in first["S"]
        assert "(" in first["S"]

    def test_first_of_sequence(self, expr_grammar):
        first = expr_grammar.first_of_sequence(("E", "+", "E"))
        assert "id" in first
        assert "(" in first
        assert "+" not in first  # + is in FOLLOW, not FIRST

    def test_first_of_sequence_nullable(self):
        g = Grammar.from_rules("A", [
            ("A", ("B", "C")),
            ("B", ()),
            ("C", ("c",)),
        ])
        first = g.first_of_sequence(("B", "C"))
        assert "c" in first
        assert EMPTY not in first  # C is not nullable

    def test_first_caching(self, expr_grammar):
        r1 = expr_grammar.first()
        r2 = expr_grammar.first()
        assert r1 is r2


# -- FOLLOW Sets ------------------------------------------------------------- #

class TestFollowSets:
    def test_follow_has_endmarker(self, expr_grammar):
        follow = expr_grammar.follow()
        assert "$" in follow["E"]

    def test_follow_expr(self, expr_grammar):
        follow = expr_grammar.follow()
        # FOLLOW(E) should include +, *, ), $
        assert "+" in follow["E"]
        assert "*" in follow["E"]
        assert ")" in follow["E"]
        assert "$" in follow["E"]

    def test_follow_caching(self, expr_grammar):
        r1 = expr_grammar.follow()
        r2 = expr_grammar.follow()
        assert r1 is r2

    def test_follow_with_nullable(self, balance_grammar):
        follow = balance_grammar.follow()
        assert "$" in follow["S"]
        assert ")" in follow["S"]


# -- Productivity & Reachability --------------------------------------------- #

class TestProductivityReachability:
    def test_productive_grammar(self, expr_grammar):
        prod = expr_grammar.productive()
        assert "E" in prod

    def test_unproductive(self):
        g = Grammar.from_rules("S", [
            ("S", ("A",)),
            ("A", ("B",)),
            ("B", ("A",)),
        ])
        prod = g.productive()
        assert "S" not in prod
        assert "A" not in prod
        assert "B" not in prod

    def test_reachable(self, expr_grammar):
        reach = expr_grammar.reachable()
        assert "E" in reach

    def test_unreachable(self):
        g = Grammar.from_rules("S", [
            ("S", ("a",)),
            ("X", ("b",)),
        ])
        reach = g.reachable()
        assert "X" not in reach
        assert "S" in reach


# -- Validation -------------------------------------------------------------- #

class TestValidation:
    def test_valid_grammar(self, expr_grammar):
        assert expr_grammar.validate() == []
        assert expr_grammar.is_valid()

    def test_missing_start(self):
        """Start symbol with no productions should be detected."""
        g = Grammar(
            start="X",
            productions={"A": [("a",)]},
        )
        problems = g.validate()
        assert any("Start symbol" in p for p in problems)

    def test_unproductive_detected(self):
        g = Grammar.from_rules("S", [
            ("S", ("A",)),
            ("A", ("B",)),
            ("B", ("A",)),
        ])
        problems = g.validate()
        assert any("unproductive" in p for p in problems)

    def test_unreachable_detected(self):
        g = Grammar.from_rules("S", [
            ("S", ("a",)),
            ("X", ("b",)),
        ])
        problems = g.validate()
        assert any("unreachable" in p for p in problems)

    def test_terminal_conflict(self):
        g = Grammar(
            start="S",
            productions={"S": [("a",)]},
            terminals={"S"},
        )
        problems = g.validate()
        assert any("terminal but has productions" in p for p in problems)


# -- Stats ------------------------------------------------------------------- #

class TestGrammarStats:
    def test_stats(self, expr_grammar):
        stats = expr_grammar.stats()
        assert stats.nonterminal_count == 1
        assert stats.production_count == 4
        assert stats.terminal_count == 5
        assert stats.max_rhs_length == 3
        assert stats.avg_rhs_length == 2.5
        assert stats.unreachable == set()
        assert stats.unproductive == set()

    def test_stats_to_dict(self, expr_grammar):
        stats = expr_grammar.stats()
        d = stats.to_dict()
        assert d["nonterminal_count"] == 1
        assert d["production_count"] == 4

    def test_stats_repr(self, expr_grammar):
        stats = expr_grammar.stats()
        assert "GrammarStats" in repr(stats)


# -- Serialization ----------------------------------------------------------- #

class TestSerialization:
    def test_to_dict(self, expr_grammar):
        d = expr_grammar.to_dict()
        assert d["start"] == "E"
        assert "E" in d["productions"]
        assert d["name"] == "expr"

    def test_from_dict_roundtrip(self, expr_grammar):
        d = expr_grammar.to_dict()
        g2 = Grammar.from_dict(d)
        assert g2.start == expr_grammar.start
        assert g2.productions == expr_grammar.productions


# -- GrammarLoader ----------------------------------------------------------- #

class TestGrammarLoader:
    def test_load_basic(self):
        text = """
start ::= <E>

<E> ::= <E> "+" <E>
      | <E> "*" <E>
      | "(" <E> ")"
      | "id"
"""
        g = GrammarLoader.load(text)
        assert g.start == "E"
        assert len(g.productions["E"]) == 4

    def test_load_epsilon(self):
        text = """start ::= <S>

<S> ::= "(" <S> ")"
      | <S> <S>
      |
"""
        g = GrammarLoader.load(text)
        assert g.start == "S"
        assert () in g.productions["S"]

    def test_load_empty_raises(self):
        with pytest.raises(GrammarError):
            GrammarLoader.load("")

    def test_load_whitespace_only_raises(self):
        with pytest.raises(GrammarError):
            GrammarLoader.load("   \n  \n")

    def test_load_no_rules_raises(self):
        with pytest.raises(GrammarError):
            GrammarLoader.load("# just a comment\n")

    def test_load_invalid_line_raises(self):
        with pytest.raises(GrammarError):
            GrammarLoader.load("this is not valid\n")

    def test_load_invalid_lhs_raises(self):
        with pytest.raises(GrammarError):
            GrammarLoader.load("bad ::= <E>\n<E> ::= \"a\"")

    def test_load_file(self, tmp_path, expr_grammar):
        p = tmp_path / "test.bnf"
        p.write_text('start ::= <E>\n<E> ::= "a"\n')
        g = GrammarLoader.load_file(str(p))
        assert g.start == "E"
        assert g.name == "test"

    def test_load_single_quotes(self):
        text = """start ::= <E>

<E> ::= <E> '+' <E>
      | 'id'
"""
        g = GrammarLoader.load(text)
        assert ("id",) in g.productions["E"]
        assert ("E", "+", "E") in g.productions["E"]

    def test_load_bare_word_terminal(self):
        text = """start ::= <E>

<E> ::= <E> + <E>
      | id
"""
        g = GrammarLoader.load(text)
        assert ("id",) in g.productions["E"]
        assert ("E", "+", "E") in g.productions["E"]