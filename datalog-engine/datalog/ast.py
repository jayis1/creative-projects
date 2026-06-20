"""Abstract syntax tree (AST) nodes for the Datalog engine.

These classes are the in-memory representation of a parsed Datalog
program: Terms (variables / constants), Atoms (predicate + terms),
Literals (positive/negative atoms), Rules (head + body), Facts,
Queries, and Programs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Iterable, Iterator


# ---------------------------------------------------------------------------
# Terms — the things that appear inside an atom's argument list
# ---------------------------------------------------------------------------


class Term:
    """Base class for Datalog terms (variables and constants)."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - subclasses override
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class Variable(Term):
    """A logic variable, identified by a name starting with an uppercase
    letter or an underscore (for anonymous variables)."""

    name: str

    def __repr__(self) -> str:
        return f"Variable({self.name!r})"

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Constant(Term):
    """A constant value — string, int, float, or bool.

    Stored internally with a ``kind`` tag so that the engine can
    canonicalise and compare constants efficiently without relying on
    Python type identity (e.g. ``1`` (int) vs ``1.0`` (float) are
    considered equal)."""

    value: object
    kind: str = field(default="")

    def __post_init__(self) -> None:
        if not self.kind:
            object.__setattr__(self, "kind", _kind_of(self.value))

    def __repr__(self) -> str:
        return f"Constant({self.value!r}, kind={self.kind!r})"

    def __str__(self) -> str:
        return _format_constant(self.value)

    # Canonical equality: 1 == 1.0
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Constant):
            return NotImplemented
        return _canonical(self) == _canonical(other)

    def __hash__(self) -> int:
        return hash(_canonical(self))


def _kind_of(v: object) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    return "unknown"


def _canonical(c: Constant) -> Tuple[str, object]:
    """Canonical form for equality/hashing.

    Treat int/float with equal numeric value as the same constant."""
    if c.kind in ("int", "float") and isinstance(c.value, (int, float)):
        return ("num", float(c.value))
    return (c.kind, c.value)


def _format_constant(v: object) -> str:
    if isinstance(v, str):
        # Quote strings that could be confused with variables/identifiers
        if v and (v[0].isupper() or v[0] == "_" or not v.replace("_", "").isalnum()):
            return f'"{v}"'
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


# ---------------------------------------------------------------------------
# Atoms and Literals
# ---------------------------------------------------------------------------


@dataclass
class Atom:
    """A predicate symbol applied to a tuple of terms.

    Example: ``edge(a, b)`` or ``path(X, Y)``.
    """

    predicate: str
    terms: Tuple[Term, ...]

    def __init__(self, predicate: str, terms: Iterable[Term]):
        self.predicate = predicate
        self.terms = tuple(terms)

    def __repr__(self) -> str:
        inner = ", ".join(str(t) for t in self.terms)
        return f"Atom({self.predicate}({inner}))"

    def __str__(self) -> str:
        inner = ", ".join(str(t) for t in self.terms)
        return f"{self.predicate}({inner})"

    @property
    def arity(self) -> int:
        return len(self.terms)

    def variables(self) -> List[Variable]:
        """Return the list of variables in this atom (with duplicates)."""
        return [t for t in self.terms if isinstance(t, Variable)]

    def is_ground(self) -> bool:
        """True if the atom has no variables (all terms are constants)."""
        return all(isinstance(t, Constant) for t in self.terms)


@dataclass
class Literal:
    """A possibly-negated atom.

    ``positive=True`` (default) for a regular positive literal;
    ``positive=False`` for a negated literal ``not atom(...)``.
    """

    atom: Atom
    positive: bool = True

    def __repr__(self) -> str:
        prefix = "" if self.positive else "not "
        return f"Literal({prefix}{self.atom})"

    def __str__(self) -> str:
        prefix = "" if self.positive else "not "
        return f"{prefix}{self.atom}"


# ---------------------------------------------------------------------------
# Rules, Facts, Queries, Programs
# ---------------------------------------------------------------------------


@dataclass
class Rule:
    """A Datalog rule: ``head :- body1, body2, ..., bodyN.``

    The head is a single atom; the body is a list of literals
    (positive or negative). All variables in the head must appear in
    the positive body (safety condition).
    """

    head: Atom
    body: List[Literal]

    def __repr__(self) -> str:
        body = ", ".join(str(l) for l in self.body)
        return f"Rule({self.head} :- {body})"

    def __str__(self) -> str:
        body = ", ".join(str(l) for l in self.body)
        return f"{self.head} :- {body}."

    def body_variables(self) -> List[Variable]:
        out: List[Variable] = []
        for lit in self.body:
            out.extend(lit.atom.variables())
        return out

    def is_safe(self, builtins: Optional[set] = None,
                arith_builtins: Optional[set] = None) -> bool:
        """Check the Datalog safety condition.

        Rules:
        1. Every variable in the head must appear in a positive
           non-builtin body literal, OR be the output arg of a binding
           builtin (arithmetic/string with 3 args, or aggregate with
           2 args) whose inputs are all bound.
        2. Every variable in a negative literal must appear in a
           positive non-builtin literal.
        3. For binding builtins, all input arguments must be bound by
           positive non-builtin literals.

        Built-in comparisons (``>``, ``<`` etc.) and type-checks
        (``is_int`` etc.) do not bind variables.
        Arithmetic (``add``, ``mul``) and string (``concat``) builtins
        bind their 3rd argument. Aggregates (``count``, ``sum``) bind
        their 2nd argument."""
        if builtins is None:
            builtins = set()
        if arith_builtins is None:
            arith_builtins = set()

        # Variables bound by positive non-builtin literals
        pos_vars = set()
        for lit in self.body:
            if lit.positive and lit.atom.predicate not in builtins:
                for v in lit.atom.variables():
                    pos_vars.add(v.name)

        # Iteratively add variables bound by binding builtins whose
        # inputs are already in pos_vars. This handles chains like:
        #   foo(X, Y) :- num(X), add(X, 5, Y).
        # where Y is bound by add (with X already bound by num).
        # Also handles aggregates: count(X, N) binds N.
        changed = True
        while changed:
            changed = False
            for lit in self.body:
                if lit.positive and lit.atom.predicate in arith_builtins:
                    terms = lit.atom.terms
                    # Binding builtins: 3-arg (arith/string) or 2-arg (aggregate)
                    if len(terms) == 3:
                        input_count = 2
                        output_idx = 2
                    elif len(terms) == 2:
                        input_count = 1
                        output_idx = 1
                    else:
                        continue
                    # Check inputs are bound
                    inputs_bound = True
                    for t in terms[:input_count]:
                        if isinstance(t, Variable) and t.name not in pos_vars:
                            inputs_bound = False
                            break
                    if inputs_bound:
                        out = terms[output_idx]
                        if isinstance(out, Variable) and out.name not in pos_vars:
                            pos_vars.add(out.name)
                            changed = True

        # head vars must be in pos_vars
        for v in self.head.variables():
            if v.name not in pos_vars:
                return False
        # negated-literal vars must be in pos_vars
        for lit in self.body:
            if not lit.positive:
                for v in lit.atom.variables():
                    if v.name not in pos_vars:
                        return False
        return True


@dataclass
class Fact:
    """A ground fact: ``predicate(c1, c2, ...).``"""

    atom: Atom

    def __repr__(self) -> str:
        return f"Fact({self.atom})"

    def __str__(self) -> str:
        return f"{self.atom}."

    def is_ground(self) -> bool:
        return self.atom.is_ground()


@dataclass
class Query:
    """A query: ``?- p(X, c).``"""

    atom: Atom

    def __repr__(self) -> str:
        return f"Query(?- {self.atom})"

    def __str__(self) -> str:
        return f"?- {self.atom}."


@dataclass
class Program:
    """A parsed Datalog program: facts, rules, and queries."""

    facts: List[Fact] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)
    queries: List[Query] = field(default_factory=list)

    def __iter__(self) -> Iterator:
        return iter((*self.facts, *self.rules, *self.queries))

    def __len__(self) -> int:
        return len(self.facts) + len(self.rules) + len(self.queries)