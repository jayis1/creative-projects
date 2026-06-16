"""Tests for the mini-Prolog engine."""

import pytest
from prolog_engine.lexer import Lexer, TokenType, Token, LexerError
from prolog_engine.parser import Parser, ParseError
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Clause, Query, Program,
    variables_in, substitute, term_to_str,
)
from prolog_engine.unifier import Unifier, Substitution, UnificationError
from prolog_engine.engine import Engine, EngineError
from prolog_engine.builtins import register_builtins


# ==================================================================
# Lexer tests
# ==================================================================

class TestLexer:
    def test_atom(self):
        tokens = Lexer("hello").tokens
        assert tokens[0].type == TokenType.ATOM
        assert tokens[0].value == "hello"

    def test_variable(self):
        tokens = Lexer("X").tokens
        assert tokens[0].type == TokenType.VARIABLE
        assert tokens[0].value == "X"

    def test_anonymous_variable(self):
        tokens = Lexer("_").tokens
        assert tokens[0].type == TokenType.VARIABLE
        assert tokens[0].value == "_"

    def test_number_integer(self):
        tokens = Lexer("42").tokens
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "42"

    def test_number_float(self):
        tokens = Lexer("3.14").tokens
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "3.14"

    def test_string(self):
        tokens = Lexer('"hello world"').tokens
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello world"

    def test_string_escape(self):
        tokens = Lexer(r'"hello\nworld"').tokens
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello\nworld"

    def test_neck(self):
        tokens = Lexer(":-").tokens
        assert tokens[0].type == TokenType.NECK
        assert tokens[0].value == ":-"

    def test_query_marker(self):
        tokens = Lexer("?-").tokens
        assert tokens[0].type == TokenType.QUERY
        assert tokens[0].value == "?-"

    def test_brackets(self):
        tokens = Lexer("[]").tokens
        types = [t.type for t in tokens]
        assert TokenType.LBRACKET in types
        assert TokenType.RBRACKET in types

    def test_parens(self):
        tokens = Lexer("()").tokens
        types = [t.type for t in tokens]
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types

    def test_comma(self):
        tokens = Lexer(",").tokens
        assert tokens[0].type == TokenType.COMMA

    def test_dot(self):
        tokens = Lexer(".").tokens
        assert tokens[0].type == TokenType.DOT

    def test_pipe(self):
        tokens = Lexer("|").tokens
        assert tokens[0].type == TokenType.PIPE

    def test_line_comment(self):
        tokens = Lexer("hello % this is a comment\nworld").tokens
        atoms = [t.value for t in tokens if t.type in (TokenType.ATOM, TokenType.EOF)]
        assert "hello" in atoms
        assert "world" in atoms

    def test_block_comment(self):
        tokens = Lexer("hello /* comment */ world").tokens
        atoms = [t.value for t in tokens if t.type in (TokenType.ATOM, TokenType.EOF)]
        assert "hello" in atoms
        assert "world" in atoms

    def test_quoted_atom(self):
        tokens = Lexer("'hello world'").tokens
        assert tokens[0].type == TokenType.ATOM
        assert tokens[0].value == "hello world"

    def test_operator_atom(self):
        tokens = Lexer("+").tokens
        assert tokens[0].type == TokenType.ATOM
        assert tokens[0].value == "+"

    def test_invalid_char(self):
        with pytest.raises(LexerError):
            Lexer("`")

    def test_unterminated_string(self):
        with pytest.raises(LexerError):
            Lexer('"hello')

    def test_complex_clause(self):
        tokens = Lexer("parent(X, Y) :- father(X, Y).").tokens
        assert tokens[0].value == "parent"
        assert tokens[1].type == TokenType.LPAREN
        assert tokens[2].type == TokenType.VARIABLE
        # tokens[0]=parent, [1]=(, [2]=X, [3]=comma, [4]=Y, [5]=), [6]=:-
        assert tokens[6].type == TokenType.NECK


# ==================================================================
# Parser tests
# ==================================================================

class TestParser:
    def test_fact(self):
        parser = Parser.from_source("hello.")
        program = parser.parse_program()
        assert len(program.clauses) == 1
        assert program.clauses[0].is_fact
        assert program.clauses[0].head.name == "hello"

    def test_compound_fact(self):
        parser = Parser.from_source("parent(tom, bob).")
        program = parser.parse_program()
        assert len(program.clauses) == 1
        clause = program.clauses[0]
        assert clause.is_fact
        assert clause.head.name == "parent"
        assert clause.head.arity == 2
        assert clause.head.args[0] == Atom("tom")
        assert clause.head.args[1] == Atom("bob")

    def test_rule(self):
        parser = Parser.from_source("grandparent(X, Z) :- parent(X, Y), parent(Y, Z).")
        program = parser.parse_program()
        assert len(program.clauses) == 1
        clause = program.clauses[0]
        assert not clause.is_fact
        assert clause.head.name == "grandparent"
        assert len(clause.body) == 2

    def test_query(self):
        parser = Parser.from_source("?- parent(X, Y).")
        query = parser.parse_query()
        assert len(query.goals) == 1
        assert query.goals[0].name == "parent"

    def test_number_term(self):
        parser = Parser.from_source("age(42).")
        program = parser.parse_program()
        clause = program.clauses[0]
        assert clause.head.args[0] == Number(42)

    def test_string_term(self):
        parser = Parser.from_source('name("hello").')
        program = parser.parse_program()
        clause = program.clauses[0]
        assert clause.head.args[0] == String("hello")

    def test_empty_list(self):
        parser = Parser.from_source("f([]).")
        program = parser.parse_program()
        clause = program.clauses[0]
        assert clause.head.args[0] == Atom("[]")

    def test_list(self):
        parser = Parser.from_source("f([a, b, c]).")
        program = parser.parse_program()
        clause = program.clauses[0]
        lst = clause.head.args[0]
        assert isinstance(lst, Compound)
        assert lst.name == "."
        assert lst.args[0] == Atom("a")
        assert lst.args[1].args[0] == Atom("b")

    def test_list_with_tail(self):
        parser = Parser.from_source("f([a | T]).")
        program = parser.parse_program()
        clause = program.clauses[0]
        lst = clause.head.args[0]
        assert isinstance(lst, Compound)
        assert lst.args[0] == Atom("a")
        assert isinstance(lst.args[1], Variable)
        assert lst.args[1].name == "T"

    def test_infix_unification(self):
        parser = Parser.from_source("?- X = hello.")
        query = parser.parse_query()
        assert len(query.goals) == 1
        goal = query.goals[0]
        assert isinstance(goal, Compound)
        assert goal.name == "="
        assert goal.arity == 2

    def test_infix_arithmetic(self):
        parser = Parser.from_source("?- X is 3 + 4 * 2.")
        query = parser.parse_query()
        assert len(query.goals) == 1
        # Should parse as: X is (3 + (4 * 2))
        goal = query.goals[0]
        assert isinstance(goal, Compound)
        assert goal.name == "is"

    def test_infix_comparison(self):
        parser = Parser.from_source("?- 3 < 5.")
        query = parser.parse_query()
        assert len(query.goals) == 1
        goal = query.goals[0]
        assert isinstance(goal, Compound)
        assert goal.name == "<"


# ==================================================================
# Unifier tests
# ==================================================================

class TestUnifier:
    def test_unify_atoms(self):
        subst = Unifier.unify(Atom("a"), Atom("a"))
        assert len(subst) == 0

    def test_unify_atoms_fail(self):
        with pytest.raises(UnificationError):
            Unifier.unify(Atom("a"), Atom("b"))

    def test_unify_variable(self):
        X = Variable("X")
        subst = Unifier.unify(X, Atom("a"))
        assert subst.apply(X) == Atom("a")

    def test_unify_two_variables(self):
        X = Variable("X")
        Y = Variable("Y")
        subst = Unifier.unify(X, Y)
        assert len(subst) == 1

    def test_unify_compounds(self):
        X = Variable("X")
        Y = Variable("Y")
        t1 = Compound("f", (Atom("a"), X))
        t2 = Compound("f", (Y, Atom("b")))
        subst = Unifier.unify(t1, t2)
        assert subst.apply(X) == Atom("b")
        assert subst.apply(Y) == Atom("a")

    def test_unify_compound_arity_mismatch(self):
        t1 = Compound("f", (Atom("a"),))
        t2 = Compound("f", (Atom("a"), Atom("b")))
        with pytest.raises(UnificationError):
            Unifier.unify(t1, t2)

    def test_unify_compound_name_mismatch(self):
        t1 = Compound("f", (Atom("a"),))
        t2 = Compound("g", (Atom("a"),))
        with pytest.raises(UnificationError):
            Unifier.unify(t1, t2)

    def test_occurs_check(self):
        X = Variable("X")
        t = Compound("f", (X,))
        with pytest.raises(UnificationError):
            Unifier.unify(X, t)

    def test_substitution_compose(self):
        X = Variable("X")
        Y = Variable("Y")
        s1 = Substitution({X: Atom("a")})
        s2 = Substitution({Y: Atom("b")})
        result = s1.compose(s2)
        assert result.apply(X) == Atom("a")
        assert result.apply(Y) == Atom("b")

    def test_match_success(self):
        X = Variable("X")
        result = Unifier.match(Compound("f", (X,)), Compound("f", (Atom("a"),)))
        assert result is not None
        assert result.apply(X) == Atom("a")

    def test_match_failure(self):
        result = Unifier.match(Atom("a"), Atom("b"))
        assert result is None


# ==================================================================
# Engine tests
# ==================================================================

class TestEngine:
    def _make_engine(self) -> Engine:
        engine = Engine()
        register_builtins(engine)
        return engine

    def test_simple_fact(self):
        engine = self._make_engine()
        engine.load_source("parent(tom, bob).")
        results = engine.query("?- parent(tom, bob).")
        assert len(results) > 0

    def test_simple_fact_fail(self):
        engine = self._make_engine()
        engine.load_source("parent(tom, bob).")
        results = engine.query("?- parent(tom, liz).")
        assert len(results) == 0

    def test_query_with_variable(self):
        engine = self._make_engine()
        engine.load_source("""
            parent(tom, bob).
            parent(tom, liz).
        """)
        results = engine.query("?- parent(tom, X).")
        assert len(results) == 2

    def test_rule(self):
        engine = self._make_engine()
        engine.load_source("""
            parent(tom, bob).
            parent(bob, ann).
            grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
        """)
        results = engine.query("?- grandparent(tom, Z).")
        assert len(results) == 1

    def test_arithmetic_is(self):
        engine = self._make_engine()
        results = engine.query("?- X is 3 + 4.")
        assert len(results) == 1
        x_val = results[0].apply(Variable("X"))
        assert isinstance(x_val, Number)
        assert x_val.value == 7

    def test_arithmetic_precedence(self):
        engine = self._make_engine()
        results = engine.query("?- X is 3 + 4 * 2.")
        assert len(results) == 1
        x_val = results[0].apply(Variable("X"))
        assert isinstance(x_val, Number)
        assert x_val.value == 11  # 3 + (4*2)

    def test_arithmetic_comparison(self):
        engine = self._make_engine()
        results = engine.query("?- 3 < 5.")
        assert len(results) == 1
        results = engine.query("?- 5 < 3.")
        assert len(results) == 0

    def test_arithmetic_le(self):
        engine = self._make_engine()
        results = engine.query("?- 3 =< 5.")
        assert len(results) == 1

    def test_arithmetic_ge(self):
        engine = self._make_engine()
        results = engine.query("?- 5 >= 3.")
        assert len(results) == 1

    def test_unification_builtin(self):
        engine = self._make_engine()
        results = engine.query("?- X = hello.")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Atom("hello")

    def test_not_unifiable(self):
        engine = self._make_engine()
        results = engine.query("?- a \\= b.")
        assert len(results) == 1

    def test_type_checks(self):
        engine = self._make_engine()
        assert len(engine.query("?- atom(hello).")) == 1
        assert len(engine.query("?- atom(42).")) == 0
        assert len(engine.query("?- number(42).")) == 1
        assert len(engine.query("?- number(hello).")) == 0

    def test_fail(self):
        engine = self._make_engine()
        assert len(engine.query("?- fail.")) == 0

    def test_true(self):
        engine = self._make_engine()
        assert len(engine.query("?- true.")) == 1

    def test_not_builtin(self):
        engine = self._make_engine()
        engine.load_source("a(1).")
        results = engine.query("?- not(a(2)).")
        assert len(results) == 1

    def test_length_builtin(self):
        engine = self._make_engine()
        results = engine.query("?- length([a, b, c], N).")
        assert len(results) == 1
        n = results[0].apply(Variable("N"))
        assert isinstance(n, Number)
        assert n.value == 3

    def test_member_builtin(self):
        engine = self._make_engine()
        results = engine.query("?- member(X, [a, b, c]).")
        assert len(results) == 3
        values = [results[i].apply(Variable("X")) for i in range(3)]
        assert Atom("a") in values
        assert Atom("b") in values
        assert Atom("c") in values

    def test_append_builtin(self):
        engine = self._make_engine()
        results = engine.query("?- append([a, b], [c, d], R).")
        assert len(results) == 1

    def test_functor_builtin(self):
        engine = self._make_engine()
        results = engine.query("?- functor(f(a, b), Name, Arity).")
        assert len(results) == 1
        name = results[0].apply(Variable("Name"))
        arity = results[0].apply(Variable("Arity"))
        assert name == Atom("f")
        assert arity == Number(2)

    def test_arg_builtin(self):
        engine = self._make_engine()
        results = engine.query("?- arg(1, f(a, b), X).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Atom("a")

    def test_conjunction(self):
        engine = self._make_engine()
        engine.load_source("""
            a(1).
            b(1).
        """)
        results = engine.query("?- a(X), b(X).")
        assert len(results) == 1

    def test_recursive_rule(self):
        engine = self._make_engine()
        engine.load_source("""
            ancestor(X, Y) :- parent(X, Y).
            ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).
            parent(a, b).
            parent(b, c).
            parent(c, d).
        """)
        results = engine.query("?- ancestor(a, Z).")
        assert len(results) == 3  # b, c, d

    def test_format_solution(self):
        engine = self._make_engine()
        engine.load_source("parent(tom, bob).")
        results = engine.query("?- parent(tom, X).")
        assert len(results) == 1
        solution = engine.format_solution(results[0])
        assert "X" in solution


# ==================================================================
# Enhanced feature tests
# ==================================================================

class TestEnhancedBuiltins:
    def _make_engine(self) -> Engine:
        engine = Engine()
        register_builtins(engine)
        return engine

    # --- Type checking additions ---

    def test_atomic(self):
        engine = self._make_engine()
        assert len(engine.query("?- atomic(hello).")) == 1
        assert len(engine.query("?- atomic(42).")) == 1
        assert len(engine.query("?- atomic(f(a)).")) == 0

    def test_ground(self):
        engine = self._make_engine()
        assert len(engine.query("?- ground(f(a, b)).")) == 1
        assert len(engine.query("?- ground(f(X)).")) == 0

    # --- Control flow additions ---

    def test_once(self):
        engine = self._make_engine()
        engine.load_source("""
            a(1).
            a(2).
            a(3).
        """)
        results = engine.query("?- once(a(X)).")
        assert len(results) == 1

    def test_forall(self):
        engine = self._make_engine()
        engine.load_source("""
            positive(1).
            positive(2).
            positive(3).
        """)
        results = engine.query("?- forall(positive(X), X > 0).")
        assert len(results) == 1

    # --- Numeric generation ---

    def test_between(self):
        engine = self._make_engine()
        results = engine.query("?- between(1, 3, X).")
        assert len(results) == 3
        values = [results[i].apply(Variable("X")).value for i in range(3)]
        assert values == [1, 2, 3]

    def test_between_check(self):
        engine = self._make_engine()
        results = engine.query("?- between(1, 5, 3).")
        assert len(results) == 1

    def test_succ(self):
        engine = self._make_engine()
        results = engine.query("?- succ(2, 3).")
        assert len(results) == 1
        results = engine.query("?- succ(2, 4).")
        assert len(results) == 0

    def test_succ_generate(self):
        engine = self._make_engine()
        results = engine.query("?- succ(2, X).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Number(3)

    def test_plus(self):
        engine = self._make_engine()
        results = engine.query("?- plus(2, 3, 5).")
        assert len(results) == 1
        results = engine.query("?- plus(2, 3, X).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Number(5)

    # --- List operations ---

    def test_reverse(self):
        engine = self._make_engine()
        results = engine.query("?- reverse([a, b, c], R).")
        assert len(results) == 1
        # R should be [c, b, a]
        r = results[0].apply(Variable("R"))
        assert term_to_str(r) == "[c, b, a]"

    def test_nth0(self):
        engine = self._make_engine()
        results = engine.query("?- nth0(1, [a, b, c], X).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Atom("b")

    def test_nth1(self):
        engine = self._make_engine()
        results = engine.query("?- nth1(1, [a, b, c], X).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Atom("a")

    def test_last(self):
        engine = self._make_engine()
        results = engine.query("?- last([a, b, c], X).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Atom("c")

    def test_sort(self):
        engine = self._make_engine()
        results = engine.query("?- sort([3, 1, 2, 1], R).")
        assert len(results) == 1
        r = results[0].apply(Variable("R"))
        assert term_to_str(r) == "[1, 2, 3]"  # deduped and sorted

    def test_msort(self):
        engine = self._make_engine()
        results = engine.query("?- msort([3, 1, 2, 1], R).")
        assert len(results) == 1
        r = results[0].apply(Variable("R"))
        assert term_to_str(r) == "[1, 1, 2, 3]"  # sorted, duplicates kept

    # --- Term inspection ---

    def test_copy_term(self):
        engine = self._make_engine()
        results = engine.query("?- copy_term(f(X, Y), C).")
        assert len(results) == 1
        c = results[0].apply(Variable("C"))
        assert isinstance(c, Compound)
        assert c.name == "f"
        assert c.arity == 2
        # The copy should have fresh variables, not X and Y
        assert isinstance(c.args[0], Variable)
        assert c.args[0].name != "X"

    def test_univ_decompose(self):
        engine = self._make_engine()
        results = engine.query("?- f(a, b) =.. L.")
        assert len(results) == 1
        l = results[0].apply(Variable("L"))
        assert term_to_str(l) == "[f, a, b]"

    def test_univ_compose(self):
        engine = self._make_engine()
        results = engine.query("?- T =.. [f, a, b].")
        assert len(results) == 1
        t = results[0].apply(Variable("T"))
        assert term_to_str(t) == "f(a, b)"

    # --- Dynamic database ---

    def test_assertz(self):
        engine = self._make_engine()
        engine.load_source("a(1).")
        engine.query("?- assertz(a(2)).")
        results = engine.query("?- a(X).")
        assert len(results) == 2

    def test_asserta(self):
        engine = self._make_engine()
        engine.load_source("a(1).")
        engine.query("?- asserta(a(0)).")
        results = engine.query("?- a(X).")
        # a(0) should be first
        x = results[0].apply(Variable("X"))
        assert x == Number(0)

    def test_retract(self):
        engine = self._make_engine()
        engine.load_source("""
            a(1).
            a(2).
        """)
        engine.query("?- retract(a(1)).")
        results = engine.query("?- a(X).")
        assert len(results) == 1

    # --- Meta-logical ---

    def test_findall(self):
        engine = self._make_engine()
        engine.load_source("""
            a(1).
            a(2).
            a(3).
        """)
        results = engine.query("?- findall(X, a(X), L).")
        assert len(results) == 1
        l = results[0].apply(Variable("L"))
        assert term_to_str(l) == "[1, 2, 3]"

    def test_bagof(self):
        engine = self._make_engine()
        engine.load_source("""
            a(1).
            a(2).
        """)
        results = engine.query("?- bagof(X, a(X), L).")
        assert len(results) == 1

    def test_bagof_fails_when_empty(self):
        engine = self._make_engine()
        engine.load_source("a(1).")
        results = engine.query("?- bagof(X, b(X), L).")
        assert len(results) == 0

    def test_setof(self):
        engine = self._make_engine()
        engine.load_source("""
            a(1).
            a(2).
            a(1).
        """)
        results = engine.query("?- setof(X, a(X), L).")
        assert len(results) == 1
        l = results[0].apply(Variable("L"))
        assert term_to_str(l) == "[1, 2]"

    # --- Tracing ---

    def test_trace_property(self):
        engine = self._make_engine()
        assert engine.trace is False
        engine.trace = True
        assert engine.trace is True

    # --- Predicate indexing ---

    def test_predicate_index(self):
        engine = self._make_engine()
        engine.load_source("""
            parent(tom, bob).
            parent(tom, liz).
            grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
        """)
        idx = engine.predicate_index()
        assert "parent/2" in idx
        assert idx["parent/2"] == 2
        assert "grandparent/2" in idx
        assert idx["grandparent/2"] == 1


# ==================================================================
# AST utility tests
# ==================================================================

class TestASTUtils:
    def test_variables_in(self):
        X = Variable("X")
        Y = Variable("Y")
        term = Compound("f", (Atom("a"), X, Compound("g", (Y,))))
        vars_set = variables_in(term)
        assert X in vars_set
        assert Y in vars_set
        assert len(vars_set) == 2

    def test_substitute(self):
        X = Variable("X")
        term = Compound("f", (X, Atom("b")))
        subst = {X: Atom("a")}
        result = substitute(term, subst)
        assert result == Compound("f", (Atom("a"), Atom("b")))

    def test_term_to_str_atom(self):
        assert term_to_str(Atom("hello")) == "hello"

    def test_term_to_str_variable(self):
        assert term_to_str(Variable("X")) == "X"

    def test_term_to_str_number(self):
        assert term_to_str(Number(42)) == "42"

    def test_term_to_str_compound(self):
        term = Compound("f", (Atom("a"), Variable("X")))
        assert term_to_str(term) == "f(a, X)"

    def test_term_to_str_list(self):
        lst = Compound(".", (Atom("a"), Compound(".", (Atom("b"), Atom("[]")))))
        assert term_to_str(lst) == "[a, b]"


# ==================================================================
# Integration tests
# ==================================================================

class TestIntegration:
    def _make_engine(self) -> Engine:
        engine = Engine()
        register_builtins(engine)
        return engine

    def test_family_tree(self):
        engine = self._make_engine()
        engine.load_source("""
            male(tom).
            male(bob).
            female(liz).
            female(ann).
            parent(tom, bob).
            parent(tom, liz).
            parent(bob, ann).
            father(X, Y) :- parent(X, Y), male(X).
            mother(X, Y) :- parent(X, Y), female(X).
            sibling(X, Y) :- parent(Z, X), parent(Z, Y), X \\= Y.
        """)
        # Fathers (tom→bob, tom→liz, bob→ann = 3)
        results = engine.query("?- father(X, Y).")
        assert len(results) == 3
        # Siblings
        results = engine.query("?- sibling(bob, liz).")
        assert len(results) == 1

    def test_fibonacci(self):
        engine = self._make_engine()
        engine.load_source("""
            fib(0, 0).
            fib(1, 1).
            fib(N, R) :- N > 1, N1 is N - 1, N2 is N - 2, fib(N1, R1), fib(N2, R2), R is R1 + R2.
        """)
        results = engine.query("?- fib(6, X).")
        assert len(results) == 1
        x = results[0].apply(Variable("X"))
        assert isinstance(x, Number)
        assert x.value == 8

    def test_list_operations(self):
        engine = self._make_engine()
        engine.load_source("""
            my_last(X, [X]).
            my_last(X, [_|T]) :- my_last(X, T).
        """)
        results = engine.query("?- my_last(X, [1, 2, 3]).")
        assert len(results) == 1
        x = results[0].apply(Variable("X"))
        assert x == Number(3)

    def test_factorial(self):
        engine = self._make_engine()
        engine.load_source("""
            fact(0, 1).
            fact(N, R) :- N > 0, N1 is N - 1, fact(N1, R1), R is N * R1.
        """)
        results = engine.query("?- fact(5, X).")
        assert len(results) == 1
        x = results[0].apply(Variable("X"))
        assert isinstance(x, Number)
        assert x.value == 120

    def test_nested_compound(self):
        engine = self._make_engine()
        engine.load_source("pair(f(a), g(b)).")
        results = engine.query("?- pair(f(X), g(Y)).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")) == Atom("a")
        assert results[0].apply(Variable("Y")) == Atom("b")

    def test_quicksort(self):
        engine = self._make_engine()
        engine.load_source("""
            qsort([], []).
            qsort([H|T], Sorted) :-
                partition(H, T, Less, Greater),
                qsort(Less, SortedLess),
                qsort(Greater, SortedGreater),
                append(SortedLess, [H|SortedGreater], Sorted).
            partition(_, [], [], []).
            partition(Pivot, [H|T], [H|Less], Greater) :-
                H =< Pivot,
                partition(Pivot, T, Less, Greater).
            partition(Pivot, [H|T], Less, [H|Greater]) :-
                H > Pivot,
                partition(Pivot, T, Less, Greater).
        """)
        results = engine.query("?- qsort([3, 1, 4, 1, 5], R).")
        assert len(results) == 1
        r = results[0].apply(Variable("R"))
        assert term_to_str(r) == "[1, 1, 3, 4, 5]"

    def test_findall_with_computation(self):
        engine = self._make_engine()
        engine.load_source("""
            num(1).
            num(2).
            num(3).
            num(4).
            num(5).
            square(X, Y) :- num(X), Y is X * X.
        """)
        results = engine.query("?- findall(Y, square(X, Y), Squares).")
        assert len(results) == 1
        squares = results[0].apply(Variable("Squares"))
        assert term_to_str(squares) == "[1, 4, 9, 16, 25]"

    def test_max_depth_protection(self):
        engine = self._make_engine()
        engine._max_depth = 50
        engine.load_source("loop :- loop.")
        with pytest.raises(EngineError, match="Maximum inference depth"):
            engine.query("?- loop.")