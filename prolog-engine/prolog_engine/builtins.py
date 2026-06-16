"""Built-in predicates for the mini-Prolog engine."""

from __future__ import annotations

from typing import TYPE_CHECKING
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Term, term_to_str,
)
from prolog_engine.unifier import Unifier, Substitution, UnificationError

if TYPE_CHECKING:
    from prolog_engine.engine import Engine


# ------------------------------------------------------------------
# Unification builtins
# ------------------------------------------------------------------

def builtin_unify(engine: "Engine", args: tuple, subst: Substitution):
    """=/2 — Unification."""
    try:
        yield Unifier.unify(args[0], args[1], subst.copy())
    except UnificationError:
        return


def builtin_not_unify(engine: "Engine", args: tuple, subst: Substitution):
    """\\=/2 — Not unifiable."""
    try:
        Unifier.unify(args[0], args[1], subst.copy())
    except UnificationError:
        yield subst
        return
    return


def builtin_is(engine: "Engine", args: tuple, subst: Substitution):
    """is/2 — Arithmetic evaluation: X is Expr."""
    left = subst.apply(args[0])
    try:
        result = engine.evaluate(args[1], subst)
    except Exception:
        return
    if isinstance(left, Variable):
        new_subst = subst.copy()
        new_subst[left] = result
        yield new_subst
    elif isinstance(left, Number):
        if left.value == result.value:
            yield subst


def builtin_arith_eq(engine: "Engine", args: tuple, subst: Substitution):
    """===/2 — Arithmetic equality (both sides evaluated)."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except Exception:
        return
    if left.value == right.value:
        yield subst


def builtin_arith_neq(engine: "Engine", args: tuple, subst: Substitution):
    """\\===/2 — Arithmetic inequality."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except Exception:
        return
    if left.value != right.value:
        yield subst


def builtin_lt(engine: "Engine", args: tuple, subst: Substitution):
    """</2 — Arithmetic less than."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except Exception:
        return
    if left.value < right.value:
        yield subst


def builtin_le(engine: "Engine", args: tuple, subst: Substitution):
    """=</2 — Arithmetic less than or equal."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except Exception:
        return
    if left.value <= right.value:
        yield subst


def builtin_gt(engine: "Engine", args: tuple, subst: Substitution):
    """>/2 — Arithmetic greater than."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except Exception:
        return
    if left.value > right.value:
        yield subst


def builtin_ge(engine: "Engine", args: tuple, subst: Substitution):
    """>=/2 — Arithmetic greater than or equal."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except Exception:
        return
    if left.value >= right.value:
        yield subst


# ------------------------------------------------------------------
# Type-checking builtins
# ------------------------------------------------------------------

def builtin_var(engine: "Engine", args: tuple, subst: Substitution):
    """var/1 — Succeeds if argument is an uninstantiated variable."""
    term = subst.apply(args[0])
    if isinstance(term, Variable):
        yield subst


def builtin_nonvar(engine: "Engine", args: tuple, subst: Substitution):
    """nonvar/1 — Succeeds if argument is not an uninstantiated variable."""
    term = subst.apply(args[0])
    if not isinstance(term, Variable):
        yield subst


def builtin_atom_check(engine: "Engine", args: tuple, subst: Substitution):
    """atom/1 — Succeeds if argument is an atom."""
    term = subst.apply(args[0])
    if isinstance(term, Atom):
        yield subst


def builtin_number_check(engine: "Engine", args: tuple, subst: Substitution):
    """number/1 — Succeeds if argument is a number."""
    term = subst.apply(args[0])
    if isinstance(term, Number):
        yield subst


def builtin_compound_check(engine: "Engine", args: tuple, subst: Substitution):
    """compound/1 — Succeeds if argument is a compound term."""
    term = subst.apply(args[0])
    if isinstance(term, Compound):
        yield subst


def builtin_integer_check(engine: "Engine", args: tuple, subst: Substitution):
    """integer/1 — Succeeds if argument is an integer number."""
    term = subst.apply(args[0])
    if isinstance(term, Number) and term.value == int(term.value):
        yield subst


def builtin_float_check(engine: "Engine", args: tuple, subst: Substitution):
    """float/1 — Succeeds if argument is a float (non-integer) number."""
    term = subst.apply(args[0])
    if isinstance(term, Number) and term.value != int(term.value):
        yield subst


def builtin_string_check(engine: "Engine", args: tuple, subst: Substitution):
    """string/1 — Succeeds if argument is a string."""
    term = subst.apply(args[0])
    if isinstance(term, String):
        yield subst


# ------------------------------------------------------------------
# Control flow builtins
# ------------------------------------------------------------------

def builtin_fail(engine: "Engine", args: tuple, subst: Substitution):
    """fail/0 — Always fails (yields nothing)."""
    return
    yield  # make this a generator


def builtin_true(engine: "Engine", args: tuple, subst: Substitution):
    """true/0 — Always succeeds."""
    yield subst


def builtin_not(engine: "Engine", args: tuple, subst: Substitution):
    """not/1 or \\+/1 — Negation as failure."""
    from prolog_engine.ast_nodes import Query
    goal = args[0]
    query = Query([goal])
    for _ in engine.execute(query):
        return  # Goal succeeded → not fails
    yield subst  # Goal failed → not succeeds


def builtin_repeat(engine: "Engine", args: tuple, subst: Substitution):
    """repeat/0 — Generates infinite choices on backtracking."""
    while True:
        yield subst


# ------------------------------------------------------------------
# List builtins
# ------------------------------------------------------------------

def _list_length(term: Term) -> int:
    """Count the elements of a Prolog list."""
    count = 0
    current = term
    while isinstance(current, Compound) and current.name == "." and current.arity == 2:
        count += 1
        current = current.args[1]
    return count


def builtin_length(engine: "Engine", args: tuple, subst: Substitution):
    """length/2 — length(List, N)."""
    lst_term = subst.apply(args[0])
    n_term = subst.apply(args[1])

    # Count elements in a ground list
    if isinstance(lst_term, Compound) or (isinstance(lst_term, Atom) and lst_term.name == "[]"):
        count = _list_length(lst_term)
        if isinstance(n_term, Variable):
            new_subst = subst.copy()
            new_subst[n_term] = Number(count)
            yield new_subst
        elif isinstance(n_term, Number):
            if n_term.value == count:
                yield subst
        return

    # If N is known and List is a variable, generate a list of that length
    if isinstance(lst_term, Variable) and isinstance(n_term, Number):
        n = int(n_term.value)
        if n < 0:
            return
        result: Term = Atom("[]")
        for i in range(n):
            engine._var_counter += 1
            var = Variable(f"_L{engine._var_counter}")
            result = Compound(".", (var, result))
        new_subst = subst.copy()
        new_subst[lst_term] = result
        yield new_subst
        return


def builtin_member(engine: "Engine", args: tuple, subst: Substitution):
    """member/2 — member(Elem, List)."""
    elem = args[0]
    lst = subst.apply(args[1])

    current = lst
    while isinstance(current, Compound) and current.name == "." and current.arity == 2:
        try:
            new_subst = Unifier.unify(elem, current.args[0], subst.copy())
            yield new_subst
        except UnificationError:
            pass
        # Move to next element — but must re-apply subst to the tail
        next_tail = current.args[1]
        if isinstance(next_tail, Variable):
            current = subst.apply(next_tail)
        else:
            current = next_tail


def builtin_append(engine: "Engine", args: tuple, subst: Substitution):
    """append/3 — append(List1, List2, Result)."""
    l1 = subst.apply(args[0])
    l2 = subst.apply(args[1])
    result = subst.apply(args[2])

    # If List1 is ground, walk it and concatenate
    if not isinstance(l1, Variable):
        elements = []
        current = l1
        while isinstance(current, Compound) and current.name == "." and current.arity == 2:
            elements.append(current.args[0])
            current = current.args[1]

        if isinstance(current, Atom) and current.name == "[]":
            # List1 is complete; Result should be List1 ++ List2
            built: Term = l2
            for elem in reversed(elements):
                built = Compound(".", (elem, built))
            try:
                yield Unifier.unify(result, built, subst.copy())
            except UnificationError:
                return
            return

        # List1 has a variable tail
        if isinstance(current, Variable):
            # Provide one solution with the tail as-is
            built = l2
            for elem in reversed(elements):
                built = Compound(".", (elem, built))
            try:
                yield Unifier.unify(result, built, subst.copy())
            except UnificationError:
                pass
            return

    else:
        # List1 is a variable — split result
        if not isinstance(result, Variable):
            elements = []
            current = result
            while isinstance(current, Compound) and current.name == "." and current.arity == 2:
                # Try prefix of current length
                prefix_list: Term = Atom("[]")
                for e in reversed(elements):
                    prefix_list = Compound(".", (e, prefix_list))
                try:
                    yield Unifier.unify(l1, prefix_list,
                               Unifier.unify(l2, current, subst.copy()))
                except UnificationError:
                    pass
                elements.append(current.args[0])
                current = current.args[1]
            # Full list as prefix
            prefix_list = Atom("[]")
            for e in reversed(elements):
                prefix_list = Compound(".", (e, prefix_list))
            try:
                yield Unifier.unify(l1, prefix_list,
                           Unifier.unify(l2, Atom("[]"), subst.copy()))
            except UnificationError:
                pass


# ------------------------------------------------------------------
# I/O builtins
# ------------------------------------------------------------------

def builtin_nl(engine: "Engine", args: tuple, subst: Substitution):
    """nl/0 — Print a newline."""
    print()
    yield subst


def builtin_write(engine: "Engine", args: tuple, subst: Substitution):
    """write/1 — Write a term to stdout."""
    term = subst.apply(args[0])
    print(term_to_str(term), end="")
    yield subst


def builtin_writeln(engine: "Engine", args: tuple, subst: Substitution):
    """writeln/1 — Write a term followed by newline."""
    term = subst.apply(args[0])
    print(term_to_str(term))
    yield subst


# ------------------------------------------------------------------
# Structural builtins
# ------------------------------------------------------------------

def builtin_functor(engine: "Engine", args: tuple, subst: Substitution):
    """functor/3 — functor(Term, Name, Arity)."""
    term = subst.apply(args[0])
    name_term = subst.apply(args[1])
    arity_term = subst.apply(args[2])

    if not isinstance(term, Variable):
        if isinstance(term, Compound):
            t_name = Atom(term.name)
            t_arity = Number(term.arity)
        elif isinstance(term, Atom):
            t_name = Atom(term.name)
            t_arity = Number(0)
        elif isinstance(term, Number):
            t_name = term
            t_arity = Number(0)
        else:
            return
        try:
            s1 = Unifier.unify(name_term, t_name, subst.copy())
            yield Unifier.unify(arity_term, t_arity, s1)
        except UnificationError:
            return
    else:
        # Construct term from Name and Arity
        if isinstance(name_term, Atom) and isinstance(arity_term, Number):
            arity = int(arity_term.value)
            if arity == 0:
                yield Unifier.unify(term, name_term, subst.copy())
            else:
                new_args = []
                for _ in range(arity):
                    engine._var_counter += 1
                    new_args.append(Variable(f"_A{engine._var_counter}"))
                new_term = Compound(name_term.name, tuple(new_args))
                yield Unifier.unify(term, new_term, subst.copy())


def builtin_arg(engine: "Engine", args: tuple, subst: Substitution):
    """arg/3 — arg(N, Term, Arg)."""
    n_term = subst.apply(args[0])
    term = subst.apply(args[1])
    arg_term = subst.apply(args[2])

    if isinstance(n_term, Number) and isinstance(term, Compound):
        n = int(n_term.value)
        if 1 <= n <= term.arity:
            try:
                yield Unifier.unify(arg_term, term.args[n - 1], subst.copy())
            except UnificationError:
                return


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------

def register_builtins(engine: "Engine") -> None:
    """Register all built-in predicates with the engine."""
    engine.register_builtin("=/2", builtin_unify)
    engine.register_builtin("\\=/2", builtin_not_unify)
    engine.register_builtin("is/2", builtin_is)
    engine.register_builtin("==/2", builtin_arith_eq)
    engine.register_builtin("\\==/2", builtin_arith_neq)
    engine.register_builtin("</2", builtin_lt)
    engine.register_builtin("=</2", builtin_le)
    engine.register_builtin(">/2", builtin_gt)
    engine.register_builtin(">=/2", builtin_ge)

    engine.register_builtin("var/1", builtin_var)
    engine.register_builtin("nonvar/1", builtin_nonvar)
    engine.register_builtin("atom/1", builtin_atom_check)
    engine.register_builtin("number/1", builtin_number_check)
    engine.register_builtin("compound/1", builtin_compound_check)
    engine.register_builtin("integer/1", builtin_integer_check)
    engine.register_builtin("float/1", builtin_float_check)
    engine.register_builtin("string/1", builtin_string_check)

    engine.register_builtin("true/0", builtin_true)
    engine.register_builtin("fail/0", builtin_fail)
    engine.register_builtin("!/0", builtin_true)  # cut handled specially in engine
    engine.register_builtin("not/1", builtin_not)
    engine.register_builtin("\\+/1", builtin_not)
    engine.register_builtin("repeat/0", builtin_repeat)

    engine.register_builtin("length/2", builtin_length)
    engine.register_builtin("member/2", builtin_member)
    engine.register_builtin("append/3", builtin_append)

    engine.register_builtin("write/1", builtin_write)
    engine.register_builtin("writeln/1", builtin_writeln)
    engine.register_builtin("nl/0", builtin_nl)

    engine.register_builtin("functor/3", builtin_functor)
    engine.register_builtin("arg/3", builtin_arg)