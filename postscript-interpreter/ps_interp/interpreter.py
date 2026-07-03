"""PostScript interpreter core.

Executes the token stream from the scanner, maintaining:
  - operand stack
  - dictionary stack (userdict on top of systemdict)
  - execution stack (for procedures and loops)
  - graphics state stack

Implements ~180 built-in operators covering arithmetic, stack manipulation,
control flow, dictionary, array, string, relational, path, and painting
operations.  See PLRM for semantics.
"""

import io
import math
import os
import struct
import sys
from .scanner import tokenize, Token
from .objects import (Name, Proc, Operator, PSDict, PSArray, PSFile,
                      MARK, NULL, pop, pop_number, pop_int, pop_string,
                      pop_bool, is_number)
from .graphics import (GraphicsState, Canvas, Matrix, Path, gray_to_rgb)
from .errors import (PSError, PSStackUnderflow, PSTypeError, PSUndefined,
                     PSRangeCheck, PSInvalidAccess, PSSyntaxError, PSVMError)


# --- Sentinel for 'exit' from loops ---
class _ExitLoop(Exception):
    pass


class _StopExecution(Exception):
    """Raised by 'stop' to unwind to nearest stopped context."""
    def __init__(self, product=None):
        self.product = product


class Interpreter:
    """The PostScript interpreter."""
    MAX_STACK = 100000
    MAX_EXEC_DEPTH = 200
    MAX_DICTS = 20
    VM_LIMIT = 20 * 1024 * 1024  # 20 MB pseudo-VM limit

    def __init__(self, canvas_width=612, canvas_height=792, output=None,
                 strict=False):
        self.operand_stack = []
        self.exec_stack = []
        self.dict_stack = []
        self.graphics_stack = []
        self.gstate = GraphicsState()
        self.canvas = Canvas(canvas_width, canvas_height)
        self.page_height = canvas_height
        self.strict = strict
        self.output = output if output is not None else sys.stdout
        self.vm_used = 0
        self.in_stopped = 0  # depth of stopped contexts
        self.exit_pending = False
        self.quit_flag = False
        self.random_state = 0
        self.errordict = None
        self._init_dicts()
        self._cmd_cache = {}

    # --- VM accounting ---
    def vmalloc(self, n):
        if self.vm_used + n > self.VM_LIMIT:
            raise PSVMError("VM exhausted")
        self.vm_used += n

    # --- Dictionary stack ---
    def _init_dicts(self):
        self.systemdict = PSDict(writable=False)
        self.globaldict = PSDict(writable=True)
        self.userdict = PSDict(writable=True)
        self.dict_stack = [self.systemdict, self.globaldict, self.userdict]
        self._register_builtins()

    def lookup(self, name: str):
        """Look up a name in the dict stack (top-down)."""
        for d in reversed(self.dict_stack):
            if name in d:
                return d.data.get(name)
        return None

    def where(self, name: str):
        """Return the dictionary containing name, or None."""
        for d in reversed(self.dict_stack):
            if name in d:
                return d
        return None

    def define(self, name: str, value):
        """Define a name in the topmost writable dictionary."""
        # find topmost writable dict
        for d in reversed(self.dict_stack):
            if d.writable:
                d.put(name, value)
                return
        # fall back to userdict
        self.userdict.put(name, value)

    # --- Stack operations ---
    def push(self, v):
        if len(self.operand_stack) >= self.MAX_STACK:
            raise PSVMError("Operand stack overflow")
        self.operand_stack.append(v)

    def opop(self):
        if not self.operand_stack:
            raise PSStackUnderflow("stack underflow")
        return self.operand_stack.pop()

    # --- Execution ---
    def run(self, src: str, filename=None):
        """Tokenize and execute a PostScript source string."""
        toks = list(tokenize(src))
        objs = self._parse_tokens(toks)
        try:
            self._execute_list(objs)
        except _StopExecution:
            pass
        return self

    def run_file(self, path: str):
        with open(path, 'r', encoding='latin-1') as f:
            src = f.read()
        return self.run(src, path)

    def _parse_tokens(self, toks):
        """Convert tokens to PS objects, building Proc bodies and arrays."""
        result = []
        i = 0
        n = len(toks)
        while i < n:
            tok = toks[i]
            i += 1
            if tok.kind == 'eof':
                break
            obj = self._token_to_object(tok, toks, i - 1)
            if obj is _SKIP:
                continue
            # Check if it's a tuple meaning (new_i, list_of_objs)
            if isinstance(obj, tuple):
                i = obj[0]
                result.extend(obj[1])
                continue
            result.append(obj)
        return result

    def _token_to_object(self, tok, toks, idx):
        k = tok.kind
        if k == 'number':
            return tok.value
        if k == 'string':
            return tok.value
        if k == 'name_literal':
            return Name(tok.value, literal=True)
        if k == 'name':
            return Name(tok.value, literal=False)
        if k == 'lbracket':
            return self._parse_array(toks, idx + 1)
        if k == 'proc_open':
            return self._parse_proc(toks, idx + 1)
        if k in ('dict_open',):
            return self._parse_dict_literal(toks, idx + 1)
        if k in ('rbracket', 'proc_close', 'dict_close'):
            raise PSSyntaxError(f"Unexpected {tok.value}")
        raise PSSyntaxError(f"Unknown token kind: {k}")

    def _parse_array(self, toks, start):
        items = []
        i = start
        while i < len(toks):
            tok = toks[i]
            if tok.kind == 'rbracket':
                return (i + 1, items)  # caller will extend
            if tok.kind == 'eof':
                raise PSSyntaxError("Unterminated array")
            if tok.kind == 'lbracket':
                sub = self._parse_array(toks, i + 1)
                i = sub[0]
                items.append(PSArray(sub[1]))
                continue
            if tok.kind == 'proc_open':
                sub = self._parse_proc(toks, i + 1)
                i = sub[0]
                items.append(sub[1])
                continue
            if tok.kind == 'dict_open':
                sub = self._parse_dict_literal(toks, i + 1)
                i = sub[0]
                items.append(sub[1])
                continue
            obj = self._token_to_object(tok, toks, i)
            if obj is _SKIP:
                i += 1
                continue
            if isinstance(obj, tuple):
                i = obj[0]
                items.extend(obj[1])
                continue
            items.append(obj)
            i += 1
        raise PSSyntaxError("Unterminated array")

    def _parse_proc(self, toks, start):
        body = []
        i = start
        depth = 1
        while i < len(toks):
            tok = toks[i]
            if tok.kind == 'proc_open':
                depth += 1
                body.append(Name('{', literal=False))  # placeholder - reparse
                # Actually, recursively parse
                sub = self._parse_proc(toks, i + 1)
                i = sub[0]
                body.append(sub[1])
                continue
            if tok.kind == 'proc_close':
                depth -= 1
                if depth == 0:
                    return (i + 1, Proc(body))
                body.append(tok.value)
                i += 1
                continue
            if tok.kind == 'eof':
                raise PSSyntaxError("Unterminated procedure")
            if tok.kind == 'lbracket':
                sub = self._parse_array(toks, i + 1)
                i = sub[0]
                body.append(PSArray(sub[1]))
                continue
            if tok.kind == 'dict_open':
                sub = self._parse_dict_literal(toks, i + 1)
                i = sub[0]
                body.append(sub[1])
                continue
            obj = self._token_to_object(tok, toks, i)
            if obj is _SKIP:
                i += 1
                continue
            if isinstance(obj, tuple):
                i = obj[0]
                body.extend(obj[1])
                continue
            body.append(obj)
            i += 1
        raise PSSyntaxError("Unterminated procedure")

    def _parse_dict_literal(self, toks, start):
        items = []
        i = start
        while i < len(toks):
            tok = toks[i]
            if tok.kind == 'dict_close':
                d = PSDict()
                for j in range(0, len(items) - 1, 2):
                    key = items[j]
                    val = items[j + 1]
                    if isinstance(key, Name):
                        key = key.value
                    d.put(key, val)
                return (i + 1, d)
            if tok.kind == 'eof':
                raise PSSyntaxError("Unterminated dict literal")
            if tok.kind == 'proc_open':
                sub = self._parse_proc(toks, i + 1)
                i = sub[0]
                items.append(sub[1])
                continue
            if tok.kind == 'lbracket':
                sub = self._parse_array(toks, i + 1)
                i = sub[0]
                items.append(PSArray(sub[1]))
                continue
            if tok.kind == 'dict_open':
                sub = self._parse_dict_literal(toks, i + 1)
                i = sub[0]
                items.append(sub[1])
                continue
            obj = self._token_to_object(tok, toks, i)
            if obj is _SKIP:
                i += 1
                continue
            if isinstance(obj, tuple):
                i = obj[0]
                items.extend(obj[1])
                continue
            items.append(obj)
            i += 1
        raise PSSyntaxError("Unterminated dict literal")

    def _execute_list(self, objs):
        """Execute a list of objects sequentially."""
        for obj in objs:
            if self.quit_flag:
                return
            self._execute_one(obj)

    def _execute_one(self, obj):
        """Execute a single object."""
        if isinstance(obj, Name):
            if obj.literal:
                self.push(obj)
                return
            # Executable name: look up and execute
            val = self.lookup(obj.value)
            if val is None:
                raise PSUndefined(f"/{obj.value} is undefined")
            self._execute_one(val)
            return
        if isinstance(obj, Proc):
            self._execute_list(obj.body)
            return
        if isinstance(obj, Operator):
            obj(self)
            return
        # Literals (number, string, bool, array, dict) get pushed
        self.push(obj)

    # --- Error handling ---
    def handle_error(self, opname, exc):
        """Push the error name and call errordict handler if available."""
        errname = type(exc).__name__.replace('PS', '').lower()
        # Clear operand stack per PLRM
        self.operand_stack.clear()
        self.push(Name(errname, literal=True))
        self.push(Name(opname, literal=True))
        handler = None
        if self.errordict and errname in self.errordict:
            handler = self.errordict.data.get(errname)
        if handler is not None:
            try:
                self._execute_one(handler)
            except Exception:
                pass
        else:
            raise exc

    # --- Builtin registration ---
    def _reg(self, name, fn):
        self.systemdict.data[name] = Operator(name, fn)

    def _register_builtins(self):
        # Called after dicts are set up
        from .builtins import register_all
        register_all(self)


_SKIP = object()