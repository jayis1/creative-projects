"""MiniLang AST node definitions.

Every node is a frozen dataclass so that trees are hashable and immutable —
the type-checker and optimizer rely on being able to compare subtrees cheaply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


# --------------------------------------------------------------------------- #
# Type annotations                                                             #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class IntType:
    def __str__(self) -> str: return "int"


@dataclass(frozen=True, slots=True)
class StringType:
    def __str__(self) -> str: return "string"


@dataclass(frozen=True, slots=True)
class BoolType:
    def __str__(self) -> str: return "bool"


@dataclass(frozen=True, slots=True)
class UnitType:
    """The type of statements that produce no value (e.g. ``print(x)``)."""
    def __str__(self) -> str: return "unit"


@dataclass(frozen=True, slots=True)
class ArrayType:
    element: "TypeNode"
    def __str__(self) -> str: return f"array<{self.element}>"


@dataclass(frozen=True, slots=True)
class FuncType:
    params: tuple["TypeNode", ...]
    ret: "TypeNode"
    def __str__(self) -> str:
        ps = ", ".join(str(p) for p in self.params)
        return f"fn({ps}) -> {self.ret}"


TypeNode = Union[IntType, StringType, BoolType, UnitType, ArrayType, FuncType]


# --------------------------------------------------------------------------- #
# Expressions                                                                   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class IntLit:
    value: int
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class StringLit:
    value: str
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class BoolLit:
    value: bool
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class NilLit:
    """The ``nil`` literal — represents the unit/empty value."""
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class ArrayLit:
    elements: tuple["Expr", ...]
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class Ident:
    name: str
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class BinOp:
    op: str
    left: "Expr"
    right: "Expr"
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class UnaryOp:
    op: str
    operand: "Expr"
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class IndexExpr:
    array: "Expr"
    index: "Expr"
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class CallExpr:
    callee: "Expr"
    args: tuple["Expr", ...]
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class Assign:
    name: str
    value: "Expr"
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class IndexAssign:
    array: "Expr"
    index: "Expr"
    value: "Expr"
    line: int = 0
    col: int = 0


Expr = Union[IntLit, StringLit, BoolLit, NilLit, ArrayLit, Ident, BinOp, UnaryOp,
             IndexExpr, CallExpr, Assign, IndexAssign]


# --------------------------------------------------------------------------- #
# Statements                                                                   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class VarDecl:
    name: str
    type_annot: TypeNode | None
    value: Expr
    is_const: bool
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class ExprStmt:
    expr: Expr
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class Block:
    stmts: tuple["Stmt", ...]
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class IfStmt:
    cond: Expr
    then_branch: Block
    else_branch: Block | None
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class WhileStmt:
    cond: Expr
    body: Block
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class ForStmt:
    """``for var in start..end { ... }`` — range-based loop."""
    var: str
    start: Expr
    end: Expr
    body: Block
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class ReturnStmt:
    value: Expr | None
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class BreakStmt:
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class ContinueStmt:
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class FuncDecl:
    name: str
    params: tuple[tuple[str, TypeNode], ...]
    ret_type: TypeNode
    body: Block
    line: int = 0
    col: int = 0


Stmt = Union[VarDecl, ExprStmt, Block, IfStmt, WhileStmt, ForStmt,
             ReturnStmt, BreakStmt, ContinueStmt, FuncDecl]


@dataclass(frozen=True, slots=True)
class Program:
    """The top-level AST: a list of statements."""
    stmts: tuple[Stmt, ...]