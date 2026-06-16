"""Built-in predicates for the mini-Prolog engine.

Comprehensive library of ~60 built-in predicates covering:
- Unification and comparison (=/2, \\=/2, ==/2, \\==/2)
- Type checking (var/1, atom/1, number/1, compound/1, ground/1, ...)
- Control flow (true/0, fail/0, !/0, not/1, \\+/1, once/1, forall/2, repeat/0, halt/0)
- Arithmetic (is/2, </2, >/2, =</2, >=/2)
- Numeric generation (between/3, succ/2, plus/3)
- List operations (member/2, append/3, length/2, reverse/2, sort/2, msort/2,
  nth0/3, nth1/3, last/2, max_list/2, min_list/2, sum_list/2)
- Term inspection (functor/3, arg/3, copy_term/2, =../2, variables/2, numbervars/3)
- Dynamic database (assertz/1, asserta/1, retract/1, clause/2)
- Meta-logical (findall/3, bagof/3, setof/3)
- String/atom manipulation (atom_length/2, atom_concat/3, sub_atom/5, char_code/2)
- I/O (write/1, writeln/1, nl/0, write_canonical/1)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Set, List as TList
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Term, term_to_str, variables_in,
)
from prolog_engine.unifier import Unifier, Substitution, UnificationError
from prolog_engine.engine import EngineError, EvaluationError

if TYPE_CHECKING:
    from prolog_engine.engine import Engine, EngineError


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
    except EvaluationError:
        return  # Unknown function/constant → fail
    except EngineError:
        raise  # Let real engine errors (division by zero) propagate
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
    """==/2 — Arithmetic equality (both sides evaluated)."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except EvaluationError:
        return  # Unknown function → fail
    except EngineError:
        raise  # Real errors propagate
    except Exception:
        return
    if left.value == right.value:
        yield subst


def builtin_arith_neq(engine: "Engine", args: tuple, subst: Substitution):
    """\\==/2 — Arithmetic inequality."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except EvaluationError:
        return
    except EngineError:
        raise
    except Exception:
        return
    if left.value != right.value:
        yield subst


def builtin_lt(engine: "Engine", args: tuple, subst: Substitution):
    """</2 — Arithmetic less than."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except EvaluationError:
        return
    except EngineError:
        raise
    except Exception:
        return
    if left.value < right.value:
        yield subst


def builtin_le(engine: "Engine", args: tuple, subst: Substitution):
    """=</2 — Arithmetic less than or equal."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except EvaluationError:
        return
    except EngineError:
        raise
    except Exception:
        return
    if left.value <= right.value:
        yield subst


def builtin_gt(engine: "Engine", args: tuple, subst: Substitution):
    """>/2 — Arithmetic greater than."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except EvaluationError:
        return
    except EngineError:
        raise
    except Exception:
        return
    if left.value > right.value:
        yield subst


def builtin_ge(engine: "Engine", args: tuple, subst: Substitution):
    """>=/2 — Arithmetic greater than or equal."""
    try:
        left = engine.evaluate(args[0], subst)
        right = engine.evaluate(args[1], subst)
    except EvaluationError:
        return
    except EngineError:
        raise
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


def builtin_atomic(engine: "Engine", args: tuple, subst: Substitution):
    """atomic/1 — Succeeds if argument is atomic (atom, number, or string)."""
    term = subst.apply(args[0])
    if isinstance(term, (Atom, Number, String)):
        yield subst


def builtin_ground(engine: "Engine", args: tuple, subst: Substitution):
    """ground/1 — Succeeds if argument is fully instantiated (no variables)."""
    term = subst.apply(args[0])
    if _is_ground(term):
        yield subst


def _is_ground(term: Term) -> bool:
    """Check if a term has no uninstantiated variables."""
    if isinstance(term, Variable):
        return False
    if isinstance(term, Compound):
        return all(_is_ground(a) for a in term.args)
    return True


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


def builtin_once(engine: "Engine", args: tuple, subst: Substitution):
    """once/1 — Execute goal but commit to first solution (like ', !')."""
    from prolog_engine.ast_nodes import Query
    goal = args[0]
    query = Query([goal])
    for new_subst in engine.execute(query):
        yield new_subst
        return  # Only yield the first solution


def builtin_forall(engine: "Engine", args: tuple, subst: Substitution):
    """forall/2 — forall(Generate, Test) succeeds iff for every solution
    of Generate, Test also succeeds."""
    from prolog_engine.ast_nodes import Query
    generate_goal = args[0]
    test_goal = args[1]

    gen_query = Query([generate_goal])
    for gen_subst in engine.execute(gen_query):
        # Apply the generation substitution to the test goal
        test_goal_instantiated = gen_subst.apply(test_goal)
        test_query = Query([test_goal_instantiated])
        found = False
        for _ in engine.execute(test_query):
            found = True
            break
        if not found:
            return  # Test failed for this generation → forall fails
    yield subst  # All tests passed


def builtin_repeat(engine: "Engine", args: tuple, subst: Substitution):
    """repeat/0 — Generates infinite choices on backtracking."""
    while True:
        yield subst


# ------------------------------------------------------------------
# Numeric generation builtins
# ------------------------------------------------------------------

def builtin_between(engine: "Engine", args: tuple, subst: Substitution):
    """between/3 — between(Low, High, Value). Generates all integers Low..High."""
    try:
        low = engine.evaluate(args[0], subst)
        high = engine.evaluate(args[1], subst)
    except EvaluationError:
        return
    except EngineError:
        raise
    except Exception:
        return
    val_term = subst.apply(args[2])

    low_int = int(low.value)
    high_int = int(high.value)

    if isinstance(val_term, Variable):
        for i in range(low_int, high_int + 1):
            new_subst = subst.copy()
            new_subst[val_term] = Number(i)
            yield new_subst
    elif isinstance(val_term, Number):
        v = int(val_term.value)
        if low_int <= v <= high_int:
            yield subst


def builtin_succ(engine: "Engine", args: tuple, subst: Substitution):
    """succ/2 — succ(N, M) means M = N + 1."""
    n_term = subst.apply(args[0])
    m_term = subst.apply(args[1])

    if isinstance(n_term, Number) and isinstance(m_term, Variable):
        new_subst = subst.copy()
        new_subst[m_term] = Number(n_term.value + 1)
        yield new_subst
    elif isinstance(m_term, Number) and isinstance(n_term, Variable):
        if m_term.value > 0:
            new_subst = subst.copy()
            new_subst[n_term] = Number(m_term.value - 1)
            yield new_subst
    elif isinstance(n_term, Number) and isinstance(m_term, Number):
        if m_term.value == n_term.value + 1:
            yield subst


def builtin_plus(engine: "Engine", args: tuple, subst: Substitution):
    """plus/3 — plus(A, B, C) means A + B = C."""
    a_term = subst.apply(args[0])
    b_term = subst.apply(args[1])
    c_term = subst.apply(args[2])

    if isinstance(a_term, Number) and isinstance(b_term, Number):
        result = Number(a_term.value + b_term.value)
        try:
            yield Unifier.unify(c_term, result, subst.copy())
        except UnificationError:
            return
    elif isinstance(a_term, Number) and isinstance(c_term, Number):
        result = Number(c_term.value - a_term.value)
        try:
            yield Unifier.unify(b_term, result, subst.copy())
        except UnificationError:
            return
    elif isinstance(b_term, Number) and isinstance(c_term, Number):
        result = Number(c_term.value - b_term.value)
        try:
            yield Unifier.unify(a_term, result, subst.copy())
        except UnificationError:
            return


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


def _list_to_python(term: Term) -> list:
    """Convert a Prolog list to a Python list of terms."""
    result = []
    current = term
    while isinstance(current, Compound) and current.name == "." and current.arity == 2:
        result.append(current.args[0])
        current = current.args[1]
    return result


def _python_to_list(items: list) -> Term:
    """Convert a Python list to a Prolog list."""
    result: Term = Atom("[]")
    for item in reversed(items):
        result = Compound(".", (item, result))
    return result


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
            built: Term = l2
            for elem in reversed(elements):
                built = Compound(".", (elem, built))
            try:
                yield Unifier.unify(result, built, subst.copy())
            except UnificationError:
                return
            return

        if isinstance(current, Variable):
            # List1 has a variable tail
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
            prefix_list = Atom("[]")
            for e in reversed(elements):
                prefix_list = Compound(".", (e, prefix_list))
            try:
                yield Unifier.unify(l1, prefix_list,
                           Unifier.unify(l2, Atom("[]"), subst.copy()))
            except UnificationError:
                pass


def builtin_reverse(engine: "Engine", args: tuple, subst: Substitution):
    """reverse/2 — reverse(List, Reversed)."""
    lst_term = subst.apply(args[0])
    rev_term = subst.apply(args[1])

    # If List is ground
    if not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        elements.reverse()
        reversed_list = _python_to_list(elements)
        try:
            yield Unifier.unify(rev_term, reversed_list, subst.copy())
        except UnificationError:
            return
        return

    # If Reversed is ground
    if not isinstance(rev_term, Variable):
        elements = _list_to_python(rev_term)
        elements.reverse()
        original = _python_to_list(elements)
        try:
            yield Unifier.unify(lst_term, original, subst.copy())
        except UnificationError:
            return


def builtin_nth0(engine: "Engine", args: tuple, subst: Substitution):
    """nth0/3 — nth0(Index, List, Element). 0-based."""
    idx_term = subst.apply(args[0])
    lst_term = subst.apply(args[1])
    elem_term = subst.apply(args[2])

    if isinstance(idx_term, Number) and not isinstance(lst_term, Variable):
        idx = int(idx_term.value)
        elements = _list_to_python(lst_term)
        if 0 <= idx < len(elements):
            try:
                yield Unifier.unify(elem_term, elements[idx], subst.copy())
            except UnificationError:
                return
    elif isinstance(idx_term, Variable) and not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        for i, elem in enumerate(elements):
            new_subst = subst.copy()
            new_subst[idx_term] = Number(i)
            try:
                yield Unifier.unify(elem_term, elem, new_subst)
            except UnificationError:
                continue


def builtin_nth1(engine: "Engine", args: tuple, subst: Substitution):
    """nth1/3 — nth1(Index, List, Element). 1-based."""
    idx_term = subst.apply(args[0])
    lst_term = subst.apply(args[1])
    elem_term = subst.apply(args[2])

    if isinstance(idx_term, Number) and not isinstance(lst_term, Variable):
        idx = int(idx_term.value)
        elements = _list_to_python(lst_term)
        if 1 <= idx <= len(elements):
            try:
                yield Unifier.unify(elem_term, elements[idx - 1], subst.copy())
            except UnificationError:
                return
    elif isinstance(idx_term, Variable) and not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        for i, elem in enumerate(elements):
            new_subst = subst.copy()
            new_subst[idx_term] = Number(i + 1)
            try:
                yield Unifier.unify(elem_term, elem, new_subst)
            except UnificationError:
                continue


def builtin_last(engine: "Engine", args: tuple, subst: Substitution):
    """last/2 — last(List, Element)."""
    lst_term = subst.apply(args[0])
    elem_term = subst.apply(args[1])

    if not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        if elements:
            try:
                yield Unifier.unify(elem_term, elements[-1], subst.copy())
            except UnificationError:
                return


def builtin_sort(engine: "Engine", args: tuple, subst: Substitution):
    """sort/2 — sort(List, Sorted). Remove duplicates and sort."""
    lst_term = subst.apply(args[0])
    sorted_term = subst.apply(args[1])

    if not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        # Sort by term representation
        def sort_key(t):
            if isinstance(t, Number):
                return (0, t.value)
            if isinstance(t, Atom):
                return (1, t.name)
            if isinstance(t, String):
                return (2, t.value)
            if isinstance(t, Compound):
                return (3, t.name, t.arity)
            return (4,)

        # Remove duplicates while preserving sort order
        seen = set()
        unique = []
        for e in elements:
            key = _term_hash_key(e)
            if key not in seen:
                seen.add(key)
                unique.append(e)

        unique.sort(key=sort_key)
        sorted_list = _python_to_list(unique)
        try:
            yield Unifier.unify(sorted_term, sorted_list, subst.copy())
        except UnificationError:
            return


def _term_hash_key(term: Term) -> tuple:
    """Create a hashable key for a term for deduplication."""
    if isinstance(term, Atom):
        return ("atom", term.name)
    if isinstance(term, Number):
        return ("num", term.value)
    if isinstance(term, String):
        return ("str", term.value)
    if isinstance(term, Variable):
        return ("var", id(term))
    if isinstance(term, Compound):
        return ("cmp", term.name, term.arity) + tuple(_term_hash_key(a) for a in term.args)
    return ()


def builtin_msort(engine: "Engine", args: tuple, subst: Substitution):
    """msort/2 — msort(List, Sorted). Sort but keep duplicates."""
    lst_term = subst.apply(args[0])
    sorted_term = subst.apply(args[1])

    if not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        def sort_key(t):
            if isinstance(t, Number):
                return (0, t.value)
            if isinstance(t, Atom):
                return (1, t.name)
            if isinstance(t, String):
                return (2, t.value)
            return (3,)
        elements.sort(key=sort_key)
        sorted_list = _python_to_list(elements)
        try:
            yield Unifier.unify(sorted_term, sorted_list, subst.copy())
        except UnificationError:
            return


# ------------------------------------------------------------------
# Term inspection builtins
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


def builtin_copy_term(engine: "Engine", args: tuple, subst: Substitution):
    """copy_term/2 — copy_term(Term, Copy). Copy with fresh variables."""
    original = subst.apply(args[0])
    copy = subst.apply(args[1])

    fresh_copy = engine.copy_term(original)
    try:
        yield Unifier.unify(copy, fresh_copy, subst.copy())
    except UnificationError:
        return


def builtin_univ(engine: "Engine", args: tuple, subst: Substitution):
    """=../2 — Term =.. List. Univ: decompose/recompose a term."""
    term = subst.apply(args[0])
    list_term = subst.apply(args[1])

    if not isinstance(term, Variable):
        # Decompose
        if isinstance(term, Compound):
            elements = [Atom(term.name)] + list(term.args)
        elif isinstance(term, Atom):
            elements = [Atom(term.name)]
        elif isinstance(term, Number):
            elements = [term]
        else:
            return
        prolog_list = _python_to_list(elements)
        try:
            yield Unifier.unify(list_term, prolog_list, subst.copy())
        except UnificationError:
            return
    else:
        # Compose from list
        if not isinstance(list_term, Variable):
            elements = _list_to_python(list_term)
            if len(elements) >= 1:
                name = elements[0]
                if isinstance(name, Atom):
                    if len(elements) == 1:
                        composed: Term = name
                    else:
                        composed = Compound(name.name, tuple(elements[1:]))
                    try:
                        yield Unifier.unify(term, composed, subst.copy())
                    except UnificationError:
                        return


# ------------------------------------------------------------------
# Dynamic database builtins
# ------------------------------------------------------------------

def builtin_assertz(engine: "Engine", args: tuple, subst: Substitution):
    """assertz/1 — Add a clause at the end of the database."""
    term = subst.apply(args[0])
    if isinstance(term, Compound):
        from prolog_engine.ast_nodes import Clause
        clause = Clause(term)  # fact
        engine.add_clause(clause)
        yield subst
    elif isinstance(term, Atom):
        from prolog_engine.ast_nodes import Clause
        clause = Clause(Compound(term.name, ()))
        engine.add_clause(clause)
        yield subst


def builtin_asserta(engine: "Engine", args: tuple, subst: Substitution):
    """asserta/1 — Add a clause at the beginning of the database.

    Note: We insert at the front by inserting at index 0 and rebuilding.
    """
    term = subst.apply(args[0])
    if isinstance(term, Compound):
        from prolog_engine.ast_nodes import Clause
        clause = Clause(term)
        engine._clauses.insert(0, clause)
        engine._rebuild_index()
        yield subst
    elif isinstance(term, Atom):
        from prolog_engine.ast_nodes import Clause
        clause = Clause(Compound(term.name, ()))
        engine._clauses.insert(0, clause)
        engine._rebuild_index()
        yield subst


def builtin_retract(engine: "Engine", args: tuple, subst: Substitution):
    """retract/1 — Remove the first matching clause."""
    term = subst.apply(args[0])
    if isinstance(term, Compound):
        if engine.retract_clause_by_head(term):
            yield subst


def builtin_clause(engine: "Engine", args: tuple, subst: Substitution):
    """clause/2 — clause(Head, Body). Introspect the database."""
    head_term = subst.apply(args[0])
    body_term = subst.apply(args[1])

    if isinstance(head_term, Compound):
        key = f"{head_term.name}/{head_term.arity}"
        indices = engine._index.get(key, [])
        for idx in indices:
            clause = engine._clauses[idx]
            try:
                new_subst = Unifier.unify(head_term, clause.head, subst.copy())
            except UnificationError:
                continue
            # Construct the body representation
            if clause.is_fact:
                body_rep: Term = Atom("true")
            else:
                body_list = clause.body if clause.body else []
                if len(body_list) == 1:
                    body_rep = body_list[0]
                elif len(body_list) > 1:
                    # Build conjunction: (a, b, c) = "','(a, ','(b, c))
                    body_rep = body_list[-1]
                    for g in reversed(body_list[:-1]):
                        body_rep = Compound(",", (g, body_rep))
                else:
                    body_rep = Atom("true")
            try:
                yield Unifier.unify(body_term, body_rep, new_subst)
            except UnificationError:
                continue


# ------------------------------------------------------------------
# Meta-logical builtins
# ------------------------------------------------------------------

def builtin_findall(engine: "Engine", args: tuple, subst: Substitution):
    """findall/3 — findall(Template, Goal, Bag)."""
    template = args[0]
    goal = args[1]
    bag_term = subst.apply(args[2])

    from prolog_engine.ast_nodes import Query
    query = Query([goal])

    collected = []
    for solution_subst in engine.execute(query):
        # Apply solution to template
        instance = solution_subst.apply(template)
        collected.append(instance)

    # Build result list
    result_list = _python_to_list(collected)
    try:
        yield Unifier.unify(bag_term, result_list, subst.copy())
    except UnificationError:
        return


def builtin_bagof(engine: "Engine", args: tuple, subst: Substitution):
    """bagof/3 — bagof(Template, Goal, Bag). Like findall but fails if no results."""
    template = args[0]
    goal = args[1]
    bag_term = subst.apply(args[2])

    from prolog_engine.ast_nodes import Query
    query = Query([goal])

    collected = []
    for solution_subst in engine.execute(query):
        instance = solution_subst.apply(template)
        collected.append(instance)

    if not collected:
        return  # bagof fails if no results

    result_list = _python_to_list(collected)
    try:
        yield Unifier.unify(bag_term, result_list, subst.copy())
    except UnificationError:
        return


def builtin_setof(engine: "Engine", args: tuple, subst: Substitution):
    """setof/3 — setof(Template, Goal, Set). Like bagof but sorted and deduped."""
    template = args[0]
    goal = args[1]
    set_term = subst.apply(args[2])

    from prolog_engine.ast_nodes import Query
    query = Query([goal])

    collected = []
    for solution_subst in engine.execute(query):
        instance = solution_subst.apply(template)
        collected.append(instance)

    if not collected:
        return

    # Sort and deduplicate
    def sort_key(t):
        if isinstance(t, Number):
            return (0, t.value)
        if isinstance(t, Atom):
            return (1, t.name)
        if isinstance(t, String):
            return (2, t.value)
        return (3,)

    seen = set()
    unique = []
    for e in collected:
        key = _term_hash_key(e)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=sort_key)

    result_list = _python_to_list(unique)
    try:
        yield Unifier.unify(set_term, result_list, subst.copy())
    except UnificationError:
        return


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


def builtin_write_canonical(engine: "Engine", args: tuple, subst: Substitution):
    """write_canonical/1 — Write in canonical form f(a, b)."""
    term = subst.apply(args[0])
    print(_write_canonical(term), end="")
    yield subst


def _write_canonical(term: Term) -> str:
    """Write term in canonical operator-free form."""
    if isinstance(term, Compound):
        if term.name == "." and term.arity == 2:
            args_str = ",".join(_write_canonical(a) for a in term.args)
            return f".({args_str})"
        if term.arity == 0:
            return term.name
        args_str = ",".join(_write_canonical(a) for a in term.args)
        return f"{term.name}({args_str})"
    return term_to_str(term)


# ------------------------------------------------------------------
# String manipulation builtins
# ------------------------------------------------------------------

def builtin_atom_length(engine: "Engine", args: tuple, subst: Substitution):
    """atom_length/2 — atom_length(Atom, Length)."""
    atom_term = subst.apply(args[0])
    len_term = subst.apply(args[1])

    if isinstance(atom_term, Atom):
        length = len(atom_term.name)
        if isinstance(len_term, Variable):
            new_subst = subst.copy()
            new_subst[len_term] = Number(length)
            yield new_subst
        elif isinstance(len_term, Number):
            if len_term.value == length:
                yield subst
    elif isinstance(atom_term, Variable) and isinstance(len_term, Number):
        return


def builtin_atom_concat(engine: "Engine", args: tuple, subst: Substitution):
    """atom_concat/3 — atom_concat(Atom1, Atom2, Result)."""
    a1 = subst.apply(args[0])
    a2 = subst.apply(args[1])
    result = subst.apply(args[2])

    if isinstance(a1, Atom) and isinstance(a2, Atom):
        combined = Atom(a1.name + a2.name)
        try:
            yield Unifier.unify(result, combined, subst.copy())
        except UnificationError:
            return
    elif isinstance(result, Atom):
        name = result.name
        for i in range(len(name) + 1):
            part1 = Atom(name[:i])
            part2 = Atom(name[i:])
            try:
                s = Unifier.unify(a1, part1, subst.copy())
                s = Unifier.unify(a2, part2, s)
                yield s
            except UnificationError:
                continue


def builtin_sub_atom(engine: "Engine", args: tuple, subst: Substitution):
    """sub_atom/5 — sub_atom(Atom, Before, Length, After, SubAtom)."""
    atom_term = subst.apply(args[0])
    before_term = subst.apply(args[1])
    length_term = subst.apply(args[2])
    after_term = subst.apply(args[3])
    sub_term = subst.apply(args[4])

    if isinstance(atom_term, Atom):
        name = atom_term.name
        n = len(name)
        for b in range(n + 1):
            for length in range(n - b + 1):
                after = n - b - length
                sub = name[b:b + length]
                try:
                    s = subst.copy()
                    if isinstance(before_term, Variable):
                        s[before_term] = Number(b)
                    elif isinstance(before_term, Number) and before_term.value != b:
                        continue
                    if isinstance(length_term, Variable):
                        s[length_term] = Number(length)
                    elif isinstance(length_term, Number) and length_term.value != length:
                        continue
                    if isinstance(after_term, Variable):
                        s[after_term] = Number(after)
                    elif isinstance(after_term, Number) and after_term.value != after:
                        continue
                    sub_atom = Atom(sub)
                    s2 = Unifier.unify(sub_term, sub_atom, s)
                    yield s2
                except UnificationError:
                    continue


def builtin_char_code(engine: "Engine", args: tuple, subst: Substitution):
    """char_code/2 — char_code(Char, Code)."""
    char_term = subst.apply(args[0])
    code_term = subst.apply(args[1])

    if isinstance(char_term, Atom) and len(char_term.name) == 1:
        code = ord(char_term.name)
        if isinstance(code_term, Variable):
            new_subst = subst.copy()
            new_subst[code_term] = Number(code)
            yield new_subst
        elif isinstance(code_term, Number):
            if code_term.value == code:
                yield subst
    elif isinstance(code_term, Number):
        code_val = int(code_term.value)
        if 0 <= code_val <= 0x10FFFF:
            char = Atom(chr(code_val))
            try:
                yield Unifier.unify(char_term, char, subst.copy())
            except UnificationError:
                return


# ------------------------------------------------------------------
# Additional list builtins
# ------------------------------------------------------------------

def builtin_max_list(engine: "Engine", args: tuple, subst: Substitution):
    """max_list/2 — max_list(List, Max). Maximum element of a list."""
    lst_term = subst.apply(args[0])
    max_term = subst.apply(args[1])

    if not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        if not elements:
            return
        max_val = None
        for e in elements:
            if isinstance(e, Number):
                if max_val is None or e.value > max_val:
                    max_val = e.value
        if max_val is not None:
            try:
                yield Unifier.unify(max_term, Number(max_val), subst.copy())
            except UnificationError:
                return


def builtin_min_list(engine: "Engine", args: tuple, subst: Substitution):
    """min_list/2 — min_list(List, Min). Minimum element of a list."""
    lst_term = subst.apply(args[0])
    min_term = subst.apply(args[1])

    if not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        if not elements:
            return
        min_val = None
        for e in elements:
            if isinstance(e, Number):
                if min_val is None or e.value < min_val:
                    min_val = e.value
        if min_val is not None:
            try:
                yield Unifier.unify(min_term, Number(min_val), subst.copy())
            except UnificationError:
                return


def builtin_sum_list(engine: "Engine", args: tuple, subst: Substitution):
    """sum_list/2 — sum_list(List, Sum). Sum of all numeric elements."""
    lst_term = subst.apply(args[0])
    sum_term = subst.apply(args[1])

    if not isinstance(lst_term, Variable):
        elements = _list_to_python(lst_term)
        total = 0.0
        for e in elements:
            if isinstance(e, Number):
                total += e.value
            else:
                return
        try:
            yield Unifier.unify(sum_term, Number(total), subst.copy())
        except UnificationError:
            return


# ------------------------------------------------------------------
# Additional term inspection builtins
# ------------------------------------------------------------------

def builtin_term_variables(engine: "Engine", args: tuple, subst: Substitution):
    """variables/2 — variables(Term, VarList)."""
    term = subst.apply(args[0])
    var_list_term = subst.apply(args[1])

    vars_in_term = list(variables_in(term))
    seen = set()
    unique_vars = []
    for v in vars_in_term:
        if v not in seen:
            seen.add(v)
            unique_vars.append(v)

    var_list = _python_to_list(unique_vars)
    try:
        yield Unifier.unify(var_list_term, var_list, subst.copy())
    except UnificationError:
        return


def builtin_numbervars(engine: "Engine", args: tuple, subst: Substitution):
    """numbervars/3 — numbervars(Term, Start, End)."""
    term = subst.apply(args[0])
    start_term = subst.apply(args[1])
    end_term = subst.apply(args[2])

    if isinstance(start_term, Number):
        start_val = int(start_term.value)
        vars_in_term = list(variables_in(term))
        seen = set()
        unique_vars = []
        for v in vars_in_term:
            if v not in seen:
                seen.add(v)
                unique_vars.append(v)

        end_val = start_val + len(unique_vars)
        if isinstance(end_term, Variable):
            new_subst = subst.copy()
            new_subst[end_term] = Number(end_val)
            yield new_subst
        elif isinstance(end_term, Number) and end_term.value == end_val:
            yield subst


# ------------------------------------------------------------------
# Additional control flow builtins
# ------------------------------------------------------------------

def builtin_halt(engine: "Engine", args: tuple, subst: Substitution):
    """halt/0 — Exit the Prolog engine."""
    import sys
    sys.exit(0)


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------

def register_builtins(engine: "Engine") -> None:
    """Register all built-in predicates with the engine.

    This registers ~60 built-in predicates covering:
    - Unification and comparison
    - Type checking
    - Control flow
    - Arithmetic and numeric generation
    - List operations
    - Term inspection
    - Dynamic database
    - Meta-logical
    - String/atom manipulation
    - I/O
    """
    import logging
    logger = logging.getLogger(__name__ + ".register_builtins")

    # Unification & comparison
    engine.register_builtin("=/2", builtin_unify)
    engine.register_builtin("\\=/2", builtin_not_unify)
    engine.register_builtin("is/2", builtin_is)
    engine.register_builtin("==/2", builtin_arith_eq)
    engine.register_builtin("\\==/2", builtin_arith_neq)
    engine.register_builtin("</2", builtin_lt)
    engine.register_builtin("=</2", builtin_le)
    engine.register_builtin(">/2", builtin_gt)
    engine.register_builtin(">=/2", builtin_ge)

    # Type checking
    engine.register_builtin("var/1", builtin_var)
    engine.register_builtin("nonvar/1", builtin_nonvar)
    engine.register_builtin("atom/1", builtin_atom_check)
    engine.register_builtin("number/1", builtin_number_check)
    engine.register_builtin("compound/1", builtin_compound_check)
    engine.register_builtin("integer/1", builtin_integer_check)
    engine.register_builtin("float/1", builtin_float_check)
    engine.register_builtin("string/1", builtin_string_check)
    engine.register_builtin("atomic/1", builtin_atomic)
    engine.register_builtin("ground/1", builtin_ground)

    # Control flow
    engine.register_builtin("true/0", builtin_true)
    engine.register_builtin("fail/0", builtin_fail)
    engine.register_builtin("!/0", builtin_true)  # cut handled specially in engine
    engine.register_builtin("not/1", builtin_not)
    engine.register_builtin("\\+/1", builtin_not)
    engine.register_builtin("once/1", builtin_once)
    engine.register_builtin("forall/2", builtin_forall)
    engine.register_builtin("repeat/0", builtin_repeat)
    engine.register_builtin("halt/0", builtin_halt)

    # Numeric generation
    engine.register_builtin("between/3", builtin_between)
    engine.register_builtin("succ/2", builtin_succ)
    engine.register_builtin("plus/3", builtin_plus)

    # List operations
    engine.register_builtin("length/2", builtin_length)
    engine.register_builtin("member/2", builtin_member)
    engine.register_builtin("append/3", builtin_append)
    engine.register_builtin("reverse/2", builtin_reverse)
    engine.register_builtin("nth0/3", builtin_nth0)
    engine.register_builtin("nth1/3", builtin_nth1)
    engine.register_builtin("last/2", builtin_last)
    engine.register_builtin("sort/2", builtin_sort)
    engine.register_builtin("msort/2", builtin_msort)
    engine.register_builtin("max_list/2", builtin_max_list)
    engine.register_builtin("min_list/2", builtin_min_list)
    engine.register_builtin("sum_list/2", builtin_sum_list)

    # Term inspection
    engine.register_builtin("functor/3", builtin_functor)
    engine.register_builtin("arg/3", builtin_arg)
    engine.register_builtin("copy_term/2", builtin_copy_term)
    engine.register_builtin("=../2", builtin_univ)
    engine.register_builtin("variables/2", builtin_term_variables)
    engine.register_builtin("numbervars/3", builtin_numbervars)

    # Dynamic database
    engine.register_builtin("assertz/1", builtin_assertz)
    engine.register_builtin("asserta/1", builtin_asserta)
    engine.register_builtin("retract/1", builtin_retract)
    engine.register_builtin("clause/2", builtin_clause)

    # Meta-logical
    engine.register_builtin("findall/3", builtin_findall)
    engine.register_builtin("bagof/3", builtin_bagof)
    engine.register_builtin("setof/3", builtin_setof)

    # String/atom manipulation
    engine.register_builtin("atom_length/2", builtin_atom_length)
    engine.register_builtin("atom_concat/3", builtin_atom_concat)
    engine.register_builtin("sub_atom/5", builtin_sub_atom)
    engine.register_builtin("char_code/2", builtin_char_code)

    # I/O
    engine.register_builtin("write/1", builtin_write)
    engine.register_builtin("writeln/1", builtin_writeln)
    engine.register_builtin("nl/0", builtin_nl)
    engine.register_builtin("write_canonical/1", builtin_write_canonical)

    logger.info("Registered %d built-in predicates", len(engine.get_builtins()))