"""
forth_interpreter.py
====================
A standalone Forth interpreter implemented in pure Python.

Supports:
  • Integer and float arithmetic
  • Stack manipulation (DUP, DROP, SWAP, OVER, ROT, 2DUP, PICK, ROLL, ...)
  • Variables, constants, values, and arrays
  • Colon definitions with compilation to bytecode IR
  • Control flow: IF/ELSE/THEN, BEGIN/UNTIL, BEGIN/WHILE/REPEAT, AGAIN,
    DO/LOOP, DO/+LOOP, LEAVE, EXIT, RECURSE, CASE/OF/ENDOF/ENDCASE
  • String literals and output (." text")
  • Memory operations (!, @, +!, []!, []@)
  • Bitwise operations
  • Interactive REPL with error recovery
"""

from __future__ import annotations

import math
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple


class ForthError(Exception):
    """Raised on Forth-level errors."""


class _ExitBody(Exception):
    """Internal signal: EXIT was called; stop executing current body."""


class _NextIdx:
    """Wrapper for a 'next token index' return value from a native word.

    Regular native words may return int values (e.g. DROP returns the popped
    value).  To distinguish a genuine 'jump to index N' return from a value
    that happens to be an int, defining words wrap their return in _NextIdx.
    """

    __slots__ = ("idx",)

    def __init__(self, idx: int) -> None:
        self.idx = idx


class Word:
    """A Forth word definition."""

    __slots__ = ("name", "immediate", "data", "native", "doc", "hidden")

    def __init__(
        self,
        name: str,
        immediate: bool = False,
        data: Optional[List[Any]] = None,
        native: Optional[Callable[..., Any]] = None,
        doc: str = "",
        hidden: bool = False,
    ) -> None:
        self.name = name
        self.immediate = immediate
        self.data = data if data is not None else []
        self.native = native
        self.doc = doc
        self.hidden = hidden


NativeFn = Callable[["ForthInterpreter", List[str], int], Any]


class ForthInterpreter:
    """The core Forth interpreter."""

    def __init__(self, output: Optional[Any] = None) -> None:
        self.stack: List[Any] = []
        self.return_stack: List[Any] = []
        self.words: Dict[str, Word] = {}
        self.output = output if output is not None else sys.stdout
        self.compiling: bool = False
        self.current_def: List[Any] = []
        self.current_name: str = ""
        self.variables: Dict[str, List[Any]] = {}
        self._defining_words: Dict[str, NativeFn] = {}
        self._register_builtins()

    # ─── output ───────────────────────────────────────────────────────────
    def emit(self, s: str) -> None:
        self.output.write(s)

    def emit_line(self, s: str = "") -> None:
        self.output.write(s + "\n")

    # ─── stack helpers ─────────────────────────────────────────────────────
    def push(self, v: Any) -> None:
        self.stack.append(v)

    def pop(self) -> Any:
        if not self.stack:
            raise ForthError("stack underflow")
        return self.stack.pop()

    def pop_int(self) -> int:
        v = self.pop()
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, float):
            if v.is_integer():
                return int(v)
            raise ForthError(f"float {v} is not integral")
        if isinstance(v, int):
            return v
        raise ForthError(f"cannot use {type(v).__name__} as integer")

    def peek(self) -> Any:
        if not self.stack:
            raise ForthError("stack underflow")
        return self.stack[-1]

    # ─── word registry ─────────────────────────────────────────────────────
    def define(self, word: Word) -> None:
        self.words[word.name.upper()] = word

    def lookup(self, name: str) -> Optional[Word]:
        return self.words.get(name.upper())

    def reg(self, name: str, fn: NativeFn, immediate: bool = False, doc: str = "") -> None:
        self.define(Word(name=name.upper(), native=fn, immediate=immediate, doc=doc))

    # ─── tokenisation ──────────────────────────────────────────────────────
    @staticmethod
    def tokenize(source: str) -> List[str]:
        """Split source into tokens; handle \\ line comments and ( ... ) block comments."""
        tokens: List[str] = []
        i, n = 0, len(source)
        while i < n:
            c = source[i]
            if c.isspace():
                i += 1
                continue
            if c == "\\" and (i == 0 or source[i - 1].isspace()):
                while i < n and source[i] != "\n":
                    i += 1
                continue
            if c == "(":
                depth = 1
                i += 1
                while i < n and depth > 0:
                    if source[i] == "(":
                        depth += 1
                    elif source[i] == ")":
                        depth -= 1
                    i += 1
                continue
            if c == '"':
                j = i + 1
                buf: List[str] = []
                while j < n and source[j] != '"':
                    buf.append(source[j])
                    j += 1
                if j >= n:
                    raise ForthError("unterminated string literal")
                tokens.append('"' + "".join(buf) + '"')
                i = j + 1
                continue
            j = i
            while j < n and not source[j].isspace():
                j += 1
            tokens.append(source[i:j])
            i = j
        return tokens

    # ─── number parsing ─────────────────────────────────────────────────────
    @staticmethod
    def parse_number(tok: str) -> Optional[Any]:
        """Try to parse *tok* as an int or float; return None on failure."""
        try:
            return int(tok)
        except ValueError:
            pass
        try:
            return float(tok)
        except ValueError:
            pass
        return None

    # ─── main eval ─────────────────────────────────────────────────────────
    def eval(self, source: str) -> None:
        tokens = self.tokenize(source)
        idx = 0
        try:
            while idx < len(tokens):
                idx = self._step(tokens, idx)
        except ForthError:
            self._reset_state()
            raise

    def _step(self, tokens: List[str], idx: int) -> int:
        if self.compiling:
            return self._compile_token(tokens, idx)
        return self._execute_token(tokens, idx)

    # ─── execution mode ────────────────────────────────────────────────────
    def _execute_token(self, tokens: List[str], idx: int) -> int:
        tok = tokens[idx]

        # : — start a definition
        if tok == ":":
            if idx + 1 >= len(tokens):
                raise ForthError(": needs a name")
            self.current_name = tokens[idx + 1]
            self.current_def = []
            self.compiling = True
            return idx + 2

        # defining words that consume the next token
        dw = self._defining_words.get(tok.upper())
        if dw is not None:
            result = dw(self, tokens, idx)
            if isinstance(result, _NextIdx):
                return result.idx
            return idx + 1

        # dictionary lookup
        word = self.lookup(tok)
        if word is not None:
            if word.native is not None:
                result = word.native(self, tokens, idx)
                # Only treat int returns as "consume extra tokens" for defining words.
                # Regular builtins may return int values (e.g. DROP returns popped value)
                # so we must NOT interpret those as jump indices.
                # Defining words return a 2-tuple (next_idx,) — but simpler: we use
                # a special _NextIdx wrapper.
                if isinstance(result, _NextIdx):
                    return result.idx
                return idx + 1
            self._execute_body(word.data)
            return idx + 1

        # number literal
        num = self.parse_number(tok)
        if num is not None:
            self.push(num)
            return idx + 1

        # string literal
        if tok.startswith('"') and tok.endswith('"'):
            self.push(tok[1:-1])
            return idx + 1

        raise ForthError(f"unknown word: {tok}")

    # ─── compilation mode ──────────────────────────────────────────────────
    def _compile_token(self, tokens: List[str], idx: int) -> int:
        tok = tokens[idx]

        # ; — end definition
        if tok == ";":
            if not self.compiling:
                raise ForthError("; outside definition")
            self.define(Word(name=self.current_name.upper(), data=self.current_def))
            self.compiling = False
            self.current_def = []
            return idx + 1

        # immediate words execute even during compilation
        word = self.lookup(tok)
        if word is not None and word.immediate:
            result = word.native(self, tokens, idx)
            if isinstance(result, _NextIdx):
                return result.idx
            return idx + 1

        # number literal → compile as LIT
        num = self.parse_number(tok)
        if num is not None:
            self.current_def.append(("lit", num))
            return idx + 1

        # string literal → compile as LIT
        if tok.startswith('"') and tok.endswith('"'):
            self.current_def.append(("lit", tok[1:-1]))
            return idx + 1

        # regular word → compile as CALL
        if word is not None:
            self.current_def.append(("call", word.name))
            return idx + 1

        raise ForthError(f"unknown word in definition: {tok}")

    # ─── execute a compiled body ──────────────────────────────────────────
    def _execute_body(self, body: List[Any]) -> None:
        """Execute compiled instructions with control-flow support."""
        ip = 0
        try:
            while ip < len(body):
                instr = body[ip]
                tag = instr[0]

                if tag == "lit":
                    self.push(instr[1])
                elif tag == "call":
                    w = self.lookup(instr[1])
                    if w is None:
                        raise ForthError(f"undefined word: {instr[1]}")
                    if w.native is not None:
                        w.native(self, [], 0)
                    else:
                        self._execute_body(w.data)
                elif tag == "if":
                    flag = self.pop()
                    if flag == 0:
                        ip = instr[1]
                        continue
                elif tag == "jump":
                    ip = instr[1]
                    continue
                elif tag == "until":
                    flag = self.pop()
                    if flag == 0:
                        ip = instr[1]
                        continue
                elif tag == "while":
                    flag = self.pop()
                    if flag == 0:
                        ip = instr[1]
                        continue
                elif tag == "do":
                    start = self.pop()
                    limit = self.pop()
                    self.return_stack.append(["loop-state", start, limit])
                elif tag == "loop":
                    state = self._find_loop_state()
                    if state is None:
                        raise ForthError("LOOP without DO")
                    state[1] += 1
                    if state[1] < state[2]:
                        ip = instr[1]
                        continue
                    else:
                        self._pop_loop_state()
                elif tag == "plusloop":
                    inc = self.pop_int()
                    state = self._find_loop_state()
                    if state is None:
                        raise ForthError("+LOOP without DO")
                    old = state[1]
                    limit = state[2]
                    new = old + inc
                    state[1] = new
                    # ANS Forth: loop terminates when index crosses the
                    # boundary between limit-1 and limit (positive inc)
                    # or between 0 and -1 (negative inc, i.e. when < 0)
                    if inc > 0 and new < limit:
                        ip = instr[1]
                        continue
                    elif inc < 0 and new >= 0:
                        ip = instr[1]
                        continue
                    else:
                        self._pop_loop_state()
                elif tag == "leave":
                    self._pop_loop_state()
                    ip = instr[1]
                    continue
                else:
                    raise ForthError(f"bad instruction: {instr}")

                ip += 1
        except _ExitBody:
            pass

    def _find_loop_state(self) -> Optional[List[Any]]:
        """Find the innermost loop-state on the return stack."""
        for item in reversed(self.return_stack):
            if isinstance(item, list) and item and item[0] == "loop-state":
                return item
        return None

    def _pop_loop_state(self) -> None:
        """Pop the innermost loop-state."""
        for k in range(len(self.return_stack) - 1, -1, -1):
            item = self.return_stack[k]
            if isinstance(item, list) and item and item[0] == "loop-state":
                self.return_stack.pop(k)
                return

    # ─── register built-in words ──────────────────────────────────────────
    def _register_builtins(self) -> None:
        # ── stack manipulation ──
        self.reg("DUP", lambda i, t, n: i.push(i.peek()), doc="Duplicate top")
        self.reg("DROP", lambda i, t, n: i.pop(), doc="Remove top")
        self.reg("?DUP", lambda i, t, n: i.push(i.peek()) if i.peek() != 0 else None, doc="Dup if nonzero")

        def _swap(i, t, n):
            a, b = i.pop(), i.pop()
            i.push(a)
            i.push(b)
        self.reg("SWAP", _swap, doc="Swap top two")

        def _over(i, t, n):
            if len(i.stack) < 2:
                raise ForthError("OVER needs 2 items")
            i.push(i.stack[-2])
        self.reg("OVER", _over, doc="Copy second to top")

        def _rot(i, t, n):
            if len(i.stack) < 3:
                raise ForthError("ROT needs 3 items")
            c = i.stack.pop()
            b = i.stack.pop()
            a = i.stack.pop()
            i.push(b)
            i.push(c)
            i.push(a)
        self.reg("ROT", _rot, doc="Rotate top three")

        def _minus_rot(i, t, n):
            if len(i.stack) < 3:
                raise ForthError("-ROT needs 3 items")
            c = i.stack.pop()
            b = i.stack.pop()
            a = i.stack.pop()
            i.push(c)
            i.push(a)
            i.push(b)
        self.reg("-ROT", _minus_rot, doc="Rotate top three (reverse)")

        def _nip(i, t, n):
            if len(i.stack) < 2:
                raise ForthError("NIP needs 2 items")
            i.stack.pop(-2)
        self.reg("NIP", _nip, doc="Remove second item")

        def _tuck(i, t, n):
            if len(i.stack) < 2:
                raise ForthError("TUCK needs 2 items")
            top = i.stack[-1]
            i.stack.insert(-2, top)
        self.reg("TUCK", _tuck, doc="Dup top, insert under second")

        self.reg("DEPTH", lambda i, t, n: i.push(len(i.stack)), doc="Push stack depth")

        # ── double stack ops ──
        def _2dup(i, t, n):
            if len(i.stack) < 2:
                raise ForthError("2DUP needs 2 items")
            i.stack.append(i.stack[-2])
            i.stack.append(i.stack[-2])
        self.reg("2DUP", _2dup, doc="Duplicate top two items")

        def _2drop(i, t, n):
            i.pop()
            i.pop()
        self.reg("2DROP", _2drop, doc="Remove top two items")

        def _2swap(i, t, n):
            if len(i.stack) < 4:
                raise ForthError("2SWAP needs 4 items")
            b2 = i.stack.pop()
            b1 = i.stack.pop()
            a2 = i.stack.pop()
            a1 = i.stack.pop()
            i.push(b1)
            i.push(b2)
            i.push(a1)
            i.push(a2)
        self.reg("2SWAP", _2swap, doc="Swap top two pairs")

        def _2over(i, t, n):
            if len(i.stack) < 4:
                raise ForthError("2OVER needs 4 items")
            i.push(i.stack[-4])
            i.push(i.stack[-4])
        self.reg("2OVER", _2over, doc="Copy third/fourth to top")

        # ── return stack ──
        def _to_r(i, t, n):
            i.return_stack.append(i.pop())
        self.reg(">R", _to_r, doc="Push to return stack")

        def _r_from(i, t, n):
            if not i.return_stack:
                raise ForthError("return stack underflow")
            i.push(i.return_stack.pop())
        self.reg("R>", _r_from, doc="Pop from return stack")

        def _r_fetch(i, t, n):
            if not i.return_stack:
                raise ForthError("return stack underflow")
            i.push(i.return_stack[-1])
        self.reg("R@", _r_fetch, doc="Copy return stack top")

        # ── arithmetic ──
        def _add(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(a + b)
        self.reg("+", _add, doc="Addition")

        def _sub(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(a - b)
        self.reg("-", _sub, doc="Subtraction")

        def _mul(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(a * b)
        self.reg("*", _mul, doc="Multiplication")

        def _div(i, t, n):
            b = i.pop_int()
            if b == 0:
                raise ForthError("division by zero")
            a = i.pop_int()
            q = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                q = -q
            i.push(q)
        self.reg("/", _div, doc="Integer division (truncate toward zero)")

        def _mod(i, t, n):
            b = i.pop_int()
            if b == 0:
                raise ForthError("modulo by zero")
            a = i.pop_int()
            r = abs(a) % abs(b)
            if a < 0:
                r = -r
            i.push(r)
        self.reg("MOD", _mod, doc="Modulo (sign follows dividend)")

        def _divmod(i, t, n):
            b = i.pop_int()
            if b == 0:
                raise ForthError("division by zero")
            a = i.pop_int()
            q = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                q = -q
            r = abs(a) % abs(b)
            if a < 0:
                r = -r
            i.push(r)
            i.push(q)
        self.reg("/MOD", _divmod, doc="Division with remainder")

        self.reg("NEGATE", lambda i, t, n: i.push(-i.pop()), doc="Negate")
        self.reg("ABS", lambda i, t, n: i.push(abs(i.pop())), doc="Absolute value")

        def _min(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(min(a, b))
        self.reg("MIN", _min, doc="Minimum")

        def _max(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(max(a, b))
        self.reg("MAX", _max, doc="Maximum")

        def _pow(i, t, n):
            b = i.pop_int()
            a = i.pop_int()
            i.push(a ** b)
        self.reg("**", _pow, doc="Power")

        # ── floating point ──
        def _fadd(i, t, n):
            b = float(i.pop())
            a = float(i.pop())
            i.push(a + b)
        self.reg("F+", _fadd, doc="Float add")

        def _fsub(i, t, n):
            b = float(i.pop())
            a = float(i.pop())
            i.push(a - b)
        self.reg("F-", _fsub, doc="Float subtract")

        def _fmul(i, t, n):
            b = float(i.pop())
            a = float(i.pop())
            i.push(a * b)
        self.reg("F*", _fmul, doc="Float multiply")

        def _fdiv(i, t, n):
            b = float(i.pop())
            if b == 0.0:
                raise ForthError("float division by zero")
            a = float(i.pop())
            i.push(a / b)
        self.reg("F/", _fdiv, doc="Float divide")

        self.reg("FSQRT", lambda i, t, n: i.push(math.sqrt(float(i.pop()))), doc="Float sqrt")
        self.reg("FSIN", lambda i, t, n: i.push(math.sin(float(i.pop()))), doc="Float sin")
        self.reg("FCOS", lambda i, t, n: i.push(math.cos(float(i.pop()))), doc="Float cos")
        self.reg("FTAN", lambda i, t, n: i.push(math.tan(float(i.pop()))), doc="Float tan")
        self.reg("FLOG", lambda i, t, n: i.push(math.log(float(i.pop()))), doc="Float natural log")
        self.reg("FEXP", lambda i, t, n: i.push(math.exp(float(i.pop()))), doc="Float exp")
        self.reg("FLOOR", lambda i, t, n: i.push(math.floor(float(i.pop()))), doc="Floor")
        self.reg("CEIL", lambda i, t, n: i.push(math.ceil(float(i.pop()))), doc="Ceiling")
        self.reg("ROUND", lambda i, t, n: i.push(round(float(i.pop()))), doc="Round")

        # ── comparison ──
        self.reg("=", lambda i, t, n: i.push(-1 if i.pop() == i.pop() else 0), doc="Equal")
        self.reg("<>", lambda i, t, n: i.push(-1 if i.pop() != i.pop() else 0), doc="Not equal")

        def _lt(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(-1 if a < b else 0)
        self.reg("<", _lt, doc="Less than")

        def _gt(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(-1 if a > b else 0)
        self.reg(">", _gt, doc="Greater than")

        def _le(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(-1 if a <= b else 0)
        self.reg("<=", _le, doc="Less or equal")

        def _ge(i, t, n):
            b = i.pop()
            a = i.pop()
            i.push(-1 if a >= b else 0)
        self.reg(">=", _ge, doc="Greater or equal")

        self.reg("0=", lambda i, t, n: i.push(-1 if i.pop() == 0 else 0), doc="Top == 0?")
        self.reg("0<>", lambda i, t, n: i.push(-1 if i.pop() != 0 else 0), doc="Top != 0?")
        self.reg("0<", lambda i, t, n: i.push(-1 if i.pop() < 0 else 0), doc="Top < 0?")
        self.reg("0>", lambda i, t, n: i.push(-1 if i.pop() > 0 else 0), doc="Top > 0?")

        # ── logic / bitwise ──
        self.reg("AND", lambda i, t, n: i.push(i.pop_int() & i.pop_int()), doc="Bitwise AND")
        self.reg("OR", lambda i, t, n: i.push(i.pop_int() | i.pop_int()), doc="Bitwise OR")
        self.reg("XOR", lambda i, t, n: i.push(i.pop_int() ^ i.pop_int()), doc="Bitwise XOR")
        self.reg("INVERT", lambda i, t, n: i.push(~i.pop_int()), doc="Bitwise NOT")

        def _lshift(i, t, n):
            b = i.pop_int()
            a = i.pop_int()
            i.push(a << b)
        self.reg("LSHIFT", _lshift, doc="Left shift")

        def _rshift(i, t, n):
            b = i.pop_int()
            a = i.pop_int()
            i.push(a >> b)
        self.reg("RSHIFT", _rshift, doc="Right shift")

        self.reg("NOT", lambda i, t, n: i.push(-1 if i.pop() == 0 else 0), doc="Logical NOT")

        # ── I/O ──
        def _dot(i, t, n):
            v = i.pop()
            if isinstance(v, float):
                i.emit(f"{v:g} ")
            elif isinstance(v, bool):
                i.emit("-1 " if v else "0 ")
            else:
                i.emit(f"{v} ")
        self.reg(".", _dot, doc="Print top + space")

        self.reg(".\"", lambda i, t, n: None, doc="Print string (compiled)", immediate=True)

        def _emit(i, t, n):
            i.emit(chr(i.pop_int()))
        self.reg("EMIT", _emit, doc="Print char")

        self.reg("CR", lambda i, t, n: i.emit("\n"), doc="Newline")
        self.reg("SPACE", lambda i, t, n: i.emit(" "), doc="Space")
        self.reg("BL", lambda i, t, n: i.push(32), doc="Blank char code")

        def _dots(i, t, n):
            i.emit("<" + " ".join(str(v) for v in i.stack) + ">")
        self.reg(".S", _dots, doc="Show stack")

        # ── variables / constants / values ──
        def _variable(i, t, n):
            if n + 1 >= len(t):
                raise ForthError("VARIABLE needs a name")
            name = t[n + 1].upper()
            i.variables[name] = [0]

            def _push_addr(i2, t2, n2, _name=name):
                i2.push(_name)
            i.define(Word(name=name, native=_push_addr, doc=f"variable {name}"))
            return _NextIdx(n + 2)
        self._defining_words["VARIABLE"] = _variable

        def _constant(i, t, n):
            if n + 1 >= len(t):
                raise ForthError("CONSTANT needs a name")
            name = t[n + 1].upper()
            val = i.pop()

            def _push_const(i2, t2, n2, _v=val):
                i2.push(_v)
            i.define(Word(name=name, native=_push_const, doc=f"constant {name}"))
            return _NextIdx(n + 2)
        self._defining_words["CONSTANT"] = _constant

        def _value(i, t, n):
            if n + 1 >= len(t):
                raise ForthError("VALUE needs a name")
            name = t[n + 1].upper()
            val = i.pop()
            i.variables[name] = [val]

            def _push_val(i2, t2, n2, _name=name):
                i2.push(i2.variables[_name][0])
            i.define(Word(name=name, native=_push_val, doc=f"value {name}"))
            return _NextIdx(n + 2)
        self._defining_words["VALUE"] = _value

        def _to(i, t, n):
            if n + 1 >= len(t):
                raise ForthError("TO needs a name")
            name = t[n + 1].upper()
            if name not in i.variables:
                raise ForthError(f"TO: {name} is not a value")
            i.variables[name][0] = i.pop()
            return _NextIdx(n + 2)
        self._defining_words["TO"] = _to

        # ── memory ──
        def _store(i, t, n):
            addr = i.pop()
            val = i.pop()
            if isinstance(addr, str) and addr in i.variables:
                i.variables[addr][0] = val
            else:
                raise ForthError(f"bad address: {addr}")
        self.reg("!", _store, doc="Store ( val addr -- )")

        def _fetch(i, t, n):
            addr = i.pop()
            if isinstance(addr, str) and addr in i.variables:
                i.push(i.variables[addr][0])
            else:
                raise ForthError(f"bad address: {addr}")
        self.reg("@", _fetch, doc="Fetch ( addr -- val )")

        def _plus_store(i, t, n):
            addr = i.pop()
            val = i.pop()
            if isinstance(addr, str) and addr in i.variables:
                i.variables[addr][0] += val
            else:
                raise ForthError(f"bad address: {addr}")
        self.reg("+!", _plus_store, doc="Add to stored ( n addr -- )")

        # ── control flow (immediate compilation words) ──
        def _if(i, t, n):
            i.current_def.append(["if", None])
            i.return_stack.append(("if-fixup", len(i.current_def) - 1))
            return n + 1
        self.reg("IF", _if, immediate=True, doc="IF ( flag -- )")

        def _else(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "if-fixup":
                raise ForthError("ELSE without IF")
            if_pos = i.return_stack.pop()[1]
            i.current_def.append(["jump", None])
            jump_pos = len(i.current_def) - 1
            i.current_def[if_pos][1] = len(i.current_def)
            i.return_stack.append(("if-fixup", jump_pos))
            return n + 1
        self.reg("ELSE", _else, immediate=True, doc="ELSE")

        def _then(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "if-fixup":
                raise ForthError("THEN without IF")
            pos = i.return_stack.pop()[1]
            i.current_def[pos][1] = len(i.current_def)
            return n + 1
        self.reg("THEN", _then, immediate=True, doc="THEN")

        def _begin(i, t, n):
            i.return_stack.append(("begin", len(i.current_def)))
            return n + 1
        self.reg("BEGIN", _begin, immediate=True, doc="BEGIN")

        def _until(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "begin":
                raise ForthError("UNTIL without BEGIN")
            begin_pos = i.return_stack.pop()[1]
            i.current_def.append(["until", begin_pos])
            return n + 1
        self.reg("UNTIL", _until, immediate=True, doc="UNTIL")

        def _while(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "begin":
                raise ForthError("WHILE without BEGIN")
            i.current_def.append(["while", None])
            i.return_stack.append(("while-fixup", len(i.current_def) - 1))
            return n + 1
        self.reg("WHILE", _while, immediate=True, doc="WHILE")

        def _repeat(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "while-fixup":
                raise ForthError("REPEAT without WHILE")
            while_pos = i.return_stack.pop()[1]
            if not i.return_stack or i.return_stack[-1][0] != "begin":
                raise ForthError("REPEAT without BEGIN")
            begin_pos = i.return_stack.pop()[1]
            i.current_def.append(["jump", begin_pos])
            i.current_def[while_pos][1] = len(i.current_def)
            return n + 1
        self.reg("REPEAT", _repeat, immediate=True, doc="REPEAT")

        # AGAIN — unconditional jump back to BEGIN (infinite loop, exit via EXIT/LEAVE)
        def _again(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "begin":
                raise ForthError("AGAIN without BEGIN")
            begin_pos = i.return_stack.pop()[1]
            i.current_def.append(["jump", begin_pos])
            return n + 1
        self.reg("AGAIN", _again, immediate=True, doc="AGAIN")

        def _do(i, t, n):
            i.current_def.append(["do", None])
            i.return_stack.append(("do-fixup", len(i.current_def) - 1))
            i.return_stack.append(("do-leave", []))
            return n + 1
        self.reg("DO", _do, immediate=True, doc="DO")

        def _loop(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "do-leave":
                raise ForthError("LOOP without DO")
            leave_positions = i.return_stack.pop()[1]
            if not i.return_stack or i.return_stack[-1][0] != "do-fixup":
                raise ForthError("LOOP without DO")
            do_pos = i.return_stack.pop()[1]
            i.current_def.append(["loop", do_pos + 1])
            i.current_def[do_pos][1] = len(i.current_def)
            for lp in leave_positions:
                i.current_def[lp][1] = len(i.current_def)
            return n + 1
        self.reg("LOOP", _loop, immediate=True, doc="LOOP")

        def _plus_loop(i, t, n):
            if not i.return_stack or i.return_stack[-1][0] != "do-leave":
                raise ForthError("+LOOP without DO")
            leave_positions = i.return_stack.pop()[1]
            if not i.return_stack or i.return_stack[-1][0] != "do-fixup":
                raise ForthError("+LOOP without DO")
            do_pos = i.return_stack.pop()[1]
            i.current_def.append(["plusloop", do_pos + 1])
            i.current_def[do_pos][1] = len(i.current_def)
            for lp in leave_positions:
                i.current_def[lp][1] = len(i.current_def)
            return n + 1
        self.reg("+LOOP", _plus_loop, immediate=True, doc="+LOOP")

        def _leave(i, t, n):
            # Search for do-leave on the return stack (may be under if-fixup etc.)
            found = False
            for item in i.return_stack:
                if isinstance(item, tuple) and item[0] == "do-leave":
                    found = True
                    break
            if not found:
                raise ForthError("LEAVE outside DO")
            i.current_def.append(["leave", None])
            # Find the do-leave tuple and append to its list
            for k in range(len(i.return_stack) - 1, -1, -1):
                item = i.return_stack[k]
                if isinstance(item, tuple) and item[0] == "do-leave":
                    i.return_stack[k] = ("do-leave", item[1] + [len(i.current_def) - 1])
                    break
            return n + 1
        self.reg("LEAVE", _leave, immediate=True, doc="LEAVE")

        # EXIT — return early from a word
        def _exit(i, t, n):
            raise _ExitBody()
        self.reg("EXIT", _exit, doc="Return from word")

        # RECURSE — compile a call to the word currently being defined
        def _recurse(i, t, n):
            i.current_def.append(["call", i.current_name.upper()])
            return n + 1
        self.reg("RECURSE", _recurse, immediate=True, doc="Recursive self-call")

        # ── loop index access ──
        def _i(i, t, n):
            state = i._find_loop_state()
            if state is None:
                raise ForthError("I outside DO loop")
            i.push(state[1])
        self.reg("I", _i, doc="Loop index")

        def _j(i, t, n):
            count = 0
            for item in reversed(i.return_stack):
                if isinstance(item, list) and item and item[0] == "loop-state":
                    count += 1
                    if count == 2:
                        i.push(item[1])
                        return
            raise ForthError("J outside nested DO loop")
        self.reg("J", _j, doc="Outer loop index")

        # ── strings ──
        self.reg("TYPE", lambda i, t, n: i.emit(str(i.pop())), doc="Print top as string")

        # ── utility ──
        def _words(i, t, n):
            ws = sorted(w.name for w in i.words.values() if not w.hidden)
            i.emit(" ".join(ws) + "\n")
        self.reg("WORDS", _words, doc="List words")

        def _see(i, t, n):
            if n + 1 >= len(t):
                raise ForthError("SEE needs a name")
            name = t[n + 1].upper()
            w = i.lookup(name)
            if w is None:
                raise ForthError(f"unknown word: {name}")
            i.emit(f": {name} ")
            if w.native is not None:
                i.emit("(native)")
            else:
                for d in w.data:
                    if d[0] == "lit":
                        i.emit(f"{d[1]} ")
                    elif d[0] == "call":
                        i.emit(f"{d[1]} ")
                    else:
                        i.emit(f"{d[0]} ")
            i.emit(";\n")
            return _NextIdx(n + 2)
        self.reg("SEE", _see, doc="Decompile word")

        def _forget(i, t, n):
            if n + 1 >= len(t):
                raise ForthError("FORGET needs a name")
            name = t[n + 1].upper()
            if name in i.words:
                del i.words[name]
            if name in i.variables:
                del i.variables[name]
            return _NextIdx(n + 2)
        self.reg("FORGET", _forget, doc="Remove word")

        def _bye(i, t, n):
            raise SystemExit(0)
        self.reg("BYE", _bye, doc="Exit")

        # ── boolean helpers ──
        self.reg("TRUE", lambda i, t, n: i.push(-1), doc="Push true (-1)")
        self.reg("FALSE", lambda i, t, n: i.push(0), doc="Push false (0)")

        # ── convenience arithmetic ──
        self.reg("1+", lambda i, t, n: i.push(i.pop() + 1), doc="Add 1")
        self.reg("1-", lambda i, t, n: i.push(i.pop() - 1), doc="Subtract 1")
        self.reg("2+", lambda i, t, n: i.push(i.pop() + 2), doc="Add 2")
        self.reg("2-", lambda i, t, n: i.push(i.pop() - 2), doc="Subtract 2")
        self.reg("2*", lambda i, t, n: i.push(i.pop_int() * 2), doc="Multiply by 2")
        self.reg("2/", lambda i, t, n: i.push(i.pop_int() >> 1), doc="Divide by 2 (shift right)")
        self.reg("S>D", lambda i, t, n: None, doc="Sign-extend to double (no-op for Python ints)")

        # ── PICK and ROLL ──
        def _pick(i, t, n):
            """PICK ( n -- item[n] )  Copy the nth item to top (0 = top)."""
            idx = i.pop_int()
            if idx < 0 or idx >= len(i.stack):
                raise ForthError(f"PICK: index {idx} out of range")
            i.push(i.stack[-1 - idx])
        self.reg("PICK", _pick, doc="Copy nth stack item to top")

        def _roll(i, t, n):
            """ROLL ( n -- )  Remove the nth item and place it on top (0 = top, no-op)."""
            idx = i.pop_int()
            if idx < 0 or idx >= len(i.stack):
                raise ForthError(f"ROLL: index {idx} out of range")
            if idx == 0:
                return
            item = i.stack.pop(-1 - idx)
            i.push(item)
        self.reg("ROLL", _roll, doc="Rotate nth stack item to top")

        # ── string printing (." immediate) ──
        def _dot_quote(i, t, n):
            # ." text" — compile/print a string at runtime.
            # The tokenizer handles "..." as string literals (starting with "),
            # so we expect the next token to be a quoted string.
            if n + 1 >= len(t):
                raise ForthError('." needs a string')
            s = t[n + 1]
            if not (s.startswith('"') and s.endswith('"') and len(s) >= 2):
                # Fallback: collect tokens until one ends with "
                parts = []
                j = n + 1
                while j < len(t):
                    tok = t[j]
                    if tok.endswith('"'):
                        parts.append(tok[:-1])
                        j += 1
                        break
                    parts.append(tok)
                    j += 1
                text = " ".join(parts)
            else:
                text = s[1:-1]
                j = n + 2
            if i.compiling:
                i.current_def.append(("lit", text))
                i.current_def.append(("call", "TYPE"))
            else:
                i.emit(text)
            return _NextIdx(j)
        self.reg('."', _dot_quote, immediate=True, doc='Print string at runtime')

        # ── CASE/ENDCASE/ENDOF (immediate compilation words) ──
        def _case(i, t, n):
            """CASE ( n -- )  Start a case statement."""
            i.return_stack.append(("case", 0))
            return n + 1
        self.reg("CASE", _case, immediate=True, doc="CASE statement")

        def _of(i, t, n):
            """OF ( test -- )  Compare top with case value; if equal, execute body."""
            # Stack at runtime: case_val test  → if equal, drop both and run body
            # We compile: OVER = IF DROP [body] DROP 0 ELSE DROP 1 THEN
            # Simpler: compile as if-then-else pattern
            i.current_def.append(["lit", "of-check"])
            # Actually, compile: OVER = IF DROP ... ELSE DROP ... THEN
            # Use a simpler approach: compile OVER = IF DROP (body) ELSE (skip) THEN
            i.current_def.append(["call", "OVER"])
            i.current_def.append(["call", "="])
            i.current_def.append(["if", None])
            i.return_stack.append(("of-fixup", len(i.current_def) - 1))
            i.current_def.append(["call", "DROP"])  # drop the case value
            return n + 1
        self.reg("OF", _of, immediate=True, doc="OF clause")

        def _endof(i, t, n):
            """ENDOF — end of an OF clause, jump past ENDCASE."""
            if not i.return_stack or i.return_stack[-1][0] != "of-fixup":
                raise ForthError("ENDOF without OF")
            if_pos = i.return_stack.pop()[1]
            # Emit jump past ENDCASE (will be fixed up)
            i.current_def.append(["jump", None])
            jump_pos = len(i.current_def) - 1
            # Fix up IF to skip to here (the ELSE part)
            i.current_def[if_pos][1] = len(i.current_def)
            # Push a new of-end-fixup to collect jumps
            if i.return_stack and i.return_stack[-1][0] == "case":
                i.return_stack[-1] = ("case", i.return_stack[-1][1] + 1)
            i.return_stack.append(("of-end-fixup", jump_pos))
            return n + 1
        self.reg("ENDOF", _endof, immediate=True, doc="ENDOF clause")

        def _endcase(i, t, n):
            """ENDCASE — end of case statement, drop the case value."""
            # Fix up all ENDOF jumps to point here
            while i.return_stack and i.return_stack[-1][0] == "of-end-fixup":
                pos = i.return_stack.pop()[1]
                i.current_def[pos][1] = len(i.current_def)
            # Pop the case marker
            if i.return_stack and i.return_stack[-1][0] == "case":
                i.return_stack.pop()
            # Drop the case value
            i.current_def.append(["call", "DROP"])
            return n + 1
        self.reg("ENDCASE", _endcase, immediate=True, doc="ENDCASE")

        # ── ARRAY support ──
        def _array(i, t, n):
            """ARRAY <name> <size> — create an array of given size."""
            if n + 2 >= len(t):
                raise ForthError("ARRAY needs name and size")
            name = t[n + 1].upper()
            try:
                size = int(t[n + 2])
            except ValueError:
                raise ForthError("ARRAY size must be a number")
            if size < 0:
                raise ForthError("ARRAY size must be non-negative")
            arr = [0] * size
            i.variables[name] = arr  # store list directly

            def _push_arr(i2, t2, n2, _name=name):
                i2.push(_name)
            i.define(Word(name=name, native=_push_arr, doc=f"array {name}[{size}]"))
            return _NextIdx(n + 3)
        self._defining_words["ARRAY"] = _array

        # ── array element access ──
        def _arr_store(i, t, n):
            """[]! ( val idx addr -- )  Store val at arr[idx]."""
            addr = i.pop()
            idx = i.pop_int()
            val = i.pop()
            if isinstance(addr, str) and addr in i.variables:
                arr = i.variables[addr]
                if isinstance(arr, list) and not isinstance(arr[0], list) if arr else True:
                    pass
                if idx < 0 or idx >= len(arr):
                    raise ForthError(f"array index {idx} out of range [0,{len(arr)})")
                arr[idx] = val
            else:
                raise ForthError(f"bad address: {addr}")
        self.reg("[]!", _arr_store, doc="Array store ( val idx addr -- )")

        def _arr_fetch(i, t, n):
            """[]@ ( idx addr -- val )  Fetch arr[idx]."""
            addr = i.pop()
            idx = i.pop_int()
            if isinstance(addr, str) and addr in i.variables:
                arr = i.variables[addr]
                if idx < 0 or idx >= len(arr):
                    raise ForthError(f"array index {idx} out of range [0,{len(arr)})")
                i.push(arr[idx])
            else:
                raise ForthError(f"bad address: {addr}")
        self.reg("[]@", _arr_fetch, doc="Array fetch ( idx addr -- val )")

        # ── SP@ (stack pointer) ──
        self.reg("SP@", lambda i, t, n: i.push(len(i.stack)), doc="Push stack depth")
        self.reg("SP!", lambda i, t, n: None, doc="Set stack pointer (no-op)")

        # ── misc ──
        self.reg("CELLS", lambda i, t, n: None, doc="Cell size (no-op, 1 cell = 1)")
        self.reg("CELL+", lambda i, t, n: i.push(i.pop() + 1), doc="Add 1 cell")
        self.reg("ALLOT", lambda i, t, n: i.pop(), doc="Allot memory (no-op)")

        # ── DUMP (hex dump of stack) ──
        def _dump(i, t, n):
            """DUMP ( -- )  Print stack contents in hex."""
            i.emit("<")
            for v in i.stack:
                if isinstance(v, int):
                    i.emit(f"{v:#x} ")
                else:
                    i.emit(f"{v} ")
            i.emit(">")
        self.reg("DUMP", _dump, doc="Hex dump of stack")

    # ─── REPL ──────────────────────────────────────────────────────────────
    def repl(self, input_stream=None) -> None:
        """Run an interactive Read-Eval-Print Loop."""
        inp = input_stream if input_stream is not None else sys.stdin
        self.emit_line("Forth Interpreter v2.0 — type BYE to exit, WORDS for word list")
        while True:
            self.emit("ok ")
            try:
                line = inp.readline()
                if not line:
                    break
                self.eval(line)
            except ForthError as e:
                self.emit_line(f"? {e}")
                self._reset_state()
            except SystemExit:
                break
            except KeyboardInterrupt:
                self.emit_line("\ninterrupted")
                self._reset_state()

    def _reset_state(self) -> None:
        """Reset interpreter state after an error."""
        self.stack.clear()
        self.compiling = False
        self.current_def = []
        self.return_stack.clear()


# ─── CLI entry point ──────────────────────────────────────────────────────
def main() -> None:
    """Command-line entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Forth interpreter")
    parser.add_argument("-e", "--eval", metavar="CODE", help="evaluate code string")
    parser.add_argument("-f", "--file", metavar="FILE", help="execute file")
    parser.add_argument("-i", "--interactive", action="store_true", help="start REPL")
    args = parser.parse_args()

    interp = ForthInterpreter()
    if args.eval:
        try:
            interp.eval(args.eval)
        except ForthError as e:
            print(f"? {e}", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        with open(args.file) as f:
            try:
                interp.eval(f.read())
            except ForthError as e:
                print(f"? {e}", file=sys.stderr)
                sys.exit(1)
    elif args.interactive or not (args.eval or args.file):
        interp.repl()


if __name__ == "__main__":
    main()