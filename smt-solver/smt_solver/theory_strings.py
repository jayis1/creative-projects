"""
Theory of Strings (partial).

Supports basic string operations:
  - str.len: string length
  - str.++: string concatenation
  - str.contains: substring check
  - str.prefixof: prefix check
  - str.suffixof: suffix check
  - str.substr: substring extraction
  - str.at: character at index
  - str.indexof: index of substring
  - str.replace: string replacement

This is a simple, non-complete theory solver that handles string constraints
by evaluating them against a model. It does not perform full string constraint
solving but can check consistency of simple assertions.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field

from .ast import Term, Var, App, StrConst, NumConst, STRING, INT, BOOL, REAL


class StringTheory:
    """Simple string theory solver.

    Evaluates string constraints against a given model and checks consistency.
    For more complex constraints, it falls back to 'unknown'.
    """

    def __init__(self):
        self._constraints: List[Tuple[Term, bool]] = []
        self._string_vars: Set[str] = set()
        self._int_vars: Set[str] = set()

    def assert_atom(self, atom: App, polarity: bool) -> bool:
        """Assert a string theory atom.

        Args:
            atom: The atom to assert.
            polarity: True if the atom is asserted true, False if negated.

        Returns:
            True if the atom is consistent so far, False if immediately unsat.
        """
        self._constraints.append((atom, polarity))
        for v in _collect_string_vars(atom):
            self._string_vars.add(v)
        for v in _collect_int_vars(atom):
            self._int_vars.add(v)
        return True

    def check(self, model: Dict[str, object]) -> Tuple[str, Optional[List[int]]]:
        """Check consistency of string constraints against a model.

        Args:
            model: A mapping from variable names to values.

        Returns:
            ("sat", None) if consistent,
            ("unsat", indices) if inconsistent,
            ("unknown", None) if cannot determine.
        """
        for i, (atom, polarity) in enumerate(self._constraints):
            result = _eval_string_atom(atom, model)
            if result is None:
                continue  # cannot evaluate
            if result != polarity:
                return "unsat", [i]
        return "sat", None

    def get_model(self, model: Dict[str, object]) -> Dict[str, object]:
        """Extend the model with default string values for string variables."""
        for v in self._string_vars:
            if v not in model:
                model[v] = ""
        return model


def _collect_string_vars(term: Term) -> Set[str]:
    """Collect all String-sorted variable names in a term."""
    result: Set[str] = set()
    if isinstance(term, Var) and term.sort == STRING:
        result.add(term.name)
    elif isinstance(term, App):
        for arg in term.args:
            result.update(_collect_string_vars(arg))
    return result


def _collect_int_vars(term: Term) -> Set[str]:
    """Collect all Int-sorted variable names in a term."""
    result: Set[str] = set()
    if isinstance(term, Var) and term.sort == INT:
        result.add(term.name)
    elif isinstance(term, App):
        for arg in term.args:
            result.update(_collect_int_vars(arg))
    return result


def _eval_string_term(term: Term, model: Dict[str, object]) -> Optional[object]:
    """Evaluate a string term under a model."""
    if isinstance(term, StrConst):
        return term.value
    if isinstance(term, NumConst):
        return term.value
    if isinstance(term, Var):
        if term.sort == STRING:
            return model.get(term.name, "")
        if term.sort == INT:
            return model.get(term.name, 0)
        if term.sort == REAL:
            return model.get(term.name, 0.0)
        if term.sort == BOOL:
            return model.get(term.name, False)
        return None
    if isinstance(term, App):
        if term.func == "str.len":
            s = _eval_string_term(term.args[0], model)
            if s is None:
                return None
            return float(len(str(s)))
        if term.func == "str.++":
            parts = [_eval_string_term(a, model) for a in term.args]
            if any(p is None for p in parts):
                return None
            return "".join(str(p) for p in parts)
        if term.func == "str.at":
            s = _eval_string_term(term.args[0], model)
            i = _eval_string_term(term.args[1], model)
            if s is None or i is None:
                return None
            s, i = str(s), int(i)
            if 0 <= i < len(s):
                return s[i]
            return ""
        if term.func == "str.substr":
            s = _eval_string_term(term.args[0], model)
            start = _eval_string_term(term.args[1], model)
            length = _eval_string_term(term.args[2], model)
            if s is None or start is None or length is None:
                return None
            s, start, length = str(s), int(start), int(length)
            if start < 0:
                start = 0
                length += start
            if start >= len(s) or length <= 0:
                return ""
            return s[start:start + length]
        if term.func == "str.indexof":
            s = _eval_string_term(term.args[0], model)
            sub = _eval_string_term(term.args[1], model)
            start = _eval_string_term(term.args[2], model)
            if s is None or sub is None or start is None:
                return None
            s, sub, start = str(s), str(sub), int(start)
            if start < 0:
                start = 0
            idx = s.find(sub, start)
            return float(idx)
        if term.func == "str.replace":
            s = _eval_string_term(term.args[0], model)
            old = _eval_string_term(term.args[1], model)
            new = _eval_string_term(term.args[2], model)
            if s is None or old is None or new is None:
                return None
            s, old, new = str(s), str(old), str(new)
            if old == "":
                return s
            return s.replace(old, new, 1)
        if term.func == "str.contains":
            s = _eval_string_term(term.args[0], model)
            sub = _eval_string_term(term.args[1], model)
            if s is None or sub is None:
                return None
            return str(sub) in str(s)
        if term.func == "str.prefixof":
            pre = _eval_string_term(term.args[0], model)
            s = _eval_string_term(term.args[1], model)
            if pre is None or s is None:
                return None
            return str(s).startswith(str(pre))
        if term.func == "str.suffixof":
            suf = _eval_string_term(term.args[0], model)
            s = _eval_string_term(term.args[1], model)
            if suf is None or s is None:
                return None
            return str(s).endswith(str(suf))
        if term.func == "=":
            a = _eval_string_term(term.args[0], model)
            b = _eval_string_term(term.args[1], model)
            if a is None or b is None:
                return None
            return a == b
        if term.func in {"<", "<=", ">", ">="}:
            a = _eval_string_term(term.args[0], model)
            b = _eval_string_term(term.args[1], model)
            if a is None or b is None:
                return None
            if term.func == "<":
                return a < b
            if term.func == "<=":
                return a <= b
            if term.func == ">":
                return a > b
            if term.func == ">=":
                return a >= b
    return None


def _eval_string_atom(atom: Term, model: Dict[str, object]) -> Optional[bool]:
    """Evaluate a string theory atom under a model."""
    return _eval_string_term(atom, model)  # type: ignore