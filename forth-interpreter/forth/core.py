"""
Core Forth interpreter data structures and execution engine.

This module contains the fundamental building blocks of the Forth interpreter:
  - :class:`ForthError` / :class:`ForthThrow` — exception types
  - :class:`Word` — a dictionary entry (native callable or compiled body)
  - :class:`ForthInterpreter` — the stack machine that compiles and executes Forth code

The interpreter supports:
  * Integer and float arithmetic
  * Full stack-manipulation word set
  * Variables, constants, values, and arrays
  * Colon definitions compiled to a bytecode-like IR
  * Control flow: IF/ELSE/THEN, BEGIN/UNTIL, BEGIN/WHILE/REPEAT, AGAIN,
    DO/LOOP, DO/+LOOP, LEAVE, EXIT, RECURSE, CASE/OF/ENDOF/ENDCASE
  * String literals and output
  * Memory operations (!, @, +!, []!, []@)
  * Bitwise operations
  * Exception handling (CATCH/THROW)
  * File inclusion (INCLUDE)
  * Configurable stack and recursion limits
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("forth")


# ─── Exceptions ──────────────────────────────────────────────────────────────

class ForthError(Exception):
    """Raised on Forth-level errors (stack underflow, unknown word, etc.)."""


class ForthThrow(ForthError):
    """Raised by THROW to propagate a Forth-level exception code.

    The ``code`` attribute holds the numeric throw code and ``message``
    holds an optional human-readable description.
    """

    def __init__(self, code: int, message: str = "") -> None:
        super().__init__(message or f"THROW {code}")
        self.code = code
        self.message = message


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


# ─── Word ────────────────────────────────────────────────────────────────────

class Word:
    """A Forth word definition (dictionary entry).

    Parameters
    ----------
    name : str
        The word name (stored upper-cased).
    immediate : bool
        If ``True``, the word executes during compilation instead of being
        compiled.
    data : list | None
        Compiled instruction list for user-defined words.
    native : callable | None
        Python callable for built-in words — signature ``(interp, tokens, idx)``.
    doc : str
        Short documentation string shown by ``WORDS`` / ``SEE``.
    hidden : bool
        If ``True``, the word is excluded from ``WORDS`` output.
    """

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


# Type alias for native word functions: (interpreter, tokens, token_index) -> Any
NativeFn = Callable[["ForthInterpreter", List[str], int], Any]


# ─── Instruction tags ─────────────────────────────────────────────────────────
# These constants make the IR easier to read and grep than bare strings.
LIT = "lit"
CALL = "call"
IF = "if"
JUMP = "jump"
UNTIL = "until"
WHILE = "while"
DO = "do"
LOOP = "loop"
PLUSLOOP = "plusloop"
LEAVE = "leave"


# ─── Interpreter ──────────────────────────────────────────────────────────────

class ForthInterpreter:
    """The core Forth interpreter / compiler / execution engine.

    Parameters
    ----------
    output : writable stream | None
        Where ``.``, ``EMIT``, ``CR`` etc. write. Defaults to ``sys.stdout``.
    max_recursion : int
        Maximum call depth for user-defined words (prevents Python stack
        overflow).  Default 500.
    max_stack : int
        Maximum data-stack depth.  Pushing beyond this raises ``ForthError``.
        Default 10 000.
    """

    def __init__(
        self,
        output: Optional[Any] = None,
        max_recursion: int = 500,
        max_stack: int = 10_000,
    ) -> None:
        self.stack: List[Any] = []
        self.return_stack: List[Any] = []
        self.words: Dict[str, Word] = {}
        self.output = output if output is not None else sys.stdout
        self.compiling: bool = False
        self.current_def: List[Any] = []
        self.current_name: str = ""
        self.variables: Dict[str, List[Any]] = {}
        self._defining_words: Dict[str, NativeFn] = {}
        self._recursion_depth: int = 0
        self.max_recursion: int = max_recursion
        self.max_stack: int = max_stack
        self._register_builtins()

    # ─── output ──────────────────────────────────────────────────────────────
    def emit(self, s: str) -> None:
        self.output.write(s)

    def emit_line(self, s: str = "") -> None:
        self.output.write(s + "\n")

    # ─── stack helpers ───────────────────────────────────────────────────────
    def push(self, v: Any) -> None:
        if len(self.stack) >= self.max_stack:
            raise ForthError(f"stack overflow (max {self.max_stack})")
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

    # ─── word registry ───────────────────────────────────────────────────────
    def define(self, word: Word) -> None:
        self.words[word.name.upper()] = word

    def lookup(self, name: str) -> Optional[Word]:
        return self.words.get(name.upper())

    def reg(self, name: str, fn: NativeFn, immediate: bool = False, doc: str = "") -> None:
        self.define(Word(name=name.upper(), native=fn, immediate=immediate, doc=doc))

    # ─── tokenisation ────────────────────────────────────────────────────────
    @staticmethod
    def tokenize(source: str) -> List[str]:
        """Split source into tokens.

        Handles ``\\`` line comments, ``( ... )`` block comments, and
        ``"..."`` string literals.  String literals are returned as a single
        token including the surrounding quotes.

        Special handling for ``."`` ``C"`` ``ABORT"`` and ``.(`` — these
        consume text until the next ``"`` or ``)`` respectively, even if
        it contains spaces.
        """
        tokens: List[str] = []
        i, n = 0, len(source)
        while i < n:
            c = source[i]
            if c.isspace():
                i += 1
                continue
            # \ line comment — only when \ is at start or preceded by whitespace
            if c == "\\" and (i == 0 or source[i - 1].isspace()):
                while i < n and source[i] != "\n":
                    i += 1
                continue
            # ( ... ) block comment (supports nesting)
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
            # "..." string literal → single token including quotes
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

            # Check for special words that consume text: ." C" ABORT" .(
            # We need to check these BEFORE the regular token reader
            # because they contain " or ( characters.
            # Check ."
            # ." reads text until the next " as the string content.
            # The " in ." is part of the word name, not the string delimiter.
            if source[i:i + 2] == '."':
                tokens.append('."')
                i += 2
                # Skip whitespace
                while i < n and source[i].isspace():
                    i += 1
                # Read until closing " — this IS the string content
                k = i
                buf2: List[str] = []
                while k < n and source[k] != '"':
                    buf2.append(source[k])
                    k += 1
                if k >= n:
                    # No closing " found — treat rest of line as string
                    tokens.append('"' + "".join(buf2).rstrip() + '"')
                    i = k
                else:
                    tokens.append('"' + "".join(buf2) + '"')
                    i = k + 1  # skip closing "
                continue
            # Check C"
            # C" reads text until the next " as a counted string.
            if source[i:i + 2] == 'C"':
                tokens.append('C"')
                i += 2
                while i < n and source[i].isspace():
                    i += 1
                k = i
                buf2: List[str] = []
                while k < n and source[k] != '"':
                    buf2.append(source[k])
                    k += 1
                if k >= n:
                    tokens.append('"' + "".join(buf2).rstrip() + '"')
                    i = k
                else:
                    tokens.append('"' + "".join(buf2) + '"')
                    i = k + 1
                continue
            # Check ABORT"
            if source[i:i + 6] == 'ABORT"':
                tokens.append('ABORT"')
                i += 6
                while i < n and source[i].isspace():
                    i += 1
                k = i
                buf2: List[str] = []
                while k < n and source[k] != '"':
                    buf2.append(source[k])
                    k += 1
                if k >= n:
                    tokens.append('"' + "".join(buf2).rstrip() + '"')
                    i = k
                else:
                    tokens.append('"' + "".join(buf2) + '"')
                    i = k + 1
                continue
            # Check .( — immediate output until )
            if source[i:i + 2] == '.(':
                tokens.append('.(')
                i += 2
                # Skip whitespace
                while i < n and source[i].isspace():
                    i += 1
                # Read until )
                k = i
                buf2: List[str] = []
                while k < n and source[k] != ')':
                    buf2.append(source[k])
                    k += 1
                tokens.append(''.join(buf2).strip())
                i = k + 1  # skip the )
                continue

            # Regular token: read until whitespace
            j = i
            while j < n and not source[j].isspace():
                j += 1
            tokens.append(source[i:j])
            i = j
        return tokens

    # ─── number parsing ──────────────────────────────────────────────────────
    @staticmethod
    def parse_number(tok: str) -> Optional[Any]:
        """Try to parse *tok* as an int or float; return ``None`` on failure."""
        try:
            return int(tok)
        except ValueError:
            pass
        try:
            return float(tok)
        except ValueError:
            pass
        return None

    # ─── main eval ───────────────────────────────────────────────────────────
    def eval(self, source: str) -> None:
        """Tokenize and evaluate *source*.

        Raises :class:`ForthError` on any error; the interpreter state is
        reset via :meth:`_reset_state` before the exception propagates.
        """
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

    # ─── execution mode ──────────────────────────────────────────────────────
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

        # defining words that consume the next token(s)
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
                # Only _NextIdx signals "jump the token pointer".
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

    # ─── compilation mode ─────────────────────────────────────────────────────
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
            self.current_def.append((LIT, num))
            return idx + 1

        # string literal → compile as LIT
        if tok.startswith('"') and tok.endswith('"'):
            self.current_def.append((LIT, tok[1:-1]))
            return idx + 1

        # regular word → compile as CALL
        if word is not None:
            self.current_def.append((CALL, word.name))
            return idx + 1

        raise ForthError(f"unknown word in definition: {tok}")

    # ─── execute a compiled body ─────────────────────────────────────────────
    def _execute_body(self, body: List[Any]) -> None:
        """Execute compiled instructions with control-flow support."""
        self._recursion_depth += 1
        if self._recursion_depth > self.max_recursion:
            self._recursion_depth -= 1
            raise ForthError(f"recursion limit exceeded (max {self.max_recursion})")
        ip = 0
        try:
            while ip < len(body):
                instr = body[ip]
                tag = instr[0]

                if tag == LIT:
                    self.push(instr[1])
                elif tag == CALL:
                    w = self.lookup(instr[1])
                    if w is None:
                        raise ForthError(f"undefined word: {instr[1]}")
                    if w.native is not None:
                        w.native(self, [], 0)
                    else:
                        self._execute_body(w.data)
                elif tag == IF:
                    flag = self.pop()
                    if flag == 0:
                        ip = instr[1]
                        continue
                elif tag == JUMP:
                    ip = instr[1]
                    continue
                elif tag == UNTIL:
                    flag = self.pop()
                    if flag == 0:
                        ip = instr[1]
                        continue
                elif tag == WHILE:
                    flag = self.pop()
                    if flag == 0:
                        ip = instr[1]
                        continue
                elif tag == DO:
                    start = self.pop()
                    limit = self.pop()
                    self.return_stack.append(["loop-state", start, limit])
                elif tag == LOOP:
                    state = self._find_loop_state()
                    if state is None:
                        raise ForthError("LOOP without DO")
                    state[1] += 1
                    if state[1] < state[2]:
                        ip = instr[1]
                        continue
                    else:
                        self._pop_loop_state()
                elif tag == PLUSLOOP:
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
                elif tag == LEAVE:
                    self._pop_loop_state()
                    ip = instr[1]
                    continue
                else:
                    raise ForthError(f"bad instruction: {instr}")

                ip += 1
        except _ExitBody:
            pass
        finally:
            self._recursion_depth -= 1

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

    # ─── reset ───────────────────────────────────────────────────────────────
    def _reset_state(self) -> None:
        """Reset interpreter state after an error."""
        self.stack.clear()
        self.compiling = False
        self.current_def = []
        self.current_name = ""
        self.return_stack.clear()
        self._recursion_depth = 0

    # ─── builtins registration (delegated to builtins package) ────────────────
    def _register_builtins(self) -> None:
        """Register all built-in words.

        Delegates to the :mod:`forth.builtins` package which splits the
        word set into logical groups.
        """
        from forth.builtins import register_all
        register_all(self)