"""MiniLang compiler — AST → bytecode.

Walks the typed AST and emits a flat bytecode chunk for the top-level program,
plus one chunk per function declaration.  Local variables are allocated to
slots by the type checker; the compiler reuses that slot mapping.

Control flow is compiled with jump-and-patch: forward jumps are emitted with
a placeholder operand, then patched once the target PC is known.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from . import ast
from .ast import (
    ArrayLit, Assign, BinOp, Block, BoolLit, BreakStmt, CallExpr, ContinueStmt,
    Expr, ExprStmt, ForStmt, FuncDecl, Ident, IfStmt, IndexAssign, IndexExpr,
    IntLit, NilLit, Program, ReturnStmt, Stmt, StringLit, UnaryOp, VarDecl,
    WhileStmt,
)
from .bytecode import Instruction, OpCode
from .errors import CompileError, MiniLangError
from .types import TypeChecker


# Built-in function names known to the compiler and VM.
BUILTIN_NAMES = {"print", "len", "push", "str", "int", "abs", "max", "min", "assert"}


@dataclass
class Chunk:
    """A compiled bytecode chunk (one per function)."""
    name: str
    code: list[Instruction] = field(default_factory=list)
    strings: list[str] = field(default_factory=list)
    nlocals: int = 0
    nparams: int = 0

    def add(self, op: OpCode, operand: int = 0, line: int = 0) -> int:
        idx = len(self.code)
        self.code.append(Instruction(op, operand, line))
        return idx

    def patch(self, idx: int, target: int) -> None:
        self.code[idx].operand = target

    def add_string(self, s: str) -> int:
        idx = len(self.strings)
        self.strings.append(s)
        return idx


@dataclass
class CompiledProgram:
    main: Chunk
    functions: dict[str, Chunk]
    strings: list[str]   # global string pool (main + all functions merged)
    debug: bool = False

    def all_chunks(self) -> list[Chunk]:
        return [self.main] + list(self.functions.values())


class Compiler:
    """Compiles a :class:`Program` AST into a :class:`CompiledProgram`."""

    def __init__(self, program: Program, tc: TypeChecker, debug: bool = False):
        self.program = program
        self.tc = tc
        self.debug = debug
        self.main = Chunk("main")
        self.functions: dict[str, Chunk] = {}
        self._scope_stack: list[dict[str, int]] = [{}]
        self._loop_stack: list[tuple[int, int]] = []  # (break_target, continue_target) indices
        self._break_targets: list[int] = []
        self._continue_targets: list[int] = []
        self._current_chunk: Chunk = self.main
        self._func_ret: bool = False  # True if inside a function

    def all_chunks(self) -> list[Chunk]:
        return [self.main] + list(self.functions.values())

    def compile(self) -> CompiledProgram:
        # Pre-register all function names so recursive/mutual calls resolve.
        for stmt in self.program.stmts:
            if isinstance(stmt, FuncDecl):
                self.functions[stmt.name] = Chunk(stmt.name)  # placeholder
        # Compile function bodies first so that CALL targets are known.
        for stmt in self.program.stmts:
            if isinstance(stmt, FuncDecl):
                self._compile_func(stmt)
        # Compile top-level statements into main chunk.
        self._current_chunk = self.main
        self._scope_stack = [{}]
        top_scope = ScopeFrame()
        for stmt in self.program.stmts:
            if not isinstance(stmt, FuncDecl):
                self._compile_stmt(stmt, top_scope)
        self.main.nlocals = max(top_scope._next, 1)
        self.main.add(OpCode.HALT, 0, 0)
        # Merge all string pools into one global pool and remap indices.
        global_strings: list[str] = []
        global_pool: dict[str, int] = {}
        for chunk in self.all_chunks():
            remap: dict[int, int] = {}
            for i, s in enumerate(chunk.strings):
                if s not in global_pool:
                    global_pool[s] = len(global_strings)
                    global_strings.append(s)
                remap[i] = global_pool[s]
            for ins in chunk.code:
                if ins.op == OpCode.PUSH_STR:
                    ins.operand = remap[ins.operand]
                elif ins.op == OpCode.CALL:
                    # CALL operand = arg_count * 10000 + name_idx
                    arg_count = ins.operand // 10000
                    name_idx = ins.operand % 10000
                    ins.operand = arg_count * 10000 + remap[name_idx]
            chunk.strings = global_strings
        return CompiledProgram(self.main, self.functions, global_strings, self.debug)

    # ------------------------------------------------------------------ #
    # function compilation                                                #
    # ------------------------------------------------------------------ #
    def _compile_func(self, decl: FuncDecl) -> None:
        chunk = Chunk(decl.name, nparams=len(decl.params))
        prev_chunk = self._current_chunk
        self._current_chunk = chunk
        meta = self.tc.functions[decl.name]
        # Build local scope: parameters occupy slots 0..nparams-1.
        # Use a shared counter so nested scopes allocate distinct slots.
        shared_counter = [len(decl.params)]
        scope = ScopeFrame(counter=shared_counter)
        for i, (pname, _) in enumerate(decl.params):
            scope._vars[pname] = i
        chunk.nlocals = meta.nlocals
        prev_ret = self._func_ret
        self._func_ret = True
        self._scope_stack.append(scope)
        body_scope = ScopeFrame(parent=scope)
        self._compile_block(decl.body, body_scope)
        # Update nlocals to include all locals (params + body vars).
        chunk.nlocals = max(body_scope._next, chunk.nparams)
        self._scope_stack.pop()
        self._func_ret = prev_ret
        # If the function body falls off the end without return, emit one
        # for unit-returning functions.  The type checker ensures non-unit
        # functions always return.
        if isinstance(decl.ret_type, ast.UnitType):
            chunk.add(OpCode.RETURN, 0, decl.line)
        self.functions[decl.name] = chunk
        self._current_chunk = prev_chunk

    # ------------------------------------------------------------------ #
    # statement compilation                                               #
    # ------------------------------------------------------------------ #
    def _compile_stmt(self, stmt: Stmt, scope: "ScopeFrame") -> None:
        if isinstance(stmt, VarDecl):
            self._compile_var_decl(stmt, scope)
        elif isinstance(stmt, ExprStmt):
            self._compile_expr(stmt.expr, scope)
            # Discard the value if the expression produces one.
            etype = self.tc.expr_types.get(id(stmt.expr))
            if not isinstance(etype, ast.UnitType):
                self._current_chunk.add(OpCode.POP, 0, stmt.line)
        elif isinstance(stmt, Block):
            self._compile_block(stmt, ScopeFrame(parent=scope))
        elif isinstance(stmt, IfStmt):
            self._compile_if(stmt, scope)
        elif isinstance(stmt, WhileStmt):
            self._compile_while(stmt, scope)
        elif isinstance(stmt, ForStmt):
            self._compile_for(stmt, scope)
        elif isinstance(stmt, ReturnStmt):
            self._compile_return(stmt, scope)
        elif isinstance(stmt, BreakStmt):
            if not self._loop_stack:
                raise CompileError("'break' outside loop", stmt.line, stmt.col)
            brk_idx = self._current_chunk.add(OpCode.JUMP, 0, stmt.line)
            self._break_targets.append(brk_idx)
        elif isinstance(stmt, ContinueStmt):
            if not self._loop_stack:
                raise CompileError("'continue' outside loop", stmt.line, stmt.col)
            cont_idx = self._current_chunk.add(OpCode.JUMP, 0, stmt.line)
            self._continue_targets.append(cont_idx)
        elif isinstance(stmt, FuncDecl):
            pass  # already compiled in compile()
        else:
            raise CompileError(f"cannot compile {type(stmt).__name__}")

    def _compile_var_decl(self, decl: VarDecl, scope: "ScopeFrame") -> None:
        slot = scope.declare(decl.name)
        self._compile_expr(decl.value, scope)
        self._current_chunk.add(OpCode.STORE_LOCAL, slot, decl.line)

    def _compile_block(self, block: Block, scope: "ScopeFrame") -> None:
        for s in block.stmts:
            self._compile_stmt(s, scope)

    def _compile_if(self, stmt: IfStmt, scope: "ScopeFrame") -> None:
        self._compile_expr(stmt.cond, scope)
        jfalse = self._current_chunk.add(OpCode.JUMP_IF_FALSE, 0, stmt.line)
        self._compile_block(stmt.then_branch, ScopeFrame(parent=scope))
        if stmt.else_branch is not None:
            jend = self._current_chunk.add(OpCode.JUMP, 0, stmt.line)
            self._current_chunk.patch(jfalse, len(self._current_chunk.code))
            self._compile_block(stmt.else_branch, ScopeFrame(parent=scope))
            self._current_chunk.patch(jend, len(self._current_chunk.code))
        else:
            self._current_chunk.patch(jfalse, len(self._current_chunk.code))

    def _compile_while(self, stmt: WhileStmt, scope: "ScopeFrame") -> None:
        start = len(self._current_chunk.code)
        self._compile_expr(stmt.cond, scope)
        jfalse = self._current_chunk.add(OpCode.JUMP_IF_FALSE, 0, stmt.line)
        body_scope = ScopeFrame(parent=scope)
        self._break_targets = []
        self._continue_targets = []
        self._loop_stack.append((0, start))
        try:
            self._compile_block(stmt.body, body_scope)
        finally:
            self._loop_stack.pop()
        self._current_chunk.add(OpCode.JUMP, start, stmt.line)
        end = len(self._current_chunk.code)
        self._current_chunk.patch(jfalse, end)
        for brk in getattr(self, "_break_targets", []):
            self._current_chunk.patch(brk, end)
        # In while loops, continue jumps to the condition (start).
        for ct in self._continue_targets:
            self._current_chunk.code[ct].operand = start
        self._break_targets = []

    def _compile_for(self, stmt: ForStmt, scope: "ScopeFrame") -> None:
        # Allocate loop variable as a new local.
        slot = scope.declare(stmt.var)
        # Compile start expression and store in loop var.
        self._compile_expr(stmt.start, scope)
        self._current_chunk.add(OpCode.STORE_LOCAL, slot, stmt.line)
        # Compile end expression and store in a hidden temp local.
        end_slot = scope.declare("__for_end_" + stmt.var)
        self._compile_expr(stmt.end, scope)
        self._current_chunk.add(OpCode.STORE_LOCAL, end_slot, stmt.line)
        # Loop:
        start = len(self._current_chunk.code)
        # Load loop var, load end, compare (i < end).
        self._current_chunk.add(OpCode.LOAD_LOCAL, slot, stmt.line)
        self._current_chunk.add(OpCode.LOAD_LOCAL, end_slot, stmt.line)
        self._current_chunk.add(OpCode.LT, 0, stmt.line)
        jfalse = self._current_chunk.add(OpCode.JUMP_IF_FALSE, 0, stmt.line)
        body_scope = ScopeFrame(parent=scope)
        # Re-bind the loop variable in the body scope (already in parent).
        self._break_targets = []
        # continue should jump to the increment section, not the comparison.
        # We'll record the increment position after the body.
        self._continue_targets: list[int] = []
        self._loop_stack.append((0, -1))  # -1 = placeholder, patched below
        try:
            self._compile_block(stmt.body, body_scope)
        finally:
            self._loop_stack.pop()
        # Increment section: continue jumps here.
        increment_pc = len(self._current_chunk.code)
        # Patch all continue jumps to point to the increment section.
        for ct in self._continue_targets:
            self._current_chunk.code[ct].operand = increment_pc
        self._current_chunk.add(OpCode.LOAD_LOCAL, slot, stmt.line)
        self._current_chunk.add(OpCode.PUSH_INT, 1, stmt.line)
        self._current_chunk.add(OpCode.ADD, 0, stmt.line)
        self._current_chunk.add(OpCode.STORE_LOCAL, slot, stmt.line)
        self._current_chunk.add(OpCode.JUMP, start, stmt.line)
        end = len(self._current_chunk.code)
        self._current_chunk.patch(jfalse, end)
        for brk in getattr(self, "_break_targets", []):
            self._current_chunk.patch(brk, end)
        self._break_targets = []

    def _compile_return(self, stmt: ReturnStmt, scope: "ScopeFrame") -> None:
        if stmt.value is None:
            self._current_chunk.add(OpCode.RETURN, 0, stmt.line)
        else:
            self._compile_expr(stmt.value, scope)
            self._current_chunk.add(OpCode.RETURN, 1, stmt.line)

    # ------------------------------------------------------------------ #
    # expression compilation                                              #
    # ------------------------------------------------------------------ #
    def _compile_expr(self, expr: Expr, scope: "ScopeFrame") -> None:
        if isinstance(expr, IntLit):
            self._current_chunk.add(OpCode.PUSH_INT, expr.value, expr.line)
        elif isinstance(expr, StringLit):
            idx = self._current_chunk.add_string(expr.value)
            self._current_chunk.add(OpCode.PUSH_STR, idx, expr.line)
        elif isinstance(expr, BoolLit):
            self._current_chunk.add(OpCode.PUSH_BOOL, 1 if expr.value else 0, expr.line)
        elif isinstance(expr, NilLit):
            self._current_chunk.add(OpCode.PUSH_NIL, 0, expr.line)
        elif isinstance(expr, ArrayLit):
            for e in expr.elements:
                self._compile_expr(e, scope)
            self._current_chunk.add(OpCode.NEW_ARRAY, len(expr.elements), expr.line)
        elif isinstance(expr, Ident):
            slot = scope.resolve(expr.name)
            if slot is not None:
                self._current_chunk.add(OpCode.LOAD_LOCAL, slot, expr.line)
            elif expr.name in self.functions:
                # Function reference used as a value → push closure placeholder.
                # We encode this as a PUSH_STR with the function name; the VM
                # resolves it to a Closure at runtime.
                idx = self._current_chunk.add_string("fn:" + expr.name)
                self._current_chunk.add(OpCode.PUSH_STR, idx, expr.line)
            else:
                raise CompileError(f"undefined variable {expr.name!r}",
                                   expr.line, expr.col)
        elif isinstance(expr, BinOp):
            self._compile_binop(expr, scope)
        elif isinstance(expr, UnaryOp):
            self._compile_expr(expr.operand, scope)
            if expr.op == "-":
                self._current_chunk.add(OpCode.NEG, 0, expr.line)
            else:  # '!'
                self._current_chunk.add(OpCode.NOT, 0, expr.line)
        elif isinstance(expr, IndexExpr):
            self._compile_expr(expr.array, scope)
            self._compile_expr(expr.index, scope)
            self._current_chunk.add(OpCode.INDEX_GET, 0, expr.line)
        elif isinstance(expr, IndexAssign):
            self._compile_expr(expr.array, scope)
            self._compile_expr(expr.index, scope)
            self._compile_expr(expr.value, scope)
            self._current_chunk.add(OpCode.INDEX_SET, 0, expr.line)
        elif isinstance(expr, CallExpr):
            self._compile_call(expr, scope)
        elif isinstance(expr, Assign):
            self._compile_expr(expr.value, scope)
            slot = scope.resolve(expr.name)
            if slot is None:
                raise CompileError(f"assignment to undefined {expr.name!r}",
                                   expr.line, expr.col)
            # DUP_TOP so the assignment expression evaluates to the value.
            self._current_chunk.add(OpCode.STORE_LOCAL, slot, expr.line)
            self._current_chunk.add(OpCode.LOAD_LOCAL, slot, expr.line)
        else:
            raise CompileError(f"cannot compile {type(expr).__name__}")

    def _compile_binop(self, expr: BinOp, scope: "ScopeFrame") -> None:
        # Short-circuit evaluation for && and ||
        if expr.op == "&&":
            self._compile_expr(expr.left, scope)
            jfalse = self._current_chunk.add(OpCode.JUMP_IF_FALSE, 0, expr.line)
            self._compile_expr(expr.right, scope)
            # If right is true, result is true; if false, result false.
            jend = self._current_chunk.add(OpCode.JUMP, 0, expr.line)
            self._current_chunk.patch(jfalse, len(self._current_chunk.code))
            self._current_chunk.add(OpCode.PUSH_BOOL, 0, expr.line)
            self._current_chunk.patch(jend, len(self._current_chunk.code))
            return
        if expr.op == "||":
            self._compile_expr(expr.left, scope)
            jtrue = self._current_chunk.add(OpCode.JUMP_IF_TRUE, 0, expr.line)
            self._compile_expr(expr.right, scope)
            jend = self._current_chunk.add(OpCode.JUMP, 0, expr.line)
            self._current_chunk.patch(jtrue, len(self._current_chunk.code))
            self._current_chunk.add(OpCode.PUSH_BOOL, 1, expr.line)
            self._current_chunk.patch(jend, len(self._current_chunk.code))
            return
        self._compile_expr(expr.left, scope)
        self._compile_expr(expr.right, scope)
        op_map = {
            "+": OpCode.ADD, "-": OpCode.SUB, "*": OpCode.MUL,
            "/": OpCode.DIV, "%": OpCode.MOD,
            "==": OpCode.EQ, "!=": OpCode.NEQ,
            "<": OpCode.LT, "<=": OpCode.LE, ">": OpCode.GT, ">=": OpCode.GE,
        }
        self._current_chunk.add(op_map[expr.op], 0, expr.line)

    def _compile_call(self, expr: CallExpr, scope: "ScopeFrame") -> None:
        # Only direct calls to named functions are supported in v1.
        if isinstance(expr.callee, Ident):
            fname = expr.callee.name
            if fname in self.functions or fname in BUILTIN_NAMES:
                # Evaluate args left-to-right.
                for arg in expr.args:
                    self._compile_expr(arg, scope)
                self._current_chunk.add(OpCode.CALL, len(expr.args), expr.line)
                # The operand encodes the function name index; we use a string
                # constant to carry it.
                name_idx = self._current_chunk.add_string("call:" + fname)
                # Replace the CALL instruction operand with the name index.
                self._current_chunk.code[-1].operand = len(expr.args) * 10000 + name_idx
                return
        raise CompileError("only direct function calls are supported",
                           expr.line, expr.col)


class ScopeFrame:
    """Compile-time scope mapping variable names to local slots.

    All scopes in a function share a single ``_next`` counter so that nested
    blocks allocate distinct slots and the function's ``nlocals`` is correct.
    """

    def __init__(self, vars: dict[str, int] | None = None,
                 parent: "ScopeFrame | None" = None,
                 counter: list[int] | None = None):
        self._vars = vars if vars is not None else {}
        self._parent = parent
        # Shared mutable counter [next_slot] across all scopes in a function.
        if counter is not None:
            self._counter = counter
        elif parent is not None:
            self._counter = parent._counter
        else:
            self._counter = [0]

    def declare(self, name: str) -> int:
        slot = self._counter[0]
        self._vars[name] = slot
        self._counter[0] += 1
        return slot

    def resolve(self, name: str) -> int | None:
        if name in self._vars:
            return self._vars[name]
        if self._parent:
            return self._parent.resolve(name)
        return None

    @property
    def _next(self) -> int:
        return self._counter[0]


def compile_program(source: str, name: str = "<string>", debug: bool = False) -> CompiledProgram:
    """Full pipeline: lex → parse → type-check → compile.

    The *source* string is attached to errors so that :meth:`MiniLangError.format`
    can show source context with a caret.
    """
    from .lexer import tokenize
    from .parser import Parser
    try:
        prog = Parser(tokenize(source, name), name).parse_program()
    except MiniLangError as e:
        e.source = source
        raise
    tc = TypeChecker()
    try:
        tc.check(prog)
    except MiniLangError as e:
        e.source = source
        raise
    try:
        return Compiler(prog, tc, debug).compile()
    except MiniLangError as e:
        e.source = source
        raise