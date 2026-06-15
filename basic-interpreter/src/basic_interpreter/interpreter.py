"""BASIC Interpreter — core execution engine.

This module implements the tree-walking interpreter that executes parsed
BASIC programs. It manages program state (variables, arrays, control flow
stacks), evaluates expressions, and dispatches statement execution.
"""

from __future__ import annotations

import datetime
import math
import os
import random
import sys
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from basic_interpreter.lexer import Lexer
from basic_interpreter.parser import Parser
from basic_interpreter.ast_nodes import (
    NumberLit, StringLit, VarRef, ArrayRef, FnCall, UnaryOp, BinOp,
    LetStmt, PrintStmt, InputStmt, LineInputStmt, IfStmt, ForStmt,
    NextStmt, WhileStmt, WendStmt, DoStmt, LoopStmt, GotoStmt,
    GosubStmt, ReturnStmt, DimStmt, EraseStmt, ReadStmt, DataStmt,
    RestoreStmt, DefFnStmt, EndStmt, StopStmt, RemStmt, OnGotoStmt,
    OnGosubStmt, SwapStmt, ClsStmt, ColorStmt, LocateStmt, BeepStmt,
    SelectCaseStmt, CaseStmt, CaseElseStmt, EndSelectStmt,
    CaseCondition, OpenStmt, CloseStmt, PrintFileStmt, InputFileStmt,
    OnErrorStmt, ResumeStmt, ExitDoStmt,
)
from basic_interpreter.errors import BasicSyntaxError, BasicRuntimeError, BasicStopException
from basic_interpreter.config import InterpreterConfig

logger = logging.getLogger(__name__)


class Interpreter:
    """Execute BASIC programs.

    The interpreter manages the full lifecycle of a BASIC program:
    loading, parsing, resolving cross-references, and executing line-by-line.

    Args:
        stdin: Input stream for INPUT statements (defaults to sys.stdin).
        stdout: Output stream for PRINT statements (defaults to sys.stdout).
        config: Optional InterpreterConfig for customizing behavior.
    """

    def __init__(self, stdin=None, stdout=None, config: Optional[InterpreterConfig] = None) -> None:
        self.config = config or InterpreterConfig()
        self.lines: Dict[int, list] = {}
        self.sorted_lines: List[int] = []
        self._line_to_idx: Dict[int, int] = {}
        self.variables: Dict[str, Any] = {}
        self.arrays: Dict[str, Any] = {}
        self.data_values: List[Any] = []
        self.data_pointer: int = 0
        self.call_stack: List[int] = []
        self.for_stack: List[dict] = []
        self.while_stack: List[Tuple[int, int, int, int]] = []
        self.do_loop_pairs: List[Tuple[int, int]] = []
        self.select_info: Dict[int, dict] = {}
        self.user_fns: Dict[str, DefFnStmt] = {}
        self.pc: int = 0
        self.running: bool = False
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.trace: bool = False
        self.max_iterations: int = self.config.max_iterations
        self._iteration_count: int = 0
        self._print_col: int = 0
        self._files: Dict[int, Any] = {}
        self._on_error_line: Optional[int] = None
        self._error_occurred: bool = False
        self._error_resume_line: Optional[int] = None
        self._active_select_end: Optional[int] = None
        self._active_select_matched: Optional[int] = None

    def __del__(self) -> None:
        """Clean up open file handles on interpreter destruction."""
        for f in self._files.values():
            try:
                f.close()
            except OSError:
                pass

    # ── Program loading ──

    def load(self, source: str) -> None:
        """Load a BASIC program from source code.

        Tokenizes, parses, and prepares the program for execution.
        Also resolves cross-references for WHILE/WEND, DO/LOOP, and SELECT CASE.

        Args:
            source: The complete BASIC source code as a string.

        Raises:
            BasicSyntaxError: If the source contains syntax errors.
        """
        # Close any previously open files before loading new program
        for f in self._files.values():
            try:
                f.close()
            except OSError:
                pass
        self._files.clear()

        self.lines.clear()
        self.data_values.clear()
        self.data_pointer = 0
        self.variables.clear()
        self.arrays.clear()
        self.call_stack.clear()
        self.for_stack.clear()
        self.while_stack.clear()
        self.do_loop_pairs.clear()
        self.select_info.clear()
        self.user_fns.clear()
        self._on_error_line = None
        self._error_occurred = False
        self._active_select_end = None
        self._active_select_matched = None

        immediate_stmts: list = []
        for raw_line in source.splitlines():
            raw_line = raw_line.rstrip()
            if not raw_line.strip():
                continue
            try:
                from basic_interpreter.lexer import TokenType as TT
                lex = Lexer(raw_line)
                toks = lex.tokenize()
                par = Parser(toks)
                linenum_tok = par._match(TT.LINENUM)
                if linenum_tok:
                    line_num = linenum_tok.value
                    if par._peek().type == TT.EOF:
                        self.lines.pop(line_num, None)
                        continue
                    stmts = par._parse_stmts()
                    self.lines[line_num] = stmts
                else:
                    if par._peek().type != TT.EOF:
                        stmts = par._parse_stmts()
                        immediate_stmts.extend(stmts)
            except BasicSyntaxError:
                raise

        self._rebuild()
        self._collect_data()
        self._resolve_while_wend()
        self._resolve_do_loop()
        self._resolve_select_case()

        if immediate_stmts:
            self.running = True
            self._exec_stmts(immediate_stmts)

    def _rebuild(self) -> None:
        """Rebuild sorted line numbers and lookup table."""
        self.sorted_lines = sorted(self.lines.keys())
        self._line_to_idx = {ln: i for i, ln in enumerate(self.sorted_lines)}

    def _collect_data(self) -> None:
        """Collect all DATA values in line-number order."""
        self.data_values = []
        self.data_pointer = 0
        for ln in self.sorted_lines:
            for stmt in self.lines[ln]:
                if isinstance(stmt, DataStmt):
                    self.data_values.extend(stmt.values)

    def _resolve_while_wend(self) -> None:
        """Match WHILE and WEND statements across lines."""
        self.while_stack = []
        stack: list = []
        for i, ln in enumerate(self.sorted_lines):
            stmts = self.lines[ln]
            for j, stmt in enumerate(stmts):
                if isinstance(stmt, WhileStmt):
                    stack.append((i, j))
                elif isinstance(stmt, WendStmt):
                    if not stack:
                        raise BasicSyntaxError("WEND without matching WHILE")
                    wi, wj = stack.pop()
                    self.while_stack.append((wi, wj, i, j))

    def _find_wend(self, while_line_idx: int) -> Optional[Tuple[int, int]]:
        """Find the WEND index for a given WHILE line index."""
        for wi, wj, wendi, wendj in self.while_stack:
            if wi == while_line_idx:
                return (wendi, wendj)
        return None

    def _find_while(self, wend_line_idx: int) -> Optional[Tuple[int, int]]:
        """Find the WHILE index for a given WEND line index."""
        for wi, wj, wendi, wendj in self.while_stack:
            if wendi == wend_line_idx:
                return (wi, wj)
        return None

    def _resolve_do_loop(self) -> None:
        """Match DO and LOOP statements across lines."""
        self.do_loop_pairs = []
        stack: list = []
        for i, ln in enumerate(self.sorted_lines):
            stmts = self.lines[ln]
            for j, stmt in enumerate(stmts):
                if isinstance(stmt, DoStmt):
                    stack.append(i)
                elif isinstance(stmt, LoopStmt):
                    if not stack:
                        raise BasicSyntaxError("LOOP without matching DO")
                    do_idx = stack.pop()
                    self.do_loop_pairs.append((do_idx, i))
        if stack:
            raise BasicSyntaxError("DO without matching LOOP")

    def _find_loop_for_do(self, do_line_idx: int) -> Optional[int]:
        """Find the LOOP index for a given DO line index."""
        for do_idx, loop_idx in self.do_loop_pairs:
            if do_idx == do_line_idx:
                return loop_idx
        return None

    def _find_do_for_loop(self, loop_line_idx: int) -> Optional[int]:
        """Find the DO index for a given LOOP line index."""
        for do_idx, loop_idx in self.do_loop_pairs:
            if loop_idx == loop_line_idx:
                return do_idx
        return None

    def _resolve_select_case(self) -> None:
        """Match SELECT CASE, CASE, CASE ELSE, END SELECT across lines."""
        self.select_info = {}
        select_stack: list = []
        for i, ln in enumerate(self.sorted_lines):
            stmts = self.lines[ln]
            for j, stmt in enumerate(stmts):
                if isinstance(stmt, SelectCaseStmt):
                    select_stack.append({"select_idx": i, "case_indices": [], "case_else_idx": None})
                elif isinstance(stmt, CaseStmt):
                    if select_stack:
                        select_stack[-1]["case_indices"].append(i)
                elif isinstance(stmt, CaseElseStmt):
                    if select_stack:
                        select_stack[-1]["case_else_idx"] = i
                elif isinstance(stmt, EndSelectStmt):
                    if select_stack:
                        info = select_stack.pop()
                        info["end_select_idx"] = i
                        self.select_info[info["select_idx"]] = info
        if select_stack:
            raise BasicSyntaxError("SELECT CASE without END SELECT")

    # ── Execution ──

    def run(self) -> None:
        """Execute the loaded program from the beginning.

        Runs until END, STOP, or the program counter goes out of range.
        Respects the max_iterations limit to prevent infinite loops.
        """
        if not self.sorted_lines:
            return
        self.running = True
        self.pc = 0
        self._iteration_count = 0

        while self.running and 0 <= self.pc < len(self.sorted_lines):
            self._iteration_count += 1
            if self._iteration_count > self.max_iterations:
                raise BasicRuntimeError("Maximum iteration count exceeded")

            current_pc = self.pc
            line_num = self.sorted_lines[self.pc]

            if self.trace:
                self.stdout.write(f"[{line_num}] ")

            stmts = self.lines[line_num]
            try:
                self._exec_stmts(stmts)
            except BasicRuntimeError as e:
                if self._on_error_line is not None and self._on_error_line != 0:
                    self._error_occurred = True
                    self._error_resume_line = current_pc
                    if self._on_error_line in self._line_to_idx:
                        idx = self._line_to_idx[self._on_error_line]
                        self.pc = idx - 1
                    else:
                        raise
                else:
                    raise

            if not self.running:
                break

            if self.pc != current_pc:
                self.pc += 1
            else:
                self.pc += 1

    def _exec_stmts(self, stmts: list) -> None:
        """Execute a list of statements sequentially."""
        for stmt in stmts:
            if not self.running:
                return
            self._exec_stmt(stmt)

    def _exec_stmt(self, stmt: Any) -> None:
        """Dispatch and execute a single statement."""
        if isinstance(stmt, (NumberLit, StringLit, BinOp, UnaryOp)):
            self._eval(stmt)
            return

        dispatch = {
            LetStmt: self._exec_let,
            PrintStmt: self._exec_print,
            InputStmt: self._exec_input,
            LineInputStmt: self._exec_line_input,
            IfStmt: self._exec_if,
            ForStmt: self._exec_for,
            NextStmt: self._exec_next,
            WhileStmt: self._exec_while,
            WendStmt: self._exec_wend,
            DoStmt: self._exec_do,
            LoopStmt: self._exec_loop,
            GotoStmt: self._exec_goto,
            GosubStmt: self._exec_gosub,
            ReturnStmt: self._exec_return,
            DimStmt: self._exec_dim,
            EraseStmt: self._exec_erase,
            ReadStmt: self._exec_read,
            DataStmt: lambda s: None,
            RestoreStmt: self._exec_restore,
            DefFnStmt: self._exec_def_fn,
            EndStmt: lambda s: setattr(self, 'running', False),
            StopStmt: None,  # handled specially below
            RemStmt: lambda s: None,
            OnGotoStmt: self._exec_on_goto,
            OnGosubStmt: self._exec_on_gosub,
            SwapStmt: self._exec_swap,
            ClsStmt: self._exec_cls,
            ColorStmt: self._exec_color,
            LocateStmt: self._exec_locate,
            BeepStmt: self._exec_beep,
            SelectCaseStmt: self._exec_select_case,
            OnErrorStmt: self._exec_on_error,
            ResumeStmt: self._exec_resume,
            OpenStmt: self._exec_open,
            CloseStmt: self._exec_close,
            PrintFileStmt: self._exec_print_file,
            InputFileStmt: self._exec_input_file,
            FnCall: lambda s: self._eval(s),
            ExitDoStmt: self._exec_exit_do,
        }

        stmt_type = type(stmt)
        if stmt_type in dispatch:
            handler = dispatch[stmt_type]
            if stmt_type == StopStmt:
                raise BasicStopException("STOP encountered")
            handler(stmt)
        elif isinstance(stmt, CaseStmt):
            self._exec_case(stmt)
        elif isinstance(stmt, CaseElseStmt):
            self._exec_case_else(stmt)
        elif isinstance(stmt, EndSelectStmt):
            self._active_select_end = None
            self._active_select_matched = None
        else:
            raise BasicRuntimeError(f"Unknown statement: {stmt_type.__name__}")

    def _exec_let(self, stmt: LetStmt) -> None:
        """Execute a LET (assignment) statement."""
        value = self._eval(stmt.value)
        if isinstance(stmt.target, VarRef):
            self.variables[stmt.target.name] = value
        elif isinstance(stmt.target, ArrayRef):
            self._set_array_ref(stmt.target, value)
        else:
            raise BasicRuntimeError(f"Invalid LET target: {stmt.target}")

    def _set_array_ref(self, ref: ArrayRef, value: Any) -> None:
        """Set a value in an array, auto-expanding if necessary."""
        name = ref.name
        indices = [int(self._eval(idx)) for idx in ref.indices]
        if name not in self.arrays:
            dim_count = len(indices)
            if dim_count == 1:
                self.arrays[name] = [0.0] * (max(indices[0], 10) + 1)
            elif dim_count == 2:
                self.arrays[name] = [[0.0] * (max(indices[1], 10) + 1) for _ in range(max(indices[0], 10) + 1)]
        arr = self.arrays[name]
        if len(indices) == 1:
            if indices[0] < 0:
                raise BasicRuntimeError("Negative array index")
            if indices[0] >= len(arr):
                arr.extend([0.0] * (indices[0] - len(arr) + 1))
            arr[indices[0]] = value
        elif len(indices) == 2:
            if indices[0] < 0 or indices[1] < 0:
                raise BasicRuntimeError("Negative array index")
            if indices[0] >= len(arr):
                while len(arr) <= indices[0]:
                    arr.append([0.0] * (len(arr[0]) if arr and isinstance(arr[0], list) and len(arr[0]) > 0 else 11))
            if indices[1] >= len(arr[indices[0]]):
                arr[indices[0]].extend([0.0] * (indices[1] - len(arr[indices[0]]) + 1))
            arr[indices[0]][indices[1]] = value

    def _exec_print(self, stmt: PrintStmt) -> None:
        """Execute a PRINT statement."""
        if stmt.using:
            self._exec_print_using(stmt)
            return
        end_newline = True
        zone_width = 14
        for expr, sep in stmt.items:
            if expr is not None:
                val = self._eval(expr)
                text = self._format_value(val)
                self.stdout.write(text)
                self._print_col += len(text)
            if sep == ";":
                end_newline = False
            elif sep == ",":
                spaces = zone_width - (self._print_col % zone_width)
                self.stdout.write(" " * spaces)
                self._print_col += spaces
                end_newline = False
            else:
                end_newline = True
        if end_newline:
            self.stdout.write("\n")
            self._print_col = 0
        self.stdout.flush()

    def _format_value(self, val) -> str:
        """Format a value for PRINT output, following BASIC conventions."""
        if isinstance(val, (int, float)):
            if isinstance(val, float) and val == int(val) and abs(val) < 1e15:
                return " " + str(int(val)) + " "
            if isinstance(val, int):
                return " " + str(val) + " "
            return " " + str(val) + " "
        return str(val)

    def _exec_print_using(self, stmt: PrintStmt) -> None:
        """Execute a PRINT USING statement with format template."""
        fmt = str(self._eval(stmt.using))
        items = [(self._eval(expr), sep) for expr, sep in stmt.items if expr is not None]
        result = self._apply_print_using(fmt, items)
        self.stdout.write(result)
        if not stmt.items or stmt.items[-1][1] is None:
            self.stdout.write("\n")
        self.stdout.flush()

    def _apply_print_using(self, fmt: str, items: list) -> str:
        """Apply a PRINT USING format template to a list of values."""
        result: list[str] = []
        fi = 0
        ii = 0
        while fi < len(fmt):
            ch = fmt[fi]
            if ch == "#":
                width = 0
                decimal = 0
                has_decimal = False
                while fi < len(fmt) and fmt[fi] in ("#", ".", ","):
                    if fmt[fi] == "#":
                        width += 1
                        if has_decimal:
                            decimal += 1
                    elif fmt[fi] == ".":
                        has_decimal = True
                    fi += 1
                if ii < len(items):
                    val = self._to_number(items[ii][0])
                    ii += 1
                    if has_decimal:
                        s = f"{val:{width + 1}.{decimal}f}"
                    else:
                        s = f"{int(val):>{width}d}"
                    result.append(s)
                continue
            elif ch == "&":
                fi += 1
                if ii < len(items):
                    val = str(items[ii][0])
                    ii += 1
                    result.append(val)
                continue
            elif ch == "\\" and fi + 1 < len(fmt) and fmt[fi + 1] == " ":
                fi += 1
                width = 2
                while fi < len(fmt) and fmt[fi] == " ":
                    width += 1
                    fi += 1
                if fi < len(fmt) and fmt[fi] == "\\":
                    width += 1
                    fi += 1
                if ii < len(items):
                    val = str(items[ii][0])
                    ii += 1
                    result.append(val[:width].ljust(width))
                continue
            elif ch == "!":
                fi += 1
                if ii < len(items):
                    val = str(items[ii][0])
                    ii += 1
                    result.append(val[0] if val else " ")
                continue
            else:
                result.append(ch)
                fi += 1
        return "".join(result)

    def _exec_input(self, stmt: InputStmt) -> None:
        """Execute an INPUT statement."""
        prompt = "? "
        if stmt.prompt:
            p = self._eval(stmt.prompt)
            prompt = str(p)
            if not prompt.endswith(" "):
                prompt += " "
        self.stdout.write(prompt)
        self.stdout.flush()
        try:
            line = self.stdin.readline()
            if not line:
                raise BasicRuntimeError("End of input")
            line = line.rstrip("\n\r")
        except EOFError:
            raise BasicRuntimeError("End of input")

        values = [v.strip() for v in line.split(",")]
        for i, var in enumerate(stmt.vars):
            raw = values[i] if i < len(values) else ""
            if isinstance(var, VarRef):
                self._assign_input_var(var.name, raw)

    def _exec_line_input(self, stmt: LineInputStmt) -> None:
        """Execute a LINE INPUT statement."""
        if stmt.file_num is not None:
            fnum = int(self._to_number(self._eval(stmt.file_num)))
            if fnum not in self._files:
                raise BasicRuntimeError(f"File #{fnum} not open")
            line = self._files[fnum].readline()
            if not line:
                raise BasicRuntimeError(f"End of file #{fnum}")
            line = line.rstrip("\n\r")
            if isinstance(stmt.var, VarRef):
                self.variables[stmt.var.name] = line
            return

        prompt = ""
        if stmt.prompt:
            p = self._eval(stmt.prompt)
            prompt = str(p)
            if not prompt.endswith(" "):
                prompt += " "
        self.stdout.write(prompt)
        self.stdout.flush()
        try:
            line = self.stdin.readline()
            if not line:
                raise BasicRuntimeError("End of input")
            line = line.rstrip("\n\r")
        except EOFError:
            raise BasicRuntimeError("End of input")

        if isinstance(stmt.var, VarRef):
            self.variables[stmt.var.name] = line

    def _assign_input_var(self, name: str, raw: str) -> None:
        """Assign a raw input string to a variable, converting types as needed."""
        if name.endswith("$"):
            self.variables[name] = raw
        else:
            try:
                self.variables[name] = float(raw) if "." in raw else float(int(raw))
            except ValueError:
                try:
                    self.variables[name] = float(raw)
                except ValueError:
                    self.variables[name] = 0.0

    def _exec_if(self, stmt: IfStmt) -> None:
        """Execute an IF...THEN...ELSE statement."""
        cond = self._eval(stmt.condition)
        if self._truthy(cond):
            self._exec_stmts(stmt.then_part)
        else:
            if stmt.else_part:
                self._exec_stmts(stmt.else_part)

    def _truthy(self, val) -> bool:
        """Determine if a value is truthy in BASIC (non-zero number, non-empty string)."""
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return len(val) > 0
        return bool(val)

    def _exec_for(self, stmt: ForStmt) -> None:
        """Execute a FOR statement."""
        start = self._to_number(self._eval(stmt.start))
        stop = self._to_number(self._eval(stmt.stop))
        step = self._to_number(self._eval(stmt.step)) if stmt.step else 1.0
        if step == 0:
            raise BasicRuntimeError("FOR step cannot be zero")

        var_name = stmt.var.name
        self.variables[var_name] = start

        for entry in self.for_stack:
            if entry["var"] == var_name:
                self.for_stack.remove(entry)
                break

        self.for_stack.append({
            "var": var_name,
            "stop": stop,
            "step": step,
            "pc": self.pc,
        })

    def _exec_next(self, stmt: NextStmt) -> None:
        """Execute a NEXT statement."""
        if stmt.var:
            var_name = stmt.var.name
            for_idx = None
            for i in range(len(self.for_stack) - 1, -1, -1):
                if self.for_stack[i]["var"] == var_name:
                    for_idx = i
                    break
            if for_idx is None:
                raise BasicRuntimeError(f"NEXT without FOR: {var_name}")
        else:
            if not self.for_stack:
                raise BasicRuntimeError("NEXT without FOR")
            for_idx = len(self.for_stack) - 1

        entry = self.for_stack[for_idx]
        var_name = entry["var"]

        current = self._to_number(self.variables.get(var_name, 0))
        step = entry["step"]
        stop = entry["stop"]

        current += step
        self.variables[var_name] = current

        done = (step > 0 and current > stop) or (step < 0 and current < stop)
        if done:
            self.for_stack.pop(for_idx)
        else:
            self.pc = entry["pc"]

    def _exec_while(self, stmt: WhileStmt) -> None:
        """Execute a WHILE statement."""
        cond = self._truthy(self._eval(stmt.condition))
        if not cond:
            wend_info = self._find_wend(self.pc)
            if wend_info:
                self.pc = wend_info[0]
            else:
                raise BasicRuntimeError("WHILE without matching WEND")

    def _exec_wend(self, stmt: WendStmt) -> None:
        """Execute a WEND statement."""
        while_info = self._find_while(self.pc)
        if while_info:
            self.pc = while_info[0]
            self.pc -= 1
        else:
            raise BasicRuntimeError("WEND without matching WHILE")

    def _exec_do(self, stmt: DoStmt) -> None:
        """Execute a DO [WHILE|UNTIL] statement."""
        if stmt.pre_condition is not None:
            cond = self._truthy(self._eval(stmt.pre_condition))
            if stmt.pre_until:
                cond = not cond
            if not cond:
                loop_idx = self._find_loop_for_do(self.pc)
                if loop_idx is not None:
                    self.pc = loop_idx
                else:
                    raise BasicRuntimeError("DO without matching LOOP")

    def _exec_loop(self, stmt: LoopStmt) -> None:
        """Execute a LOOP [WHILE|UNTIL] statement."""
        do_idx = self._find_do_for_loop(self.pc)
        if do_idx is None:
            raise BasicRuntimeError("LOOP without matching DO")

        if stmt.post_condition is not None:
            cond_val = self._truthy(self._eval(stmt.post_condition))
            if stmt.post_until:
                if cond_val:
                    return
                else:
                    self.pc = do_idx - 1
            else:
                if cond_val:
                    self.pc = do_idx - 1
                else:
                    return
        else:
            do_line = self.sorted_lines[do_idx]
            for s in self.lines[do_line]:
                if isinstance(s, DoStmt):
                    if s.pre_condition is not None:
                        self.pc = do_idx - 1
                        return
            raise BasicRuntimeError("DO...LOOP without condition: infinite loop")

    def _exec_exit_do(self, stmt: ExitDoStmt) -> None:
        """Execute an EXIT DO statement."""
        loop_idx = self._find_loop_for_do(self.pc)
        if loop_idx is not None:
            self.pc = loop_idx
        else:
            raise BasicRuntimeError("EXIT DO without DO loop")

    def _exec_goto(self, stmt: GotoStmt) -> None:
        """Execute a GOTO statement."""
        if stmt.line not in self._line_to_idx:
            raise BasicRuntimeError(f"GOTO: line {stmt.line} not found")
        idx = self._line_to_idx[stmt.line]
        self.pc = idx - 1

    def _exec_gosub(self, stmt: GosubStmt) -> None:
        """Execute a GOSUB statement."""
        if stmt.line not in self._line_to_idx:
            raise BasicRuntimeError(f"GOSUB: line {stmt.line} not found")
        self.call_stack.append(self.pc)
        idx = self._line_to_idx[stmt.line]
        self.pc = idx - 1

    def _exec_return(self, stmt: ReturnStmt) -> None:
        """Execute a RETURN statement."""
        if not self.call_stack:
            raise BasicRuntimeError("RETURN without GOSUB")
        self.pc = self.call_stack.pop()

    def _exec_dim(self, stmt: DimStmt) -> None:
        """Execute a DIM statement."""
        for name, dims in stmt.declarations:
            if name in self.arrays:
                raise BasicRuntimeError(f"Array {name} already dimensioned")
            if len(dims) == 1:
                self.arrays[name] = [0.0] * (dims[0] + 1)
            elif len(dims) == 2:
                self.arrays[name] = [[0.0] * (dims[1] + 1) for _ in range(dims[0] + 1)]
            else:
                raise BasicRuntimeError("DIM supports 1D and 2D arrays only")

    def _exec_erase(self, stmt: EraseStmt) -> None:
        """Execute an ERASE statement."""
        for name in stmt.names:
            self.arrays.pop(name, None)

    def _exec_read(self, stmt: ReadStmt) -> None:
        """Execute a READ statement."""
        for var in stmt.vars:
            if self.data_pointer >= len(self.data_values):
                raise BasicRuntimeError("Out of DATA")
            raw = self.data_values[self.data_pointer]
            self.data_pointer += 1
            if isinstance(var, VarRef):
                name = var.name
                if name.endswith("$"):
                    self.variables[name] = str(raw)
                else:
                    try:
                        self.variables[name] = float(raw) if isinstance(raw, str) and "." in raw else (float(raw) if isinstance(raw, str) else raw)
                    except (ValueError, TypeError):
                        self.variables[name] = 0.0
            elif isinstance(var, ArrayRef):
                indices = [int(self._eval(idx)) for idx in var.indices]
                self._set_array(var.name, indices, raw)

    def _exec_restore(self, stmt: RestoreStmt) -> None:
        """Execute a RESTORE statement."""
        if stmt.line_num is not None:
            target = stmt.line_num
            ptr = 0
            for ln in self.sorted_lines:
                for s in self.lines[ln]:
                    if isinstance(s, DataStmt):
                        if ln == target:
                            self.data_pointer = ptr
                            return
                        ptr += len(s.values)
            raise BasicRuntimeError(f"RESTORE: line {target} not found or has no DATA")
        else:
            self.data_pointer = 0

    def _exec_def_fn(self, stmt: DefFnStmt) -> None:
        """Execute a DEF FN statement."""
        fn_name = "FN" + stmt.name
        self.user_fns[fn_name] = stmt

    def _exec_on_goto(self, stmt: OnGotoStmt) -> None:
        """Execute an ON...GOTO statement."""
        val = int(self._to_number(self._eval(stmt.expr)))
        if 1 <= val <= len(stmt.targets):
            target = stmt.targets[val - 1]
            if target not in self._line_to_idx:
                raise BasicRuntimeError(f"ON GOTO: line {target} not found")
            idx = self._line_to_idx[target]
            self.pc = idx - 1

    def _exec_on_gosub(self, stmt: OnGosubStmt) -> None:
        """Execute an ON...GOSUB statement."""
        val = int(self._to_number(self._eval(stmt.expr)))
        if 1 <= val <= len(stmt.targets):
            target = stmt.targets[val - 1]
            if target not in self._line_to_idx:
                raise BasicRuntimeError(f"ON GOSUB: line {target} not found")
            self.call_stack.append(self.pc)
            idx = self._line_to_idx[target]
            self.pc = idx - 1

    def _exec_swap(self, stmt: SwapStmt) -> None:
        """Execute a SWAP statement."""
        v1_name = self._get_lvalue_name(stmt.var1)
        v2_name = self._get_lvalue_name(stmt.var2)
        v1 = self.variables.get(v1_name, 0.0 if not v1_name.endswith("$") else "")
        v2 = self.variables.get(v2_name, 0.0 if not v2_name.endswith("$") else "")
        self.variables[v1_name] = v2
        self.variables[v2_name] = v1

    def _get_lvalue_name(self, lv) -> str:
        """Get the variable name from an lvalue node."""
        if isinstance(lv, VarRef):
            return lv.name
        raise BasicRuntimeError("SWAP only supports simple variables")

    def _exec_cls(self, stmt: ClsStmt) -> None:
        """Execute a CLS (clear screen) statement."""
        self.stdout.write("\033[2J\033[H")
        self.stdout.flush()
        self._print_col = 0

    def _exec_color(self, stmt: ColorStmt) -> None:
        """Execute a COLOR statement."""
        fg = int(self._to_number(self._eval(stmt.fg))) if stmt.fg else 7
        ansi_fg = 30 + fg if fg < 8 else (90 + fg - 8) if fg < 16 else 37
        code = f"\033[{ansi_fg}m"
        if stmt.bg is not None:
            bg = int(self._to_number(self._eval(stmt.bg)))
            ansi_bg = 40 + bg if bg < 8 else (100 + bg - 8) if bg < 16 else 40
            code += f"\033[{ansi_bg}m"
        self.stdout.write(code)
        self.stdout.flush()

    def _exec_locate(self, stmt: LocateStmt) -> None:
        """Execute a LOCATE statement."""
        row = int(self._to_number(self._eval(stmt.row))) if stmt.row else 1
        col = int(self._to_number(self._eval(stmt.col))) if stmt.col else 1
        self.stdout.write(f"\033[{row};{col}H")
        self.stdout.flush()
        self._print_col = col - 1

    def _exec_beep(self, stmt: BeepStmt) -> None:
        """Execute a BEEP statement."""
        self.stdout.write("\a")
        self.stdout.flush()

    def _exec_select_case(self, stmt: SelectCaseStmt) -> None:
        """Execute a SELECT CASE statement."""
        test_val = self._eval(stmt.test_expr)
        info = self.select_info.get(self.pc)
        if info is None:
            return

        case_indices = info["case_indices"]
        case_else_idx = info.get("case_else_idx")
        end_select_idx = info.get("end_select_idx", len(self.sorted_lines) - 1)

        matched_case_idx = None
        for case_idx in case_indices:
            case_stmts = self.lines[self.sorted_lines[case_idx]]
            for s in case_stmts:
                if isinstance(s, CaseStmt):
                    if self._match_case(test_val, s.conditions):
                        matched_case_idx = case_idx
                        break
            if matched_case_idx is not None:
                break

        self._active_select_end = end_select_idx

        if matched_case_idx is not None:
            self._active_select_matched = matched_case_idx
            self.pc = matched_case_idx - 1
        elif case_else_idx is not None:
            self._active_select_matched = case_else_idx
            self.pc = case_else_idx - 1
        else:
            self.pc = end_select_idx
            self._active_select_end = None
            self._active_select_matched = None

    def _exec_case(self, stmt: CaseStmt) -> None:
        """Handle a CASE statement during execution (skip to END SELECT if not matched)."""
        if self._active_select_end is not None and self._active_select_matched is not None:
            if self.pc != self._active_select_matched:
                self.pc = self._active_select_end
                self._active_select_end = None
                self._active_select_matched = None

    def _exec_case_else(self, stmt: CaseElseStmt) -> None:
        """Handle a CASE ELSE statement during execution."""
        if self._active_select_end is not None and self._active_select_matched is not None:
            if self.pc != self._active_select_matched:
                self.pc = self._active_select_end
                self._active_select_end = None
                self._active_select_matched = None

    def _match_case(self, test_val, conditions: list) -> bool:
        """Test if a value matches any CASE condition."""
        for cond in conditions:
            if cond.is_op is not None:
                cmp_val = self._eval(cond.is_val)
                if self._compare(test_val, cond.is_op, cmp_val):
                    return True
            elif cond.high is not None:
                low = self._eval(cond.low)
                high = self._eval(cond.high)
                if isinstance(test_val, str):
                    if low <= test_val <= high:
                        return True
                else:
                    if self._to_number(low) <= self._to_number(test_val) <= self._to_number(high):
                        return True
            else:
                val = self._eval(cond.low)
                if isinstance(test_val, str) and isinstance(val, str):
                    if test_val == val:
                        return True
                elif not isinstance(test_val, str) and not isinstance(val, str):
                    if self._to_number(test_val) == self._to_number(val):
                        return True
                elif isinstance(val, str):
                    if str(test_val) == val:
                        return True
                else:
                    if self._to_number(test_val) == self._to_number(val):
                        return True
        return False

    def _compare(self, left, op: str, right) -> bool:
        """Compare two values with the given operator."""
        if isinstance(left, str) and isinstance(right, str):
            ops = {"=": lambda a, b: a == b, "<>": lambda a, b: a != b,
                   "<": lambda a, b: a < b, ">": lambda a, b: a > b,
                   "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}
            return ops.get(op, lambda a, b: False)(left, right)
        ln = self._to_number(left)
        rn = self._to_number(right)
        if op == "=": return ln == rn
        if op == "<>": return ln != rn
        if op == "<": return ln < rn
        if op == ">": return ln > rn
        if op == "<=": return ln <= rn
        if op == ">=": return ln >= rn
        return False

    def _exec_open(self, stmt: OpenStmt) -> None:
        """Execute an OPEN statement for file I/O."""
        filename = str(self._eval(stmt.filename))
        fnum = int(self._to_number(self._eval(stmt.file_num)))
        mode = stmt.mode.upper()
        try:
            if mode == "I":
                f = open(filename, "r")
            elif mode == "O":
                f = open(filename, "w")
            elif mode == "A":
                f = open(filename, "a")
            else:
                raise BasicRuntimeError(f"Invalid file mode: {mode}")
            self._files[fnum] = f
        except OSError as e:
            raise BasicRuntimeError(f"Cannot open file '{filename}': {e}")

    def _exec_close(self, stmt: CloseStmt) -> None:
        """Execute a CLOSE statement."""
        if stmt.file_num is not None:
            fnum = int(self._to_number(self._eval(stmt.file_num)))
            if fnum in self._files:
                self._files[fnum].close()
                del self._files[fnum]
        else:
            for f in self._files.values():
                f.close()
            self._files.clear()

    def _exec_print_file(self, stmt: PrintFileStmt) -> None:
        """Execute a PRINT# statement for file output."""
        fnum = int(self._to_number(self._eval(stmt.file_num)))
        if fnum not in self._files:
            raise BasicRuntimeError(f"File #{fnum} not open")
        f = self._files[fnum]
        end_newline = True
        for expr, sep in stmt.items:
            if expr is not None:
                val = self._eval(expr)
                f.write(self._format_value(val))
            if sep == ";":
                end_newline = False
            elif sep == ",":
                f.write("\t")
                end_newline = False
            else:
                end_newline = True
        if end_newline:
            f.write("\n")
        f.flush()

    def _exec_input_file(self, stmt: InputFileStmt) -> None:
        """Execute an INPUT# statement for file input."""
        fnum = int(self._to_number(self._eval(stmt.file_num)))
        if fnum not in self._files:
            raise BasicRuntimeError(f"File #{fnum} not open")
        f = self._files[fnum]
        line = f.readline()
        if not line:
            raise BasicRuntimeError(f"End of file #{fnum}")
        line = line.rstrip("\n\r")
        values = [v.strip() for v in line.split(",")]
        for i, var in enumerate(stmt.vars):
            raw = values[i] if i < len(values) else ""
            if isinstance(var, VarRef):
                self._assign_input_var(var.name, raw)

    def _exec_on_error(self, stmt: OnErrorStmt) -> None:
        """Execute an ON ERROR GOTO statement."""
        if stmt.line == 0:
            self._on_error_line = None
        else:
            self._on_error_line = stmt.line

    def _exec_resume(self, stmt: ResumeStmt) -> None:
        """Execute a RESUME statement."""
        if not self._error_occurred:
            raise BasicRuntimeError("RESUME without error")
        if stmt.line is not None and stmt.line > 0:
            if stmt.line not in self._line_to_idx:
                raise BasicRuntimeError(f"RESUME: line {stmt.line} not found")
            idx = self._line_to_idx[stmt.line]
            self.pc = idx - 1
        elif stmt.line == -1:
            if self._error_resume_line is not None:
                self.pc = self._error_resume_line
        else:
            if self._error_resume_line is not None:
                self.pc = self._error_resume_line - 1
        self._error_occurred = False

    def _set_array(self, name: str, indices: list, value: Any) -> None:
        """Set a value in an array, auto-expanding if necessary."""
        if name not in self.arrays:
            if len(indices) == 1:
                self.arrays[name] = [0.0] * (max(indices[0], 10) + 1)
            elif len(indices) == 2:
                self.arrays[name] = [[0.0] * (max(indices[1], 10) + 1) for _ in range(max(indices[0], 10) + 1)]
        arr = self.arrays[name]
        if len(indices) == 1:
            if indices[0] >= len(arr):
                arr.extend([0.0] * (indices[0] - len(arr) + 1))
            arr[indices[0]] = value
        elif len(indices) == 2:
            if indices[0] >= len(arr):
                while len(arr) <= indices[0]:
                    arr.append([0.0] * (len(arr[0]) if arr and isinstance(arr[0], list) and len(arr[0]) > 0 else 11))
            if indices[1] >= len(arr[indices[0]]):
                arr[indices[0]].extend([0.0] * (indices[1] - len(arr[indices[0]]) + 1))
            arr[indices[0]][indices[1]] = value

    # ── Expression evaluation ──

    def _eval(self, expr) -> Any:
        """Evaluate an expression node and return its value."""
        if isinstance(expr, NumberLit):
            return expr.value
        if isinstance(expr, StringLit):
            return expr.value
        if isinstance(expr, VarRef):
            name = expr.name
            system_vars = {"DATE$", "TIME$", "INKEY$", "TIMER"}
            if name in system_vars and name not in self.variables:
                return self._eval_fn(FnCall(name, []))
            if name in self.variables:
                return self.variables[name]
            if not name.endswith("$"):
                return 0.0
            return ""
        if isinstance(expr, ArrayRef):
            name = expr.name
            indices = [int(self._to_number(self._eval(idx))) for idx in expr.indices]
            if name not in self.arrays:
                if not name.endswith("$"):
                    return 0.0
                return ""
            arr = self.arrays[name]
            if len(indices) == 1:
                if 0 <= indices[0] < len(arr):
                    return arr[indices[0]]
                return 0.0 if not name.endswith("$") else ""
            elif len(indices) == 2:
                if 0 <= indices[0] < len(arr) and 0 <= indices[1] < len(arr[0]):
                    return arr[indices[0]][indices[1]]
                return 0.0 if not name.endswith("$") else ""
        if isinstance(expr, FnCall):
            return self._eval_fn(expr)
        if isinstance(expr, UnaryOp):
            val = self._eval(expr.operand)
            if expr.op == "-":
                return -self._to_number(val)
            if expr.op == "NOT":
                return -1 if not self._truthy(val) else 0
            raise BasicRuntimeError(f"Unknown unary op: {expr.op}")
        if isinstance(expr, BinOp):
            return self._eval_binop(expr)

        raise BasicRuntimeError(f"Cannot evaluate: {type(expr).__name__}")

    def _eval_fn(self, expr: FnCall) -> Any:
        """Evaluate a function call (built-in or user-defined)."""
        name = expr.name

        # User-defined functions
        if name in self.user_fns:
            fn_def = self.user_fns[name]
            arg_vals = [self._eval(a) for a in expr.args]
            if len(arg_vals) != len(fn_def.params):
                raise BasicRuntimeError(f"FN {name}: expected {len(fn_def.params)} args, got {len(arg_vals)}")
            saved: dict = {}
            for param, val in zip(fn_def.params, arg_vals):
                saved[param] = self.variables.get(param)
                self.variables[param] = val
            try:
                result = self._eval(fn_def.body)
            finally:
                for param, old_val in saved.items():
                    if old_val is None:
                        self.variables.pop(param, None)
                    else:
                        self.variables[param] = old_val
            return result

        # Built-in functions
        args = [self._eval(a) for a in expr.args]

        math_fns = {
            "ABS": lambda a: abs(self._to_number(a[0])),
            "INT": lambda a: float(math.floor(self._to_number(a[0]))),
            "FIX": lambda a: float(math.trunc(self._to_number(a[0]))),
            "SGN": lambda a: 1.0 if self._to_number(a[0]) > 0 else (-1.0 if self._to_number(a[0]) < 0 else 0.0),
            "SQR": lambda a: self._sqr(a[0]),
            "SIN": lambda a: math.sin(self._to_number(a[0])),
            "COS": lambda a: math.cos(self._to_number(a[0])),
            "TAN": lambda a: math.tan(self._to_number(a[0])),
            "ATN": lambda a: math.atan(self._to_number(a[0])),
            "LOG": lambda a: self._log(a[0]),
            "EXP": lambda a: math.exp(self._to_number(a[0])),
            "CINT": lambda a: float(round(self._to_number(a[0]))),
            "CSNG": lambda a: float(self._to_number(a[0])),
            "CDBL": lambda a: float(self._to_number(a[0])),
            "LEN": lambda a: float(len(str(a[0]))),
            "ASC": lambda a: self._asc(a[0]),
            "VAL": lambda a: self._val(a[0]),
            "FRE": lambda a: float(655360),
            "PEEK": lambda a: 0.0,
            "TIMER": lambda a: time.time() % 86400,
        }

        if name in math_fns:
            return math_fns[name](args)

        # RND — special handling for seed
        if name == "RND":
            if args:
                x = self._to_number(args[0])
                if x < 0:
                    random.seed(int(x))
                elif x == 0:
                    return random.random()
            return random.random()

        # String functions
        if name == "LEFT$":
            return str(args[0])[:int(self._to_number(args[1]))]
        if name == "RIGHT$":
            s = str(args[0])
            n = int(self._to_number(args[1]))
            return s[-n:] if n > 0 else ""
        if name == "MID$":
            s = str(args[0])
            start = int(self._to_number(args[1])) - 1
            if start < 0:
                start = 0
            if len(args) > 2:
                length = int(self._to_number(args[2]))
                return s[start:start + length]
            return s[start:]
        if name == "CHR$":
            code = int(self._to_number(args[0]))
            try:
                return chr(code)
            except ValueError:
                return "?"
        if name == "STR$":
            val = args[0]
            if isinstance(val, float) and val == int(val):
                return " " + str(int(val))
            return str(val)
        if name == "LCASE$":
            return str(args[0]).lower()
        if name == "UCASE$":
            return str(args[0]).upper()
        if name == "LTRIM$":
            return str(args[0]).lstrip()
        if name == "RTRIM$":
            return str(args[0]).rstrip()
        if name == "STRING$":
            n = int(self._to_number(args[0]))
            if isinstance(args[1], (int, float)):
                return chr(int(args[1])) * n
            return str(args[1])[0] * n if str(args[1]) else ""
        if name == "INSTR":
            if len(args) == 2:
                haystack = str(args[0])
                needle = str(args[1])
                idx = haystack.find(needle)
                return float(idx + 1) if idx >= 0 else 0.0
            elif len(args) == 3:
                start = int(self._to_number(args[0])) - 1
                haystack = str(args[1])
                needle = str(args[2])
                idx = haystack.find(needle, max(0, start))
                return float(idx + 1) if idx >= 0 else 0.0

        # I/O and system functions
        if name == "TAB":
            n = int(self._to_number(args[0]))
            spaces = max(0, n - self._print_col)
            self.stdout.write(" " * spaces)
            self._print_col = n
            return ""
        if name == "SPC":
            n = int(self._to_number(args[0]))
            self.stdout.write(" " * max(0, n))
            self._print_col += n
            return ""
        if name == "DATE$":
            return datetime.date.today().strftime("%m-%d-%Y")
        if name == "TIME$":
            return datetime.datetime.now().strftime("%H:%M:%S")
        if name == "INKEY$":
            return ""
        if name == "ENVIRON$":
            if args:
                return os.environ.get(str(args[0]), "")
            return ""

        raise BasicRuntimeError(f"Unknown function: {name}")

    def _sqr(self, val) -> float:
        """Square root with negative number check."""
        n = self._to_number(val)
        if n < 0:
            raise BasicRuntimeError("SQR of negative number")
        return math.sqrt(n)

    def _log(self, val) -> float:
        """Natural logarithm with non-positive check."""
        n = self._to_number(val)
        if n <= 0:
            raise BasicRuntimeError("LOG of non-positive number")
        return math.log(n)

    def _asc(self, val) -> float:
        """ASCII value of first character."""
        s = str(val)
        if not s:
            raise BasicRuntimeError("ASC of empty string")
        return float(ord(s[0]))

    def _val(self, val) -> float:
        """Convert string to number."""
        s = str(val).strip()
        try:
            if "." in s:
                return float(s)
            return float(int(s))
        except ValueError:
            return 0.0

    def _eval_binop(self, expr: BinOp) -> Any:
        """Evaluate a binary operation."""
        # Logical operators (short-circuit for AND/OR)
        if expr.op == "AND":
            left = self._truthy(self._eval(expr.left))
            if not left:
                return 0
            right = self._truthy(self._eval(expr.right))
            return -1 if right else 0
        if expr.op == "OR":
            left = self._truthy(self._eval(expr.left))
            if left:
                return -1
            right = self._truthy(self._eval(expr.right))
            return -1 if right else 0
        if expr.op == "XOR":
            left = self._truthy(self._eval(expr.left))
            right = self._truthy(self._eval(expr.right))
            return -1 if left != right else 0
        if expr.op == "EQV":
            left = self._truthy(self._eval(expr.left))
            right = self._truthy(self._eval(expr.right))
            return -1 if left == right else 0
        if expr.op == "IMP":
            left = self._truthy(self._eval(expr.left))
            right = self._truthy(self._eval(expr.right))
            return -1 if (not left) or right else 0

        left = self._eval(expr.left)
        right = self._eval(expr.right)

        if expr.op == "+" and (isinstance(left, str) or isinstance(right, str)):
            return str(left) + str(right)

        if expr.op in ("=", "<>", "<", ">", "<=", ">=") and isinstance(left, str) and isinstance(right, str):
            ops = {"=": lambda a, b: a == b, "<>": lambda a, b: a != b,
                   "<": lambda a, b: a < b, ">": lambda a, b: a > b,
                   "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}
            return -1 if ops[expr.op](left, right) else 0

        ln = self._to_number(left)
        rn = self._to_number(right)

        if expr.op == "+": return ln + rn
        if expr.op == "-": return ln - rn
        if expr.op == "*": return ln * rn
        if expr.op == "/":
            if rn == 0: raise BasicRuntimeError("Division by zero")
            return ln / rn
        if expr.op == "\\":
            if rn == 0: raise BasicRuntimeError("Division by zero")
            return float(int(int(ln) / int(rn)))
        if expr.op == "MOD":
            if rn == 0: raise BasicRuntimeError("Division by zero")
            return float(int(ln) - int(int(ln) / int(rn)) * int(rn))
        if expr.op == "^": return ln ** rn
        if expr.op == "=": return -1 if ln == rn else 0
        if expr.op == "<>": return -1 if ln != rn else 0
        if expr.op == "<": return -1 if ln < rn else 0
        if expr.op == ">": return -1 if ln > rn else 0
        if expr.op == "<=": return -1 if ln <= rn else 0
        if expr.op == ">=": return -1 if ln >= rn else 0

        raise BasicRuntimeError(f"Unknown operator: {expr.op}")

    def _to_number(self, val) -> float:
        """Convert a value to a float number."""
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                return 0.0
        if isinstance(val, bool):
            return -1.0 if val else 0.0
        return 0.0