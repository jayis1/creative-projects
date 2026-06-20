"""Comprehensive pytest test suite for the Datalog engine.

Run with: pytest -v
"""

import json
import os
import sys
import tempfile

import pytest

# Ensure the datalog package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datalog import (
    Engine,
    EngineConfig,
    DatalogError,
    SafetyError,
    StratificationError,
    parse,
    Variable,
    Constant,
    Atom,
    Rule,
    Literal,
)
from datalog.builtins import (
    is_arithmetic,
    is_comparison,
    is_string_builtin,
    is_typecheck,
    is_aggregate,
)
from datalog.config import load_config
from datalog.output import format_results
from datalog.aggregation import is_aggregate_rule


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #

@pytest.fixture
def graph_engine():
    """Engine with a simple graph for transitive closure tests."""
    e = Engine()
    e.add_source("""
        edge(a, b). edge(b, c). edge(c, d). edge(d, e).
        edge(a, c). edge(b, d). edge(c, e).
        path(X, Y) :- edge(X, Y).
        path(X, Y) :- edge(X, Z), path(Z, Y).
    """)
    return e


@pytest.fixture
def family_engine():
    """Engine with a family database."""
    e = Engine()
    e.add_source("""
        parent(tom, bob). parent(tom, liz).
        parent(bob, ann). parent(bob, pat).
        parent(pat, jim).
        male(tom). male(bob). male(jim).
        female(liz). female(ann). female(pat).
        ancestor(X, Y) :- parent(X, Y).
        ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
        sibling(X, Y) :- parent(Z, X), parent(Z, Y), X != Y.
    """)
    return e


# --------------------------------------------------------------------------- #
# Parser tests                                                               #
# --------------------------------------------------------------------------- #

class TestParser:
    def test_parse_facts(self):
        prog = parse("parent(tom, bob). parent(tom, liz).")
        assert len(prog.facts) == 2
        assert len(prog.rules) == 0
        assert prog.facts[0].atom.predicate == "parent"

    def test_parse_rule(self):
        prog = parse("ancestor(X, Y) :- parent(X, Y).")
        assert len(prog.rules) == 1
        assert prog.rules[0].head.predicate == "ancestor"
        assert len(prog.rules[0].body) == 1

    def test_parse_query(self):
        prog = parse("?- ancestor(tom, X).")
        assert len(prog.queries) == 1
        assert prog.queries[0].atom.predicate == "ancestor"

    def test_parse_query_no_dot(self):
        prog = parse("?- ancestor(tom, X)")
        assert len(prog.queries) == 1

    def test_parse_negation(self):
        prog = parse("childless(X) :- person(X), not parent(X, Y).")
        assert len(prog.rules) == 1
        assert not prog.rules[0].body[1].positive

    def test_parse_comparison_infix(self):
        prog = parse("big(X) :- num(X), X > 5.")
        assert len(prog.rules) == 1
        # Second body literal is the comparison
        assert prog.rules[0].body[1].atom.predicate == ">"

    def test_parse_comparison_prefix(self):
        prog = parse("big(X) :- num(X), >(X, 5).")
        assert len(prog.rules) == 1
        assert prog.rules[0].body[1].atom.predicate == ">"

    def test_parse_string_constant(self):
        prog = parse('name("hello").')
        assert prog.facts[0].atom.terms[0] == Constant("hello")

    def test_parse_int_constant(self):
        prog = parse("age(42).")
        assert prog.facts[0].atom.terms[0] == Constant(42)

    def test_parse_float_constant(self):
        prog = parse("pi(3.14).")
        assert prog.facts[0].atom.terms[0] == Constant(3.14)

    def test_parse_bool_constant(self):
        prog = parse("flag(true). flag(false).")
        assert prog.facts[0].atom.terms[0] == Constant(True)
        assert prog.facts[1].atom.terms[0] == Constant(False)

    def test_parse_line_comment(self):
        prog = parse("% this is a comment\nparent(tom, bob).")
        assert len(prog.facts) == 1

    def test_parse_block_comment(self):
        prog = parse("/* block comment */ parent(tom, bob).")
        assert len(prog.facts) == 1

    def test_parse_anonymous_variable(self):
        prog = parse("foo(X) :- bar(X, _).")
        # The _ should get a unique name
        body_var = prog.rules[0].body[0].atom.terms[1]
        assert isinstance(body_var, Variable)
        assert body_var.name != "_"

    def test_parse_lex_error(self):
        from datalog.parser import LexError
        with pytest.raises(LexError):
            parse("@@@")

    def test_parse_error_unexpected(self):
        from datalog.parser import ParseError
        with pytest.raises(ParseError):
            parse(":- parent(tom, bob).")

    def test_parse_unterminated_string(self):
        from datalog.parser import LexError
        with pytest.raises(LexError):
            parse('name("hello)')


# --------------------------------------------------------------------------- #
# AST tests                                                                  #
# --------------------------------------------------------------------------- #

class TestAST:
    def test_constant_equality(self):
        assert Constant(1) == Constant(1)
        assert Constant(1) == Constant(1.0)  # canonical equality
        assert Constant("a") == Constant("a")
        assert Constant(1) != Constant(2)

    def test_constant_hash(self):
        # 1 and 1.0 should hash the same (canonical)
        assert hash(Constant(1)) == hash(Constant(1.0))

    def test_atom_is_ground(self):
        a = Atom("p", [Constant("a"), Constant("b")])
        assert a.is_ground()
        a2 = Atom("p", [Variable("X"), Constant("b")])
        assert not a2.is_ground()

    def test_atom_variables(self):
        a = Atom("p", [Variable("X"), Constant("b"), Variable("Y")])
        vs = a.variables()
        assert len(vs) == 2

    def test_rule_safety(self):
        builtins = {">", "<", ">=", "<=", "!=", "==", "add", "sub", "mul",
                     "div", "idiv", "mod", "count", "sum", "min", "max", "avg",
                     "concat", "substr", "strlen", "is_int", "is_float",
                     "is_str", "is_bool"}
        arith = {"add", "sub", "mul", "div", "idiv", "mod",
                 "concat", "substr", "strlen", "count", "sum", "min", "max", "avg"}
        # Safe: X appears in positive body
        r = Rule(
            Atom("foo", [Variable("X")]),
            [Literal(Atom("bar", [Variable("X")]))],
        )
        assert r.is_safe(builtins, arith)

    def test_rule_unsafe_head(self):
        builtins = {">"}
        arith = set()
        # Unsafe: X only in comparison
        r = Rule(
            Atom("foo", [Variable("X")]),
            [Literal(Atom(">", [Variable("X"), Constant(5)]))],
        )
        assert not r.is_safe(builtins, arith)

    def test_rule_safe_with_arith(self):
        builtins = {"add", "mul"}
        arith = {"add", "mul"}
        # Safe: X in positive, Y bound by add
        r = Rule(
            Atom("foo", [Variable("X"), Variable("Y")]),
            [
                Literal(Atom("num", [Variable("X")])),
                Literal(Atom("add", [Variable("X"), Constant(5), Variable("Y")])),
            ],
        )
        assert r.is_safe(builtins, arith)


# --------------------------------------------------------------------------- #
# Engine — basic query tests                                                 #
# --------------------------------------------------------------------------- #

class TestEngineBasic:
    def test_transitive_closure(self, graph_engine):
        result = graph_engine.query("path(a, Y)")
        ys = sorted(r["Y"] for r in result)
        assert ys == ["b", "c", "d", "e"]

    def test_query_ground(self, graph_engine):
        result = graph_engine.query("path(a, b)")
        assert len(result) == 1
        assert result[0] == {}

    def test_query_nonexistent(self, graph_engine):
        result = graph_engine.query("path(z, Y)")
        assert result == []

    def test_query_wrong_arity(self, graph_engine):
        result = graph_engine.query("path(a)")
        assert result == []

    def test_query_unknown_predicate(self, graph_engine):
        result = graph_engine.query("unknown(X)")
        assert result == []

    def test_add_fact_programmatic(self):
        e = Engine()
        e.add_fact("edge", "a", "b")
        e.add_fact("edge", "b", "c")
        assert ("a", "b") in e.facts("edge")
        assert ("b", "c") in e.facts("edge")

    def test_retract_fact(self):
        e = Engine()
        e.add_fact("edge", "a", "b")
        assert e.retract_fact("edge", "a", "b") is True
        assert ("a", "b") not in e.facts("edge")
        assert e.retract_fact("edge", "a", "b") is False  # already removed

    def test_retract_fact_nonexistent(self):
        e = Engine()
        assert e.retract_fact("edge", "x", "y") is False

    def test_clear(self):
        e = Engine()
        e.add_source("edge(a, b). path(X,Y) :- edge(X,Y).")
        e.clear()
        assert e.predicates() == []
        assert e.rules() == []

    def test_predicates(self, family_engine):
        preds = family_engine.predicates()
        assert "parent" in preds
        assert "ancestor" in preds
        assert "sibling" in preds

    def test_arity(self, family_engine):
        assert family_engine.arity("parent") == 2
        assert family_engine.arity("ancestor") == 2
        assert family_engine.arity("unknown") is None

    def test_relation(self, family_engine):
        rel = family_engine.relation("parent")
        assert ("tom", "bob") in rel
        assert ("pat", "jim") in rel


# --------------------------------------------------------------------------- #
# Engine — negation tests                                                    #
# --------------------------------------------------------------------------- #

class TestNegation:
    def test_stratified_negation(self):
        e = Engine()
        e.add_source("""
            edge(a, b). edge(b, c). edge(c, a).
            out(X) :- edge(X, Y).
            sink(X) :- node(X), not out(X).
            node(a). node(b). node(c). node(d).
        """)
        sinks = e.relation("sink")
        assert ("d",) in sinks
        assert ("a",) not in sinks

    def test_non_stratifiable(self):
        e = Engine()
        e.add_source("""
            p(X) :- q(X), not p(X).
            q(1).
        """)
        with pytest.raises(StratificationError):
            e.query("p(X)")

    def test_negated_comparison(self):
        e = Engine()
        e.add_source("""
            num(1). num(2). num(3). num(4). num(5).
            not_big(X) :- num(X), not X > 3.
        """)
        result = sorted(e.relation("not_big"))
        assert result == [(1,), (2,), (3,)]


# --------------------------------------------------------------------------- #
# Engine — built-in tests                                                    #
# --------------------------------------------------------------------------- #

class TestBuiltins:
    def test_comparison_gt(self):
        e = Engine()
        e.add_source("num(1). num(2). num(3). num(4). num(5). big(X) :- num(X), X > 3.")
        assert set(e.relation("big")) == {(4,), (5,)}

    def test_comparison_lt(self):
        e = Engine()
        e.add_source("num(1). num(2). num(3). small(X) :- num(X), X < 3.")
        assert set(e.relation("small")) == {(1,), (2,)}

    def test_comparison_ge(self):
        e = Engine()
        e.add_source("num(1). num(2). num(3). ge(X) :- num(X), X >= 2.")
        assert set(e.relation("ge")) == {(2,), (3,)}

    def test_comparison_le(self):
        e = Engine()
        e.add_source("num(1). num(2). num(3). le(X) :- num(X), X <= 2.")
        assert set(e.relation("le")) == {(1,), (2,)}

    def test_comparison_neq(self):
        e = Engine()
        e.add_source('pair(a, b). pair(a, a). diff(X, Y) :- pair(X, Y), X != Y.')
        assert set(e.relation("diff")) == {("a", "b")}

    def test_comparison_eq(self):
        e = Engine()
        e.add_source('pair(a, b). pair(a, a). same(X, Y) :- pair(X, Y), X == Y.')
        assert set(e.relation("same")) == {("a", "a")}

    def test_arith_add(self):
        e = Engine()
        e.add_source("num(1). num(2). num(3). plus(X, Y) :- num(X), add(X, 5, Y).")
        assert set(e.relation("plus")) == {(1, 6), (2, 7), (3, 8)}

    def test_arith_mul(self):
        e = Engine()
        e.add_source("num(1). num(2). num(3). dbl(X, Y) :- num(X), mul(X, 2, Y).")
        assert set(e.relation("dbl")) == {(1, 2), (2, 4), (3, 6)}

    def test_arith_sub(self):
        e = Engine()
        e.add_source("num(10). num(20). minus(X, Y) :- num(X), sub(X, 3, Y).")
        assert set(e.relation("minus")) == {(10, 7), (20, 17)}

    def test_arith_div_by_zero(self):
        e = Engine()
        e.add_source("num(1). num(0). safe_div(X, Y) :- num(X), num(Y), div(X, Y, Z).")
        # div by zero should fail gracefully (no result for Y=0)
        # But this rule has Z in head — need a rule that outputs Z
        e2 = Engine()
        e2.add_source("""
            num(1). num(0).
            result(X, Y, Z) :- num(X), num(Y), div(X, Y, Z).
        """)
        rel = e2.relation("result")
        # Only (1, 1, 1.0) should be present, not (1, 0, ...)
        assert (1, 0) not in [(t[0], t[1]) for t in rel]

    def test_arith_check_mode(self):
        e = Engine()
        e.add_source("num(1). num(2). num(3). check_add(X) :- num(X), add(X, 1, 2).")
        # add(X, 1, 2) checks if X+1 == 2, so only X=1 passes
        assert set(e.relation("check_add")) == {(1,)}

    def test_string_concat(self):
        e = Engine()
        e.add_source('name(hello). name(world). greet(X, Y) :- name(X), concat(X, "!", Y).')
        assert ("hello", "hello!") in e.relation("greet")
        assert ("world", "world!") in e.relation("greet")

    def test_string_strlen(self):
        e = Engine()
        e.add_source('name(hello). name(hi). len(X, N) :- name(X), strlen(X, 0, N).')
        assert ("hello", 5) in e.relation("len")
        assert ("hi", 2) in e.relation("len")

    def test_typecheck_is_int(self):
        e = Engine()
        e.add_source("val(1). val(hello). val(3.14). intval(X) :- val(X), is_int(X).")
        assert set(e.relation("intval")) == {(1,)}

    def test_typecheck_is_str(self):
        e = Engine()
        e.add_source("val(1). val(hello). val(3.14). strval(X) :- val(X), is_str(X).")
        assert set(e.relation("strval")) == {("hello",)}

    def test_typecheck_is_float(self):
        e = Engine()
        e.add_source("val(1). val(hello). val(3.14). fltval(X) :- val(X), is_float(X).")
        assert set(e.relation("fltval")) == {(3.14,)}

    def test_typecheck_is_bool(self):
        e = Engine()
        e.add_source("val(true). val(1). val(hello). boolval(X) :- val(X), is_bool(X).")
        assert set(e.relation("boolval")) == {(True,)}


# --------------------------------------------------------------------------- #
# Engine — aggregation tests                                                 #
# --------------------------------------------------------------------------- #

class TestAggregation:
    @pytest.fixture
    def company_engine(self):
        e = Engine()
        e.add_source("""
            employee(alice, engineering, 90000).
            employee(bob, engineering, 75000).
            employee(carol, engineering, 85000).
            employee(dave, sales, 65000).
            employee(eve, sales, 70000).
        """)
        return e

    def test_count(self, company_engine):
        prog = parse("dept_count(Dept, N) :- employee(Name, Dept, Sal), count(Name, N).")
        company_engine.add_rule(prog.rules[0])
        result = sorted(company_engine.relation("dept_count"))
        assert ("engineering", 3) in result
        assert ("sales", 2) in result

    def test_sum(self, company_engine):
        prog = parse("dept_total(Dept, Total) :- employee(Name, Dept, Sal), sum(Sal, Total).")
        company_engine.add_rule(prog.rules[0])
        result = dict(company_engine.relation("dept_total"))
        assert result["engineering"] == 250000
        assert result["sales"] == 135000

    def test_min(self, company_engine):
        prog = parse("dept_min(Dept, MinSal) :- employee(Name, Dept, Sal), min(Sal, MinSal).")
        company_engine.add_rule(prog.rules[0])
        result = dict(company_engine.relation("dept_min"))
        assert result["engineering"] == 75000
        assert result["sales"] == 65000

    def test_max(self, company_engine):
        prog = parse("dept_max(Dept, MaxSal) :- employee(Name, Dept, Sal), max(Sal, MaxSal).")
        company_engine.add_rule(prog.rules[0])
        result = dict(company_engine.relation("dept_max"))
        assert result["engineering"] == 90000
        assert result["sales"] == 70000

    def test_is_aggregate_rule(self):
        prog = parse("dept_count(Dept, N) :- employee(Name, Dept, Sal), count(Name, N).")
        assert is_aggregate_rule(prog.rules[0]) is True

    def test_not_aggregate_rule(self):
        prog = parse("path(X, Y) :- edge(X, Y).")
        assert is_aggregate_rule(prog.rules[0]) is False


# --------------------------------------------------------------------------- #
# Engine — JSON I/O tests                                                    #
# --------------------------------------------------------------------------- #

class TestJSONIO:
    def test_export_import_roundtrip(self):
        e = Engine()
        e.add_source("""
            edge(a, b). edge(b, c).
            path(X, Y) :- edge(X, Y).
            path(X, Y) :- edge(X, Z), path(Z, Y).
        """)
        j = e.to_json()
        e2 = Engine()
        e2.from_json(j)
        assert set(e2.relation("path")) == set(e.relation("path"))

    def test_export_structure(self):
        e = Engine()
        e.add_source("edge(a, b). edge(b, c).")
        j = json.loads(e.to_json())
        assert "facts" in j
        assert "rules" in j
        assert "edge" in j["facts"]
        assert j["facts"]["edge"]["arity"] == 2

    def test_import_invalid_json(self):
        e = Engine()
        with pytest.raises(DatalogError):
            e.from_json("{not valid json")

    def test_import_non_object(self):
        e = Engine()
        with pytest.raises(DatalogError):
            e.from_json("[1, 2, 3]")

    def test_import_bad_fact_entry(self):
        e = Engine()
        with pytest.raises(DatalogError):
            e.from_json('{"facts": {"bad": "not a dict with tuples"}}')


# --------------------------------------------------------------------------- #
# Engine — safety checks                                                     #
# --------------------------------------------------------------------------- #

class TestSafety:
    def test_unsafe_rule_rejected(self):
        e = Engine()
        with pytest.raises(SafetyError):
            e.add_source("foo(X) :- X > 5.")

    def test_safe_arith_rule_accepted(self):
        e = Engine()
        e.add_source("num(1). num(2). foo(X, Y) :- num(X), add(X, 5, Y).")
        assert len(e.rules()) == 1


# --------------------------------------------------------------------------- #
# Engine — introspection tests                                               #
# --------------------------------------------------------------------------- #

class TestIntrospection:
    def test_explain_idb(self, graph_engine):
        text = graph_engine.explain("path")
        assert "path/2" in text
        assert "IDB" in text
        assert "Rules:" in text

    def test_explain_edb(self, graph_engine):
        text = graph_engine.explain("edge")
        assert "edge/2" in text
        assert "EDB" in text

    def test_explain_unknown(self, graph_engine):
        text = graph_engine.explain("nonexistent")
        assert "unknown" in text

    def test_rules_listing(self, graph_engine):
        rules = graph_engine.rules()
        assert len(rules) == 2
        assert all(r.head.predicate == "path" for r in rules)

    def test_facts(self, graph_engine):
        facts = graph_engine.facts("edge")
        assert len(facts) == 7

    def test_stats(self, graph_engine):
        stats = graph_engine.stats()
        assert stats["predicates"] >= 2
        assert stats["rules"] == 2
        assert stats["total_facts"] == 7
        assert stats["strata"] >= 1


# --------------------------------------------------------------------------- #
# Config tests                                                               #
# --------------------------------------------------------------------------- #

class TestConfig:
    def test_config_defaults(self):
        c = EngineConfig()
        assert c.log_level == "WARNING"
        assert c.max_iterations == 100000
        assert c.output_format == "binding"

    def test_config_from_dict(self):
        c = EngineConfig.from_dict({"log_level": "DEBUG", "max_iterations": 100})
        assert c.log_level == "DEBUG"
        assert c.max_iterations == 100

    def test_config_json_file(self, tmp_path):
        config_file = tmp_path / "test.json"
        config_file.write_text('{"log_level": "INFO", "queries": ["path(a,Y)"]}')
        c = load_config(str(config_file))
        assert c.log_level == "INFO"
        assert c.queries == ["path(a,Y)"]

    def test_config_toml_file(self, tmp_path):
        config_file = tmp_path / "test.toml"
        config_file.write_text('log_level = "DEBUG"\nmax_iterations = 50')
        c = load_config(str(config_file))
        assert c.log_level == "DEBUG"
        assert c.max_iterations == 50

    def test_config_unsupported_format(self, tmp_path):
        config_file = tmp_path / "test.txt"
        config_file.write_text("invalid")
        from datalog.errors import ConfigurationError
        with pytest.raises(ConfigurationError):
            load_config(str(config_file))

    def test_config_nonexistent_file(self):
        from datalog.errors import ConfigurationError
        with pytest.raises(ConfigurationError):
            load_config("/nonexistent/path.json")

    def test_config_invalid_json(self, tmp_path):
        config_file = tmp_path / "bad.json"
        config_file.write_text("{invalid")
        from datalog.errors import ConfigurationError
        with pytest.raises(ConfigurationError):
            load_config(str(config_file))


# --------------------------------------------------------------------------- #
# Output formatting tests                                                    #
# --------------------------------------------------------------------------- #

class TestOutput:
    def test_binding_format(self):
        result = format_results([{"X": "a", "Y": 1}], "binding")
        assert "X = 'a'" in result
        assert "Y = 1" in result

    def test_binding_empty(self):
        result = format_results([], "binding")
        assert result == "false."

    def test_json_format(self):
        result = format_results([{"X": 1, "Y": "a"}], "json")
        data = json.loads(result)
        assert data == [{"X": 1, "Y": "a"}]

    def test_csv_format(self):
        result = format_results([{"X": 1, "Y": "a"}, {"X": 2, "Y": "b"}], "csv")
        assert "X,Y" in result
        assert "1,a" in result

    def test_table_format(self):
        result = format_results([{"X": "a"}], "table")
        assert "X" in result
        assert "a" in result
        assert "+" in result  # table border

    def test_unknown_format(self):
        with pytest.raises(ValueError):
            format_results([], "unknown")


# --------------------------------------------------------------------------- #
# Builtins registry tests                                                    #
# --------------------------------------------------------------------------- #

class TestBuiltinRegistry:
    def test_is_comparison(self):
        assert is_comparison(">")
        assert is_comparison("<")
        assert not is_comparison("add")

    def test_is_arithmetic(self):
        assert is_arithmetic("add")
        assert is_arithmetic("mul")
        assert not is_arithmetic(">")

    def test_is_string_builtin(self):
        assert is_string_builtin("concat")
        assert is_string_builtin("strlen")
        assert not is_string_builtin("add")

    def test_is_typecheck(self):
        assert is_typecheck("is_int")
        assert is_typecheck("is_str")
        assert not is_typecheck("add")

    def test_is_aggregate(self):
        assert is_aggregate("count")
        assert is_aggregate("sum")
        assert not is_aggregate("add")


# --------------------------------------------------------------------------- #
# Edge case / regression tests                                               #
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    def test_edb_idb_same_predicate(self):
        """Predicate with both base facts and rules should union both."""
        e = Engine()
        e.add_source("""
            edge(a, b). edge(b, c).
            edge(X, Y) :- extra(X, Y).
            extra(c, d).
        """)
        result = e.relation("edge")
        assert ("a", "b") in result
        assert ("b", "c") in result
        assert ("c", "d") in result

    def test_mutual_recursion_even_odd(self):
        e = Engine()
        e.add_source("""
            num(0). num(1). num(2). num(3). num(4). num(5).
            even(0).
            even(X) :- num(X), odd(Y), add(Y, 1, X).
            odd(X) :- num(X), even(Y), add(Y, 1, X).
        """)
        evens = set(e.relation("even"))
        odds = set(e.relation("odd"))
        assert (0,) in evens
        assert (1,) in odds
        assert (2,) in evens

    def test_empty_engine_query(self):
        e = Engine()
        assert e.query("foo(X)") == []

    def test_retract_rule(self):
        e = Engine()
        e.add_source("path(X, Y) :- edge(X, Y).")
        rules = e.rules()
        assert e.retract_rule(rules[0]) is True
        assert len(e.rules()) == 0

    def test_arity_mismatch_error(self):
        e = Engine()
        e.add_source("edge(a, b).")
        with pytest.raises(DatalogError):
            e.add_source("edge(a, b, c).")

    def test_facts_must_be_ground(self):
        from datalog.parser import ParseError
        e = Engine()
        with pytest.raises(ParseError):
            e.add_source("foo(X).")

    def test_cycle_detection(self):
        e = Engine()
        e.add_source("""
            edge(a, b). edge(b, c). edge(c, a).
            path(X, Y) :- edge(X, Y).
            path(X, Y) :- edge(X, Z), path(Z, Y).
            on_cycle(X) :- edge(X, Y), path(Y, X).
        """)
        cycles = e.relation("on_cycle")
        assert ("a",) in cycles
        assert ("b",) in cycles
        assert ("c",) in cycles

    def test_max_iterations_limit(self):
        e = Engine(EngineConfig(max_iterations=1))
        # A simple transitive closure should work in few iterations,
        # but let's test the limit is respected
        e.add_source("""
            edge(a, b). edge(b, c). edge(c, d). edge(d, e). edge(e, f).
            edge(f, g). edge(g, h).
            path(X, Y) :- edge(X, Y).
            path(X, Y) :- edge(X, Z), path(Z, Y).
        """)
        with pytest.raises(DatalogError):
            e.query("path(a, Y)")

    def test_load_file(self, tmp_path):
        src_file = tmp_path / "test.dl"
        src_file.write_text("edge(a, b). path(X, Y) :- edge(X, Y).")
        e = Engine()
        e.load_file(str(src_file))
        assert ("a", "b") in e.facts("edge")
        assert e.query("path(a, Y)") == [{"Y": "b"}]