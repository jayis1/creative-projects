"""Core Scheme data types.

Defines the runtime representations of Scheme values:
- ``Symbol`` — interned identifiers
- ``Pair`` / ``Nil`` — the cons-cell backbone of Scheme lists
- ``Bool`` — ``#t`` / ``#f`` (distinct from Python ``True``/``False`` for clarity)
- ``Char`` — character literal
- ``Vector`` — homogeneous vector type
- ``Unspecified`` — the result of side-effecting forms (e.g. ``set!``)
- ``EOF`` — end-of-file object
- ``Procedure`` / ``Lambda`` — callable values
- ``Continuation`` — reified continuation captured by ``call/cc``
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Callable, Optional


class SchemeType:
    """Base marker class for Scheme runtime types."""

    __slots__ = ()


class Symbol(SchemeType):
    """An interned Scheme symbol."""

    _table: dict[str, "Symbol"] = {}
    __slots__ = ("name",)

    def __new__(cls, name: str) -> "Symbol":
        existing = cls._table.get(name)
        if existing is not None:
            return existing
        obj = object.__new__(cls)
        obj.name = name
        cls._table[name] = obj
        return obj

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)

    @classmethod
    def intern(cls, name: str) -> "Symbol":
        return cls(name)

    @classmethod
    def Gensym(cls, prefix: str = "g") -> "Symbol":
        import itertools
        cls._gensym_counter = getattr(cls, "_gensym_counter", 0) + 1
        name = f"{prefix}{cls._gensym_counter}"
        # Ensure uniqueness even if a user symbol matches
        while name in cls._table:
            cls._gensym_counter += 1
            name = f"{prefix}{cls._gensym_counter}"
        obj = object.__new__(cls)
        obj.name = name
        cls._table[name] = obj
        return obj


class Pair(SchemeType):
    """A mutable cons cell."""

    __slots__ = ("car", "cdr")

    def __init__(self, car: Any, cdr: Any):
        self.car = car
        self.cdr = cdr

    def __repr__(self) -> str:
        return scheme_repr(self)

    def __eq__(self, other) -> bool:
        # Structural equality (same as equal? in Scheme)
        if not isinstance(other, Pair):
            return False
        # Compare element by element to handle recursive structures
        return scheme_equal_pair(self, other)

    def __hash__(self) -> int:
        # Pairs are mutable; use identity for hashing
        return id(self)

    def __iter__(self):
        node = self
        while isinstance(node, Pair):
            yield node.car
            node = node.cdr
        if node is not Nil and not isinstance(node, NilType):
            raise TypeError("cannot iterate improper list")

    def __len__(self) -> int:
        n = 0
        node: Any = self
        while isinstance(node, Pair):
            n += 1
            node = node.cdr
        return n


def scheme_equal_pair(a: "Pair", b: "Pair", _depth: int = 0) -> bool:
    """Structural equality for pairs with cycle protection."""
    if _depth > 1000:
        return a is b
    if a is b:
        return True
    # Compare car
    ca, cb = a.car, b.car
    if isinstance(ca, Pair) and isinstance(cb, Pair):
        if not scheme_equal_pair(ca, cb, _depth + 1):
            return False
    elif ca != cb:
        return False
    # Compare cdr
    cd, cd2 = a.cdr, b.cdr
    if cd is Nil or isinstance(cd, NilType):
        return cd2 is Nil or isinstance(cd2, NilType)
    if cd2 is Nil or isinstance(cd2, NilType):
        return False
    if isinstance(cd, Pair) and isinstance(cd2, Pair):
        return scheme_equal_pair(cd, cd2, _depth + 1)
    return cd == cd2


class NilType(SchemeType):
    """The empty list ``()``."""

    __slots__ = ()
    _instance: Optional["NilType"] = None

    def __new__(cls) -> "NilType":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "()"

    def __iter__(self):
        return iter([])

    def __len__(self) -> int:
        return 0

    def __bool__(self) -> bool:
        return True  # () is truthy in Scheme


Nil = NilType()


class Bool(SchemeType):
    """Scheme boolean wrapper.

    Instances are interned: ``Bool(True) is TRUE`` and ``Bool(False) is FALSE``.
    """

    __slots__ = ("value",)
    _instances: dict = {}

    def __new__(cls, value: bool) -> "Bool":
        # Intern: always return the canonical singleton
        key = bool(value)
        inst = cls._instances.get(key)
        if inst is None:
            inst = object.__new__(cls)
            cls._instances[key] = inst
        return inst

    def __init__(self, value: bool):
        self.value = bool(value)

    def __repr__(self) -> str:
        return "#t" if self.value else "#f"

    def __bool__(self) -> bool:
        return self.value


TRUE = Bool(True)
FALSE = Bool(False)


class Char(SchemeType):
    """Scheme character literal."""

    __slots__ = ("value",)

    def __init__(self, value: str):
        self.value = value

    def __repr__(self) -> str:
        names = {
            " ": "#\\space",
            "\n": "#\\newline",
            "\t": "#\\tab",
            "\r": "#\\return",
            "\0": "#\\null",
        }
        return names.get(self.value, f"#\\{self.value}")

    def __eq__(self, other) -> bool:
        return isinstance(other, Char) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class Vector(SchemeType):
    """Scheme vector — a fixed-length array."""

    __slots__ = ("items",)

    def __init__(self, items: list):
        self.items = items

    def __repr__(self) -> str:
        return "#(" + " ".join(scheme_repr(x) for x in self.items) + ")"

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx):
        return self.items[idx]

    def __setitem__(self, idx, val):
        self.items[idx] = val

    def __eq__(self, other) -> bool:
        return isinstance(other, Vector) and self.items == other.items

    def __iter__(self):
        return iter(self.items)


class UnspecifiedType(SchemeType):
    """The unspecified value (result of side-effecting forms)."""

    __slots__ = ()
    _instance: Optional["UnspecifiedType"] = None

    def __new__(cls) -> "UnspecifiedType":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return ""


Unspecified = UnspecifiedType()


class EOFType(SchemeType):
    """End-of-file object."""

    __slots__ = ()
    _instance: Optional["EOFType"] = None

    def __new__(cls) -> "EOFType":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "#<eof>"


EOF = EOFType()


class Procedure(SchemeType):
    """A Scheme procedure (closure or primitive)."""

    __slots__ = ("name", "fn")

    def __init__(self, name: str, fn: Callable):
        self.name = name
        self.fn = fn

    def __call__(self, *args):
        return self.fn(*args)

    def __repr__(self) -> str:
        return f"#<procedure:{self.name}>"


class Lambda(SchemeType):
    """A user-defined closure with parameters, body, and captured environment."""

    __slots__ = ("params", "rest", "body", "env", "name", "min_args")

    def __init__(self, params: list, rest: Optional[Symbol], body, env, name: str = "lambda"):
        self.params = params
        self.rest = rest  # the 'rest' parameter symbol if any (for variadic)
        self.body = body  # list of body forms
        self.env = env
        self.name = name
        self.min_args = len(params)

    def __repr__(self) -> str:
        return f"#<procedure:{self.name}>"


class Continuation(SchemeType):
    """A reified continuation captured by call/cc."""

    __slots__ = ("tag",)

    def __init__(self, tag):
        self.tag = tag

    def __repr__(self) -> str:
        return f"#<continuation>"


class Macro(SchemeType):
    """A macro defined via syntax-rules."""

    __slots__ = ("rules", "ellipses", "literals")

    def __init__(self, rules, literals):
        self.rules = rules  # list of (pattern, template) pairs
        self.literals = literals  # list of literal identifiers


# ---------------------------------------------------------------------------
# printing

def scheme_repr(val: Any) -> str:
    """Produce a Scheme-readable string for a value."""
    if val is None:
        return ""
    if val is True:
        return "#t"
    if val is False:
        return "#f"
    if isinstance(val, Bool):
        return "#t" if val.value else "#f"
    if isinstance(val, Symbol):
        return val.name
    if isinstance(val, str):
        # Escape strings
        escaped = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(val, bool):  # Python bool (shouldn't normally occur)
        return "#t" if val else "#f"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if val == int(val) and abs(val) < 1e16:
            return f"{val:.1f}"
        return repr(val)
    if isinstance(val, Fraction):
        return f"{val.numerator}/{val.denominator}"
    if isinstance(val, Char):
        return repr(val)
    if isinstance(val, NilType):
        return "()"
    if isinstance(val, UnspecifiedType):
        return ""
    if isinstance(val, EOFType):
        return "#<eof>"
    if isinstance(val, Pair):
        parts = []
        node: Any = val
        while isinstance(node, Pair):
            parts.append(scheme_repr(node.car))
            node = node.cdr
        if node is Nil or isinstance(node, NilType):
            return "(" + " ".join(parts) + ")"
        return "(" + " ".join(parts) + " . " + scheme_repr(node) + ")"
    if isinstance(val, Vector):
        return "#(" + " ".join(scheme_repr(x) for x in val.items) + ")"
    if isinstance(val, (Procedure, Lambda, Continuation, Macro)):
        return repr(val)
    if isinstance(val, list):
        return "(" + " ".join(scheme_repr(x) for x in val) + ")"
    if callable(val):
        return f"#<procedure:{getattr(val, '__name__', '?')}>"
    return str(val)


def scheme_display(val: Any) -> str:
    """Like scheme_repr but strings are displayed without quotes."""
    if isinstance(val, str):
        return val
    if isinstance(val, Char):
        return val.value
    if isinstance(val, Pair):
        parts = []
        node: Any = val
        while isinstance(node, Pair):
            parts.append(scheme_display(node.car))
            node = node.cdr
        if node is Nil or isinstance(node, NilType):
            return "(" + " ".join(parts) + ")"
        return "(" + " ".join(parts) + " . " + scheme_display(node) + ")"
    if isinstance(val, Vector):
        return "#(" + " ".join(scheme_display(x) for x in val.items) + ")"
    return scheme_repr(val)


def to_python_bool(val: Any) -> bool:
    """Scheme truthiness: everything except #f is true."""
    if isinstance(val, Bool):
        return val.value
    if val is False:
        return False
    return True


def is_true(val: Any) -> bool:
    """Scheme truthiness test."""
    return to_python_bool(val)


def list_to_pairs(lst: list, tail=None) -> Any:
    """Convert a Python list to a Scheme list (chain of Pairs)."""
    result = tail if tail is not None else Nil
    for item in reversed(lst):
        result = Pair(item, result)
    return result


def pairs_to_list(lst: Any) -> list:
    """Convert a Scheme list to a Python list."""
    result = []
    node = lst
    while isinstance(node, Pair):
        result.append(node.car)
        node = node.cdr
    return result


def is_list(val: Any) -> bool:
    """Check if val is a proper Scheme list (not improper, not cyclic)."""
    if val is Nil or isinstance(val, NilType):
        return True
    if not isinstance(val, Pair):
        return False
    # Floyd's cycle detection
    slow = val
    fast = val
    while True:
        # Advance fast by 2
        if not isinstance(fast, Pair):
            return False
        fast = fast.cdr
        if fast is Nil or isinstance(fast, NilType):
            return True
        if not isinstance(fast, Pair):
            return False
        fast = fast.cdr
        if fast is Nil or isinstance(fast, NilType):
            return True
        # Advance slow by 1
        slow = slow.cdr
        if fast is slow:
            return False  # cycle detected