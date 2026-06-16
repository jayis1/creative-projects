"""Abstract Syntax Tree nodes for the mini-Prolog engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union, Any


# ------------------------------------------------------------------
# Term types
# ------------------------------------------------------------------

@dataclass(frozen=True)
class Atom:
    """A Prolog atom (e.g. hello, foo_bar)."""
    name: str

    def __repr__(self) -> str:
        return f"Atom({self.name!r})"

    def __hash__(self) -> int:
        return hash(("Atom", self.name))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Atom) and self.name == other.name


@dataclass(frozen=True)
class Variable:
    """A Prolog variable (e.g. X, _Y, _)."""
    name: str

    def __repr__(self) -> str:
        return f"Variable({self.name!r})"

    def __hash__(self) -> int:
        return hash(("Variable", self.name))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Variable) and self.name == other.name


@dataclass(frozen=True)
class Number:
    """A Prolog number (integer or float)."""
    value: float

    def __repr__(self) -> str:
        if self.value == int(self.value):
            return f"Number({int(self.value)})"
        return f"Number({self.value})"

    def __hash__(self) -> int:
        return hash(("Number", self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Number) and self.value == other.value


@dataclass(frozen=True)
class String:
    """A Prolog string literal."""
    value: str

    def __repr__(self) -> str:
        return f"String({self.value!r})"

    def __hash__(self) -> int:
        return hash(("String", self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, String) and self.value == other.value


@dataclass(frozen=True)
class Compound:
    """A compound term: name(arg1, arg2, ...)."""
    name: str
    args: tuple

    def __repr__(self) -> str:
        if not self.args:
            return f"Compound({self.name!r})"
        args_str = ", ".join(repr(a) for a in self.args)
        return f"Compound({self.name!r}, ({args_str}))"

    def __hash__(self) -> int:
        return hash(("Compound", self.name, self.args))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Compound) and self.name == other.name and self.args == other.args

    @property
    def arity(self) -> int:
        return len(self.args)


# ------------------------------------------------------------------
# Top-level constructs
# ------------------------------------------------------------------

@dataclass
class Clause:
    """A Prolog clause: head :- body.  Or just head. for facts."""
    head: Compound
    body: Optional[List[Union[Compound, Atom]]] = None  # None means fact

    @property
    def is_fact(self) -> bool:
        return self.body is None

    def __repr__(self) -> str:
        if self.is_fact:
            return f"Clause({self.head!r})"
        body_str = ", ".join(repr(g) for g in self.body)
        return f"Clause({self.head!r} :- {body_str})"


@dataclass
class Query:
    """A Prolog query: ?- goal1, goal2, ..."""
    goals: List[Union[Compound, Atom]]

    def __repr__(self) -> str:
        goals_str = ", ".join(repr(g) for g in self.goals)
        return f"Query({goals_str})"


@dataclass
class Program:
    """A Prolog program: a collection of clauses."""
    clauses: List[Clause] = field(default_factory=list)

    def add_clause(self, clause: Clause) -> None:
        self.clauses.append(clause)

    def __repr__(self) -> str:
        return f"Program({len(self.clauses)} clauses)"


# Type alias
Term = Union[Atom, Variable, Number, String, Compound]


def variables_in(term: Term) -> set:
    """Return the set of Variable nodes in a term."""
    if isinstance(term, Variable):
        return {term}
    if isinstance(term, Compound):
        result: set = set()
        for arg in term.args:
            result |= variables_in(arg)
        return result
    return set()


def substitute(term: Term, subst: dict) -> Term:
    """Apply a substitution dict {Variable -> Term} to a term."""
    if isinstance(term, Variable):
        # Chase the substitution chain
        seen = set()
        current = term
        while current in subst and id(current) not in seen:
            seen.add(id(current))
            current = subst[current]
        return current
    if isinstance(term, Compound):
        new_args = tuple(substitute(arg, subst) for arg in term.args)
        return Compound(term.name, new_args)
    return term


def term_to_str(term: Term) -> str:
    """Pretty-print a term to a Prolog-like string."""
    if isinstance(term, Atom):
        return term.name
    if isinstance(term, Variable):
        return term.name
    if isinstance(term, Number):
        if term.value == int(term.value):
            return str(int(term.value))
        return str(term.value)
    if isinstance(term, String):
        return f'"{term.value}"'
    if isinstance(term, Compound):
        if term.name == "." and term.arity == 2:
            return _list_to_str(term)
        if term.arity == 0:
            return term.name
        args_str = ", ".join(term_to_str(a) for a in term.args)
        return f"{term.name}({args_str})"
    return str(term)


def _list_to_str(term: Term) -> str:
    """Convert a Prolog list (compound using dot notation) to string."""
    elements: list[str] = []
    current = term
    while isinstance(current, Compound) and current.name == "." and current.arity == 2:
        elements.append(term_to_str(current.args[0]))
        current = current.args[1]
    if isinstance(current, Atom) and current.name == "[]":
        return f"[{', '.join(elements)}]"
    else:
        return f"[{', '.join(elements)}|{term_to_str(current)}]"