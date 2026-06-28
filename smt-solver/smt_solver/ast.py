"""
AST for SMT terms and formulas.

The AST uses a small, well-defined node hierarchy.  Every node is an
immutable, hashable value (tuples under the hood) so that terms can be
used as dictionary keys and stored in hash-consed maps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Optional, List


# ---------------------------------------------------------------------------
# Sorts (types)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Sort:
    """A first-order sort.  Builtins: Bool, Real, Int."""
    name: str
    args: Tuple["Sort", ...] = ()

    def __str__(self) -> str:
        if self.args:
            return f"({self.name} {' '.join(str(a) for a in self.args)})"
        return self.name

    @property
    def is_bool(self) -> bool:
        return self.name == "Bool"

    @property
    def is_numeric(self) -> bool:
        return self.name in ("Real", "Int")


# Predefined sorts
BOOL = Sort("Bool")
REAL = Sort("Real")
INT = Sort("Int")


def function_sort(domain: Tuple[Sort, ...], rng: Sort) -> Sort:
    """Create an uninterpreted-function sort for signatures."""
    return Sort("->", tuple(domain) + (rng,))


# ---------------------------------------------------------------------------
# Term nodes
# ---------------------------------------------------------------------------

class Term:
    """Base class for all terms/formulas.  Subclasses define ``sort``."""
    __slots__ = ()

    def children(self) -> Tuple["Term", ...]:
        return ()

    def __str__(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError


@dataclass(frozen=True)
class Var(Term):
    """A variable referenced by name."""
    name: str
    sort: Sort = REAL

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class BoolConst(Term):
    """Boolean literal true/false."""
    value: bool = True
    sort: Sort = field(default=BOOL, repr=False)

    def __str__(self) -> str:
        return "true" if self.value else "false"


@dataclass(frozen=True)
class NumConst(Term):
    """Numeric constant.  ``is_int`` distinguishes Int from Real."""
    value: float = 0.0
    is_int: bool = False
    sort: Sort = field(default=REAL, repr=False)

    def __str__(self) -> str:
        if self.is_int:
            return str(int(self.value))
        if float(self.value).is_integer():
            return f"{int(self.value)}.0"
        return repr(self.value)

    def __post_init__(self):
        if self.is_int and not float(self.value).is_integer():
            object.__setattr__(self, "value", float(int(self.value)))


@dataclass(frozen=True)
class App(Term):
    """Application of a function symbol to arguments.

    When ``func`` is one of the known logical connectives it is treated
    specially by the solver.  Otherwise it is an uninterpreted function
    application handled by the EUF theory.
    """
    func: str = ""
    args: Tuple[Term, ...] = ()
    sort: Sort = BOOL

    def children(self) -> Tuple[Term, ...]:
        return self.args

    def __str__(self) -> str:
        if not self.args:
            return self.func
        return f"({self.func} {' '.join(str(a) for a in self.args)})"


# ---------------------------------------------------------------------------
# Convenience constructors for Boolean / arithmetic operators
# ---------------------------------------------------------------------------

def And(*terms: Term) -> Term:
    """N-ary conjunction.  And() with no args is ``true``."""
    if not terms:
        return BoolConst(True)
    if len(terms) == 1:
        return terms[0]
    return App("and", tuple(terms), BOOL)


def Or(*terms: Term) -> Term:
    """N-ary disjunction.  Or() with no args is ``false``."""
    if not terms:
        return BoolConst(False)
    if len(terms) == 1:
        return terms[0]
    return App("or", tuple(terms), BOOL)


def Not(t: Term) -> Term:
    """Logical negation."""
    if isinstance(t, BoolConst):
        return BoolConst(not t.value)
    return App("not", (t,), BOOL)


def Implies(a: Term, b: Term) -> Term:
    return App("=>", (a, b), BOOL)


def Iff(a: Term, b: Term) -> Term:
    return App("=", (a, b), BOOL)


def Eq(a: Term, b: Term) -> Term:
    """Equality (works for both Bool and numeric terms)."""
    return App("=", (a, b), BOOL)


def Lt(a: Term, b: Term) -> Term:
    return App("<", (a, b), BOOL)


def Le(a: Term, b: Term) -> Term:
    return App("<=", (a, b), BOOL)


def Gt(a: Term, b: Term) -> Term:
    return App(">", (a, b), BOOL)


def Ge(a: Term, b: Term) -> Term:
    return App(">=", (a, b), BOOL)


def Add(*terms: Term) -> Term:
    if not terms:
        return NumConst(0.0)
    if len(terms) == 1:
        return terms[0]
    return App("+", tuple(terms), terms[0].sort)


def Sub(a: Term, b: Term) -> Term:
    return App("-", (a, b), a.sort)


def Mul(*terms: Term) -> Term:
    if not terms:
        return NumConst(1.0)
    if len(terms) == 1:
        return terms[0]
    return App("*", tuple(terms), terms[0].sort)


def Neg(t: Term) -> Term:
    return App("-", (t,), t.sort)


def Ite(cond: Term, then_t: Term, else_t: Term) -> Term:
    return App("ite", (cond, then_t, else_t), then_t.sort)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def collect_vars(term: Term) -> set:
    """Return the set of all leaf Var nodes in a term tree."""
    found: set = set()
    stack = [term]
    while stack:
        n = stack.pop()
        if isinstance(n, Var):
            found.add(n)
        elif isinstance(n, App):
            stack.extend(n.args)
    return found


def pre_order(term: Term):
    """Yield all subterms in pre-order traversal."""
    yield term
    for c in term.children():
        yield from pre_order(c)


def is_atom(term: Term) -> bool:
    """A *theory atom* is an App whose top symbol is a theory predicate.

    Boolean connectives and ite are not atoms.
    """
    if not isinstance(term, App):
        return False
    return term.func in {"=", "<", "<=", ">", ">="}


def is_bool_connective(term: Term) -> bool:
    if not isinstance(term, App):
        return False
    return term.func in {"and", "or", "not", "=>", "ite", "xor", "distinct"}