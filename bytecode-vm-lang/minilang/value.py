"""Runtime value representation for the MiniLang VM.

The VM uses a tagged-union style: a :class:`Value` carries an ``int`` tag and a
Python object payload.  Keeping the tag in a separate attribute avoids
``isinstance`` checks in the hot dispatch loop.

Heap-allocated values (arrays and closures) are :class:`Object` instances so
that a tracing garbage collector can walk them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class ValueTag(IntEnum):
    INT = 0
    BOOL = 1
    STRING = 2
    NIL = 3
    ARRAY = 4
    CLOSURE = 5
    BOUND = 6   # builtin function bound to the VM


@dataclass(slots=True)
class Value:
    """A single MiniLang runtime value."""
    tag: ValueTag
    payload: object

    # ---- constructors -------------------------------------------------- #
    @classmethod
    def int(cls, n: int) -> "Value":
        return cls(ValueTag.INT, n)

    @classmethod
    def bool_(cls, b: bool) -> "Value":
        return cls(ValueTag.BOOL, b)

    @classmethod
    def str_(cls, s: str) -> "Value":
        return cls(ValueTag.STRING, s)

    @classmethod
    def nil(cls) -> "Value":
        return cls(ValueTag.NIL, None)

    @classmethod
    def array(cls, items: list["Value"]) -> "Value":
        return cls(ValueTag.ARRAY, items)

    @classmethod
    def closure(cls, obj: "Closure") -> "Value":
        return cls(ValueTag.CLOSURE, obj)

    @classmethod
    def bound(cls, obj: "BoundFunc") -> "Value":
        return cls(ValueTag.BOUND, obj)

    # ---- predicates ---------------------------------------------------- #
    def is_truthy(self) -> bool:
        if self.tag == ValueTag.BOOL:
            return bool(self.payload)
        if self.tag == ValueTag.INT:
            return self.payload != 0
        if self.tag == ValueTag.STRING:
            return len(self.payload) > 0  # type: ignore[arg-type]
        if self.tag == ValueTag.NIL:
            return False
        return True  # arrays, closures always truthy

    def equals(self, other: "Value") -> bool:
        if self.tag != other.tag:
            return False
        if self.tag == ValueTag.ARRAY:
            # structural equality for arrays
            a = self.payload
            b = other.payload
            if len(a) != len(b):  # type: ignore[arg-type]
                return False
            return all(x.equals(y) for x, y in zip(a, b))  # type: ignore[arg-type]
        return self.payload == other.payload

    # ---- display ------------------------------------------------------- #
    def display(self) -> str:
        if self.tag == ValueTag.INT:
            return str(self.payload)
        if self.tag == ValueTag.BOOL:
            return "true" if self.payload else "false"
        if self.tag == ValueTag.STRING:
            return str(self.payload)
        if self.tag == ValueTag.NIL:
            return "nil"
        if self.tag == ValueTag.ARRAY:
            items = self.payload  # type: ignore[assignment]
            return "[" + ", ".join(v.display() for v in items) + "]"
        if self.tag == ValueTag.CLOSURE:
            cl = self.payload  # type: ignore[assignment]
            return f"<fn {cl.name}>"
        if self.tag == ValueTag.BOUND:
            return f"<builtin {self.payload.name}>"  # type: ignore[attr-defined]
        return "<value>"


class Object:
    """Base class for heap-allocated MiniLang values (visited by the GC)."""


@dataclass(slots=True)
class Closure(Object):
    """A function value: bytecode chunk + captured environment."""
    name: str
    code: list  # list[Instruction]
    nparams: int
    nlocals: int
    upvalues: list["Value"] = field(default_factory=list)


@dataclass(slots=True)
class BoundFunc(Object):
    """A built-in function implemented in Python."""
    name: str
    arity: int
    fn: object  # callable[list[Value], Value]

    def __repr__(self) -> str:
        return f"BoundFunc({self.name}, arity={self.arity})"