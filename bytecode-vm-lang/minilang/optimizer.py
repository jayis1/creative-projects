"""MiniLang AST-level optimizer.

Performs three optimization passes:

1. **Constant folding** — evaluates expressions with literal operands at
   compile time (e.g. ``2 + 3`` → ``5``).
2. **Dead-code elimination** — removes statements after an unconditional
   ``return``/``break``/``continue`` in the same block.
3. **Jump threading** — collapses ``JUMP → JUMP`` chains in the bytecode.

The optimizer operates on the AST *before* type-checking for folding and
dead-code elimination, and on the bytecode *after* compilation for jump
threading.
"""

from __future__ import annotations

from . import ast
from .ast import (
    ArrayLit, BinOp, Block, BoolLit, BreakStmt, ContinueStmt, Expr, IntLit,
    Program, ReturnStmt, Stmt, StringLit, UnaryOp, WhileStmt, IfStmt,
)
from .bytecode import Instruction, OpCode
from .compiler import CompiledProgram


# --------------------------------------------------------------------------- #
# AST-level passes                                                             #
# --------------------------------------------------------------------------- #
class ConstantFolder:
    """Fold constant expressions in the AST."""

    def optimize(self, program: Program) -> Program:
        new_stmts = tuple(self._opt_stmt(s) for s in program.stmts)
        return Program(new_stmts)

    def _opt_stmt(self, stmt: Stmt) -> Stmt:
        if isinstance(stmt, ast.VarDecl):
            return ast.VarDecl(stmt.name, stmt.type_annot,
                                self._opt_expr(stmt.value), stmt.is_const,
                                stmt.line, stmt.col)
        if isinstance(stmt, ast.ExprStmt):
            return ast.ExprStmt(self._opt_expr(stmt.expr), stmt.line, stmt.col)
        if isinstance(stmt, Block):
            return Block(tuple(self._opt_stmt(s) for s in stmt.stmts),
                         stmt.line, stmt.col)
        if isinstance(stmt, IfStmt):
            cond = self._opt_expr(stmt.cond)
            then_b = Block(tuple(self._opt_stmt(s) for s in stmt.then_branch.stmts),
                            stmt.then_branch.line, stmt.then_branch.col)
            else_b = None
            if stmt.else_branch is not None:
                else_b = Block(tuple(self._opt_stmt(s) for s in stmt.else_branch.stmts),
                               stmt.else_branch.line, stmt.else_branch.col)
            # Fold: if true → then only; if false → else only.
            if isinstance(cond, BoolLit):
                if cond.value:
                    return then_b
                return else_b if else_b is not None else Block(())
            return IfStmt(cond, then_b, else_b, stmt.line, stmt.col)
        if isinstance(stmt, WhileStmt):
            cond = self._opt_expr(stmt.cond)
            body = Block(tuple(self._opt_stmt(s) for s in stmt.body.stmts),
                         stmt.body.line, stmt.body.col)
            # while false → skip entirely.
            if isinstance(cond, BoolLit) and not cond.value:
                return Block(())
            return WhileStmt(cond, body, stmt.line, stmt.col)
        if isinstance(stmt, ast.ForStmt):
            start = self._opt_expr(stmt.start)
            end = self._opt_expr(stmt.end)
            body = Block(tuple(self._opt_stmt(s) for s in stmt.body.stmts),
                         stmt.body.line, stmt.body.col)
            return ast.ForStmt(stmt.var, start, end, body, stmt.line, stmt.col)
        if isinstance(stmt, ReturnStmt):
            val = self._opt_expr(stmt.value) if stmt.value is not None else None
            return ReturnStmt(val, stmt.line, stmt.col)
        if isinstance(stmt, ast.FuncDecl):
            body = Block(tuple(self._opt_stmt(s) for s in stmt.body.stmts),
                         stmt.body.line, stmt.body.col)
            return ast.FuncDecl(stmt.name, stmt.params, stmt.ret_type, body,
                                stmt.line, stmt.col)
        return stmt

    def _opt_expr(self, expr: Expr) -> Expr:
        if isinstance(expr, BinOp):
            left = self._opt_expr(expr.left)
            right = self._opt_expr(expr.right)
            folded = self._try_fold(expr.op, left, right)
            if folded is not None:
                return folded
            return BinOp(expr.op, left, right, expr.line, expr.col)
        if isinstance(expr, UnaryOp):
            operand = self._opt_expr(expr.operand)
            if expr.op == "-" and isinstance(operand, IntLit):
                return IntLit(-operand.value, expr.line, expr.col)
            if expr.op == "!" and isinstance(operand, BoolLit):
                return BoolLit(not operand.value, expr.line, expr.col)
            return UnaryOp(expr.op, operand, expr.line, expr.col)
        if isinstance(expr, ast.ArrayLit):
            return ArrayLit(tuple(self._opt_expr(e) for e in expr.elements),
                            expr.line, expr.col)
        if isinstance(expr, ast.IndexExpr):
            return ast.IndexExpr(self._opt_expr(expr.array),
                                  self._opt_expr(expr.index),
                                  expr.line, expr.col)
        if isinstance(expr, ast.CallExpr):
            return ast.CallExpr(expr.callee,
                                 tuple(self._opt_expr(a) for a in expr.args),
                                 expr.line, expr.col)
        if isinstance(expr, ast.Assign):
            return ast.Assign(expr.name, self._opt_expr(expr.value),
                               expr.line, expr.col)
        if isinstance(expr, ast.IndexAssign):
            return ast.IndexAssign(self._opt_expr(expr.array),
                                     self._opt_expr(expr.index),
                                     self._opt_expr(expr.value),
                                     expr.line, expr.col)
        return expr

    @staticmethod
    def _try_fold(op: str, left: Expr, right: Expr) -> Expr | None:
        # Only fold if both sides are literals.
        if isinstance(left, IntLit) and isinstance(right, IntLit):
            a, b = left.value, right.value
            if op == "+": return IntLit(a + b, left.line, left.col)
            if op == "-": return IntLit(a - b, left.line, left.col)
            if op == "*": return IntLit(a * b, left.line, left.col)
            if op == "/" and b != 0: return IntLit(a // b, left.line, left.col)
            if op == "%" and b != 0: return IntLit(a % b, left.line, left.col)
            if op == "<": return BoolLit(a < b, left.line, left.col)
            if op == "<=": return BoolLit(a <= b, left.line, left.col)
            if op == ">": return BoolLit(a > b, left.line, left.col)
            if op == ">=": return BoolLit(a >= b, left.line, left.col)
            if op == "==": return BoolLit(a == b, left.line, left.col)
            if op == "!=": return BoolLit(a != b, left.line, left.col)
        if isinstance(left, BoolLit) and isinstance(right, BoolLit):
            a, b = left.value, right.value
            if op == "&&": return BoolLit(a and b, left.line, left.col)
            if op == "||": return BoolLit(a or b, left.line, left.col)
            if op == "==": return BoolLit(a == b, left.line, left.col)
            if op == "!=": return BoolLit(a != b, left.line, left.col)
        if isinstance(left, StringLit) and isinstance(right, StringLit):
            a, b = left.value, right.value
            if op == "+": return StringLit(a + b, left.line, left.col)
            if op == "<": return BoolLit(a < b, left.line, left.col)
            if op == "<=": return BoolLit(a <= b, left.line, left.col)
            if op == ">": return BoolLit(a > b, left.line, left.col)
            if op == ">=": return BoolLit(a >= b, left.line, left.col)
            if op == "==": return BoolLit(a == b, left.line, left.col)
            if op == "!=": return BoolLit(a != b, left.line, left.col)
        return None


class DeadCodeEliminator:
    """Remove statements after an unconditional control-flow transfer."""

    def optimize(self, program: Program) -> Program:
        new_stmts = tuple(self._opt_stmt(s) for s in program.stmts)
        return Program(new_stmts)

    def _opt_stmt(self, stmt: Stmt) -> Stmt:
        if isinstance(stmt, Block):
            return Block(self._opt_block_stmts(stmt.stmts), stmt.line, stmt.col)
        if isinstance(stmt, IfStmt):
            then_b = Block(self._opt_block_stmts(stmt.then_branch.stmts),
                           stmt.then_branch.line, stmt.then_branch.col)
            else_b = None
            if stmt.else_branch is not None:
                else_b = Block(self._opt_block_stmts(stmt.else_branch.stmts),
                               stmt.else_branch.line, stmt.else_branch.col)
            return IfStmt(stmt.cond, then_b, else_b, stmt.line, stmt.col)
        if isinstance(stmt, WhileStmt):
            body = Block(self._opt_block_stmts(stmt.body.stmts),
                         stmt.body.line, stmt.body.col)
            return WhileStmt(stmt.cond, body, stmt.line, stmt.col)
        if isinstance(stmt, ast.ForStmt):
            body = Block(self._opt_block_stmts(stmt.body.stmts),
                         stmt.body.line, stmt.body.col)
            return ast.ForStmt(stmt.var, stmt.start, stmt.end, body,
                                stmt.line, stmt.col)
        if isinstance(stmt, ast.FuncDecl):
            body = Block(self._opt_block_stmts(stmt.body.stmts),
                         stmt.body.line, stmt.body.col)
            return ast.FuncDecl(stmt.name, stmt.params, stmt.ret_type, body,
                                stmt.line, stmt.col)
        return stmt

    @staticmethod
    def _opt_block_stmts(stmts: tuple[Stmt, ...]) -> tuple[Stmt, ...]:
        result: list[Stmt] = []
        for s in stmts:
            result.append(s)
            if isinstance(s, (ReturnStmt, BreakStmt, ContinueStmt)):
                break  # dead code after this point
        return tuple(result)


# --------------------------------------------------------------------------- #
# Bytecode-level passes                                                        #
# --------------------------------------------------------------------------- #
def jump_threading(program: CompiledProgram) -> CompiledProgram:
    """Collapse ``JUMP → JUMP`` chains so dispatch never chases more than one."""
    for chunk in program.all_chunks():
        code = chunk.code
        changed = True
        while changed:
            changed = False
            for i, ins in enumerate(code):
                if ins.op in (OpCode.JUMP, OpCode.JUMP_IF_FALSE, OpCode.JUMP_IF_TRUE):
                    target = ins.operand
                    while (0 <= target < len(code)
                           and code[target].op == OpCode.JUMP
                           and code[target].operand != target):
                        new_target = code[target].operand
                        if new_target == i:  # would create a self-loop
                            break
                        ins.operand = new_target
                        target = new_target
                        changed = True
    return program


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #
def optimize(program: Program) -> Program:
    """Run all AST-level optimization passes."""
    folder = ConstantFolder()
    dce = DeadCodeEliminator()
    # Run folding + DCE to a fixed point (cheap to check: no change → stop).
    prev = program
    for _ in range(3):
        p = dce.optimize(folder.optimize(prev))
        if p == prev:
            break
        prev = p
    return prev