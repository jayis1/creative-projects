"""MiniLang type checker.

Performs bidirectional type inference: every expression gets a type, every
declaration's type is checked for consistency.  The checker enforces:

* arithmetic only on ``int``
* comparisons on ``int`` (``< <= > >=``) and equality on same-type operands
* logical operators on ``bool``
* array indexing requires an ``array<T>`` and an ``int`` index, yields ``T``
* array literals infer ``array<T>`` from elements (all same type)
* function call: callee is a ``fn`` type, argument count & types match
* assignment: RHS type matches variable's declared/inferred type
* ``return`` inside the body must match the declared return type
* ``break``/``continue`` only inside loops

The checker produces a :class:`TypedProgram` which the compiler uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from . import ast
from .ast import (
    ArrayLit, ArrayType, Assign, BinOp, Block, BoolLit, BoolType, BreakStmt,
    CallExpr, ContinueStmt, Expr, ExprStmt, ForStmt, FuncDecl, FuncType,
    Ident, IfStmt, IndexAssign, IndexExpr, IntLit, IntType, NilLit, Program,
    ReturnStmt, Stmt, StringLit, StringType, TypeNode, UnaryOp, UnitType,
    VarDecl, WhileStmt,
)
from .errors import MiniLangError


class TypeError(MiniLangError):
    """Raised for a type error."""


# --------------------------------------------------------------------------- #
# typed AST — same shape as the untyped AST but every expression carries       #
# a type and every function declaration has its resolved return type.          #
# We re-use the original AST nodes but annotate them through a side table.      #
# --------------------------------------------------------------------------- #
@dataclass
class FuncMeta:
    """Per-function metadata collected during checking."""
    name: str
    ftype: FuncType
    nlocals: int
    param_slots: dict[str, int]
    local_types: dict[str, TypeNode]


class Scope:
    """A lexical scope mapping variable names to (slot, type)."""

    def __init__(self, parent: "Scope | None" = None):
        self.parent = parent
        self.vars: dict[str, tuple[int, TypeNode]] = {}
        self.next_slot = parent.next_slot if parent else 0
        self.is_const: dict[str, bool] = {}

    def declare(self, name: str, t: TypeNode, const: bool = False) -> int:
        slot = self.next_slot
        self.vars[name] = (slot, t)
        self.next_slot += 1
        self.is_const[name] = const
        return slot

    def resolve(self, name: str) -> tuple[int, TypeNode] | None:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def is_const_var(self, name: str) -> bool:
        if name in self.is_const:
            return self.is_const[name]
        if self.parent:
            return self.parent.is_const_var(name)
        return False


class TypeChecker:
    """Walks the AST, checks types, allocates local slots, returns metadata."""

    # Built-in function signatures: name -> (param_types, return_type)
    BUILTINS: dict[str, tuple[tuple[TypeNode, ...], TypeNode]] = {
        "print": ((IntType(),), UnitType()),  # will accept any type
        "len": ((ArrayType(IntType()),), IntType()),  # array or string
        "push": ((ArrayType(IntType()), IntType()), UnitType()),  # any array + any
        "str": ((IntType(),), StringType()),  # any type
        "int": ((IntType(),), IntType()),  # string/bool/int
        "abs": ((IntType(),), IntType()),
        "max": ((IntType(), IntType()), IntType()),
        "min": ((IntType(), IntType()), IntType()),
        "assert": ((IntType(),), UnitType()),  # bool + optional string message
    }

    def __init__(self):
        self.functions: dict[str, FuncMeta] = {}
        self.expr_types: dict[int, TypeNode] = {}  # id(expr) -> type
        self.var_slots: dict[str, int] = {}
        self._loop_depth = 0
        self._current_ret: TypeNode | None = None

    def check(self, program: Program) -> None:
        # First pass: register function signatures so calls can resolve.
        for stmt in program.stmts:
            if isinstance(stmt, FuncDecl):
                self._declare_function(stmt)
        # Second pass: check function bodies and top-level statements.
        top_scope = Scope()
        for stmt in program.stmts:
            if isinstance(stmt, FuncDecl):
                self._check_func_body(stmt)
            else:
                self._check_stmt(stmt, top_scope)

    # -- function registration ------------------------------------------- #
    def _declare_function(self, decl: FuncDecl) -> None:
        if decl.name in self.functions:
            raise TypeError(f"duplicate function {decl.name!r}",
                             decl.line, decl.col)
        ftype = FuncType(tuple(p[1] for p in decl.params), decl.ret_type)
        self.functions[decl.name] = FuncMeta(
            name=decl.name, ftype=ftype, nlocals=len(decl.params),
            param_slots={}, local_types={},
        )

    def _check_func_body(self, decl: FuncDecl) -> None:
        meta = self.functions[decl.name]
        scope = Scope()
        slot = 0
        for pname, ptype in decl.params:
            scope.declare(pname, ptype)
            meta.param_slots[pname] = slot
            slot += 1
        meta.nlocals = slot
        self._current_ret = decl.ret_type
        self._check_block(decl.body, scope)
        # If declared return type is not unit, ensure all paths return.
        if isinstance(decl.ret_type, UnitType):
            pass
        else:
            if not self._block_always_returns(decl.body):
                raise TypeError(
                    f"function {decl.name!r} must return a value on all paths",
                    decl.line, decl.col)
        self._current_ret = None

    # -- statement checking ---------------------------------------------- #
    def _check_stmt(self, stmt: Stmt, scope: Scope) -> None:
        if isinstance(stmt, VarDecl):
            self._check_var_decl(stmt, scope)
        elif isinstance(stmt, ExprStmt):
            self.expr_types[id(stmt.expr)] = self._check_expr(stmt.expr, scope)
        elif isinstance(stmt, Block):
            self._check_block(stmt, scope)
        elif isinstance(stmt, IfStmt):
            self._check_if(stmt, scope)
        elif isinstance(stmt, WhileStmt):
            self._check_while(stmt, scope)
        elif isinstance(stmt, ForStmt):
            self._check_for(stmt, scope)
        elif isinstance(stmt, ReturnStmt):
            self._check_return(stmt, scope)
        elif isinstance(stmt, BreakStmt):
            if self._loop_depth == 0:
                raise TypeError("'break' outside loop", stmt.line, stmt.col)
        elif isinstance(stmt, ContinueStmt):
            if self._loop_depth == 0:
                raise TypeError("'continue' outside loop", stmt.line, stmt.col)
        elif isinstance(stmt, FuncDecl):
            self._check_func_body(stmt)
        else:
            raise TypeError(f"unchecked statement {type(stmt).__name__}")

    def _check_block(self, block: Block, parent: Scope) -> None:
        scope = Scope(parent)
        for s in block.stmts:
            self._check_stmt(s, scope)

    def _check_var_decl(self, decl: VarDecl, scope: Scope) -> None:
        val_type = self._check_expr(decl.value, scope)
        if decl.type_annot is not None:
            if not self._assignable(val_type, decl.type_annot):
                raise TypeError(
                    f"cannot assign {val_type} to {decl.type_annot}",
                    decl.line, decl.col)
            final_type = decl.type_annot
        else:
            final_type = val_type
        scope.declare(decl.name, final_type, decl.is_const)

    def _check_if(self, stmt: IfStmt, scope: Scope) -> None:
        ct = self._check_expr(stmt.cond, scope)
        if not isinstance(ct, BoolType):
            raise TypeError(f"if condition must be bool, got {ct}",
                             stmt.line, stmt.col)
        self._check_block(stmt.then_branch, scope)
        if stmt.else_branch is not None:
            self._check_block(stmt.else_branch, scope)

    def _check_while(self, stmt: WhileStmt, scope: Scope) -> None:
        ct = self._check_expr(stmt.cond, scope)
        if not isinstance(ct, BoolType):
            raise TypeError(f"while condition must be bool, got {ct}",
                             stmt.line, stmt.col)
        self._loop_depth += 1
        self._check_block(stmt.body, scope)
        self._loop_depth -= 1

    def _check_for(self, stmt: ForStmt, scope: Scope) -> None:
        st = self._check_expr(stmt.start, scope)
        et = self._check_expr(stmt.end, scope)
        if not isinstance(st, IntType) or not isinstance(et, IntType):
            raise TypeError("for range bounds must be int", stmt.line, stmt.col)
        body_scope = Scope(scope)
        body_scope.declare(stmt.var, IntType())
        self._loop_depth += 1
        self._check_block(stmt.body, body_scope)
        self._loop_depth -= 1

    def _check_return(self, stmt: ReturnStmt, scope: Scope) -> None:
        if self._current_ret is None:
            raise TypeError("'return' outside function", stmt.line, stmt.col)
        if stmt.value is None:
            if not isinstance(self._current_ret, UnitType):
                raise TypeError("missing return value", stmt.line, stmt.col)
        else:
            vt = self._check_expr(stmt.value, scope)
            if not self._assignable(vt, self._current_ret):
                raise TypeError(
                    f"return type {vt} does not match {self._current_ret}",
                    stmt.line, stmt.col)

    # -- expression checking --------------------------------------------- #
    def _check_expr(self, expr: Expr, scope: Scope) -> TypeNode:
        if isinstance(expr, IntLit):
            t: TypeNode = IntType()
        elif isinstance(expr, StringLit):
            t = StringType()
        elif isinstance(expr, BoolLit):
            t = BoolType()
        elif isinstance(expr, NilLit):
            t = UnitType()
        elif isinstance(expr, ArrayLit):
            if not expr.elements:
                t = ArrayType(IntType())  # default empty-array element type
            else:
                elem_types = [self._check_expr(e, scope) for e in expr.elements]
                first = elem_types[0]
                for et_ in elem_types[1:]:
                    if not self._assignable(et_, first):
                        raise TypeError("array literal has mixed types",
                                         expr.line, expr.col)
                t = ArrayType(first)
        elif isinstance(expr, Ident):
            r = scope.resolve(expr.name)
            if r is None:
                if expr.name in self.functions:
                    t = self.functions[expr.name].ftype
                else:
                    raise TypeError(f"undefined variable {expr.name!r}",
                                    expr.line, expr.col)
            else:
                t = r[1]
        elif isinstance(expr, BinOp):
            t = self._check_binop(expr, scope)
        elif isinstance(expr, UnaryOp):
            ot = self._check_expr(expr.operand, scope)
            if expr.op == "-":
                if not isinstance(ot, IntType):
                    raise TypeError("unary '-' requires int", expr.line, expr.col)
                t = IntType()
            else:  # '!'
                if not isinstance(ot, BoolType):
                    raise TypeError("'!' requires bool", expr.line, expr.col)
                t = BoolType()
        elif isinstance(expr, IndexExpr):
            at = self._check_expr(expr.array, scope)
            it = self._check_expr(expr.index, scope)
            if not isinstance(at, ArrayType):
                raise TypeError(f"cannot index {at}", expr.line, expr.col)
            if not isinstance(it, IntType):
                raise TypeError("array index must be int", expr.line, expr.col)
            t = at.element
        elif isinstance(expr, IndexAssign):
            at = self._check_expr(expr.array, scope)
            it = self._check_expr(expr.index, scope)
            vt = self._check_expr(expr.value, scope)
            if not isinstance(at, ArrayType):
                raise TypeError(f"cannot index {at}", expr.line, expr.col)
            if not isinstance(it, IntType):
                raise TypeError("array index must be int", expr.line, expr.col)
            if not self._assignable(vt, at.element):
                raise TypeError(f"cannot assign {vt} to {at}", expr.line, expr.col)
            t = UnitType()
        elif isinstance(expr, CallExpr):
            t = self._check_call(expr, scope)
        elif isinstance(expr, Assign):
            t = self._check_assign(expr, scope)
        else:
            raise TypeError(f"unchecked expression {type(expr).__name__}")
        self.expr_types[id(expr)] = t
        return t

    def _check_binop(self, expr: BinOp, scope: Scope) -> TypeNode:
        lt = self._check_expr(expr.left, scope)
        rt = self._check_expr(expr.right, scope)
        op = expr.op
        if op == "+":
            # String concatenation: string + string -> string
            if isinstance(lt, StringType) and isinstance(rt, StringType):
                return StringType()
            # Int addition
            if isinstance(lt, IntType) and isinstance(rt, IntType):
                return IntType()
            raise TypeError(f"'+' requires int+int or string+string, got {lt}, {rt}",
                            expr.line, expr.col)
        if op in ("-", "*", "/", "%"):
            if not isinstance(lt, IntType) or not isinstance(rt, IntType):
                raise TypeError(f"'{op}' requires int operands", expr.line, expr.col)
            return IntType()
        if op in ("<", "<=", ">", ">="):
            # Allow comparisons on both int and string (lexicographic)
            if isinstance(lt, IntType) and isinstance(rt, IntType):
                return BoolType()
            if isinstance(lt, StringType) and isinstance(rt, StringType):
                return BoolType()
            raise TypeError(f"'{op}' requires int or string operands, got {lt}, {rt}",
                            expr.line, expr.col)
        if op in ("==", "!="):
            if not self._assignable(lt, rt) and not self._assignable(rt, lt):
                raise TypeError(f"'{op}' on incompatible types {lt}, {rt}",
                                expr.line, expr.col)
            return BoolType()
        if op in ("&&", "||"):
            if not isinstance(lt, BoolType) or not isinstance(rt, BoolType):
                raise TypeError(f"'{op}' requires bool operands", expr.line, expr.col)
            return BoolType()
        raise TypeError(f"unknown operator {op!r}")

    def _check_call(self, expr: CallExpr, scope: Scope) -> TypeNode:
        if isinstance(expr.callee, Ident) and expr.callee.name in self.functions:
            meta = self.functions[expr.callee.name]
            ftype = meta.ftype
        elif isinstance(expr.callee, Ident) and expr.callee.name in self.BUILTINS:
            # Builtins: len/str/int/push accept specific types.
            name = expr.callee.name
            if name == "print":
                if len(expr.args) != 1:
                    raise TypeError("print expects 1 argument", expr.line, expr.col)
                self._check_expr(expr.args[0], scope)
                return UnitType()
            if name == "len":
                if len(expr.args) != 1:
                    raise TypeError("len expects 1 argument", expr.line, expr.col)
                at = self._check_expr(expr.args[0], scope)
                if not (isinstance(at, ArrayType) or isinstance(at, StringType)):
                    raise TypeError(f"len() expects array or string, got {at}",
                                    expr.line, expr.col)
                return IntType()
            if name == "str":
                if len(expr.args) != 1:
                    raise TypeError("str expects 1 argument", expr.line, expr.col)
                self._check_expr(expr.args[0], scope)
                return StringType()
            if name == "int":
                if len(expr.args) != 1:
                    raise TypeError("int expects 1 argument", expr.line, expr.col)
                at = self._check_expr(expr.args[0], scope)
                if not (isinstance(at, IntType) or isinstance(at, StringType)
                        or isinstance(at, BoolType)):
                    raise TypeError(f"int() expects string/bool/int, got {at}",
                                    expr.line, expr.col)
                return IntType()
            if name == "push":
                if len(expr.args) != 2:
                    raise TypeError("push expects 2 arguments", expr.line, expr.col)
                at = self._check_expr(expr.args[0], scope)
                self._check_expr(expr.args[1], scope)
                if not isinstance(at, ArrayType):
                    raise TypeError(f"push() expects array, got {at}",
                                    expr.line, expr.col)
                return UnitType()
            if name == "abs":
                if len(expr.args) != 1:
                    raise TypeError("abs expects 1 argument", expr.line, expr.col)
                at = self._check_expr(expr.args[0], scope)
                if not isinstance(at, IntType):
                    raise TypeError(f"abs() expects int, got {at}", expr.line, expr.col)
                return IntType()
            if name == "max" or name == "min":
                if len(expr.args) != 2:
                    raise TypeError(f"{name} expects 2 arguments", expr.line, expr.col)
                at1 = self._check_expr(expr.args[0], scope)
                at2 = self._check_expr(expr.args[1], scope)
                if not isinstance(at1, IntType) or not isinstance(at2, IntType):
                    raise TypeError(f"{name}() expects int, got {at1}, {at2}",
                                    expr.line, expr.col)
                return IntType()
            if name == "assert":
                if len(expr.args) < 1 or len(expr.args) > 2:
                    raise TypeError("assert expects 1 or 2 arguments", expr.line, expr.col)
                at = self._check_expr(expr.args[0], scope)
                if not isinstance(at, BoolType):
                    raise TypeError(f"assert() expects bool, got {at}", expr.line, expr.col)
                if len(expr.args) == 2:
                    mt = self._check_expr(expr.args[1], scope)
                    if not isinstance(mt, StringType):
                        raise TypeError("assert message must be string", expr.line, expr.col)
                return UnitType()
            raise TypeError(f"unknown builtin {name}", expr.line, expr.col)
        else:
            ct = self._check_expr(expr.callee, scope)
            if not isinstance(ct, FuncType):
                raise TypeError(f"cannot call {ct}", expr.line, expr.col)
            ftype = ct
        if len(expr.args) != len(ftype.params):
            raise TypeError(
                f"function expects {len(ftype.params)} args, got {len(expr.args)}",
                expr.line, expr.col)
        for i, (arg, ptype) in enumerate(zip(expr.args, ftype.params)):
            at = self._check_expr(arg, scope)
            if not self._assignable(at, ptype):
                raise TypeError(
                    f"argument {i} type {at} does not match {ptype}",
                    expr.line, expr.col)
        return ftype.ret

    def _check_assign(self, expr: Assign, scope: Scope) -> TypeNode:
        r = scope.resolve(expr.name)
        if r is None:
            raise TypeError(f"assignment to undefined variable {expr.name!r}",
                            expr.line, expr.col)
        slot, var_type = r
        if scope.is_const_var(expr.name):
            raise TypeError(f"cannot assign to const {expr.name!r}",
                            expr.line, expr.col)
        vt = self._check_expr(expr.value, scope)
        if not self._assignable(vt, var_type):
            raise TypeError(f"cannot assign {vt} to {var_type}",
                            expr.line, expr.col)
        return var_type

    # -- helpers --------------------------------------------------------- #
    @staticmethod
    def _assignable(src: TypeNode, dst: TypeNode) -> bool:
        # Unit is assignable to unit only; otherwise structural equality.
        if isinstance(src, UnitType) and isinstance(dst, UnitType):
            return True
        if isinstance(src, IntType) and isinstance(dst, IntType):
            return True
        if isinstance(src, StringType) and isinstance(dst, StringType):
            return True
        if isinstance(src, BoolType) and isinstance(dst, BoolType):
            return True
        if isinstance(src, ArrayType) and isinstance(dst, ArrayType):
            return TypeChecker._assignable(src.element, dst.element)
        if isinstance(src, FuncType) and isinstance(dst, FuncType):
            if len(src.params) != len(dst.params):
                return False
            for a, b in zip(src.params, dst.params):
                if not TypeChecker._assignable(a, b):
                    return False
            return TypeChecker._assignable(src.ret, dst.ret)
        return False

    def _block_always_returns(self, block: Block) -> bool:
        for s in block.stmts:
            if isinstance(s, ReturnStmt):
                return True
            if isinstance(s, IfStmt) and s.else_branch is not None:
                if (self._block_always_returns(s.then_branch)
                        and self._block_always_returns(s.else_branch)):
                    return True
        return False


def check_program(program: Program) -> TypeChecker:
    """Type-check *program* and return the :class:`TypeChecker` with metadata."""
    tc = TypeChecker()
    tc.check(program)
    return tc