"""PostScript objects and the operand/execution stacks.

PostScript objects can be:
  - number (int or float)
  - string  (Python str, latin-1 bytes under the hood)
  - name    (a Name instance - executable vs literal)
  - boolean (True/False)
  - array   (list)
  - dict    (PSDict - a chained dictionary)
  - procedure (a Proc object wrapping a list of objects)
  - operator (a Python callable with name)
  - font    (a dict-like PSFont)
  - file    (a file-like wrapper)
  - null    (None sentinel)
  - mark    (Mark sentinel for [ ... ] and { ... })
"""

from .errors import PSTypeError, PSStackUnderflow, PSRangeCheck


# Sentinel objects
class _Mark:
    __slots__ = ()
    _inst = None
    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst
    def __repr__(self):
        return "mark"

MARK = _Mark()


class _Null:
    __slots__ = ()
    _inst = None
    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst
    def __repr__(self):
        return "null"

NULL = _Null()


class Name:
    """A PostScript name (symbol). `literal` True means /name (pushed, not executed)."""
    __slots__ = ("value", "literal")
    def __init__(self, value: str, literal: bool = False):
        self.value = value
        self.literal = literal
    def __repr__(self):
        return f"Name({'/' if self.literal else ''}{self.value})"
    def __eq__(self, other):
        return isinstance(other, Name) and self.value == other.value and self.literal == other.literal
    def __hash__(self):
        return hash((self.value, self.literal))


class Proc:
    """A PostScript procedure body { ... } - a deferred list of objects."""
    __slots__ = ("body",)
    def __init__(self, body: list):
        self.body = body
    def __repr__(self):
        return "{...}" if self.body else "{}"
    def __eq__(self, other):
        return isinstance(other, Proc) and self.body is other.body
    def __hash__(self):
        return id(self)


class Operator:
    """A built-in operator implemented as a Python callable."""
    __slots__ = ("name", "fn", "arity")
    def __init__(self, name: str, fn, arity=None):
        self.name = name
        self.fn = fn
        self.arity = arity  # for documentation; not enforced
    def __repr__(self):
        return f"--{self.name}--"
    def __call__(self, interp):
        return self.fn(interp)


class PSDict:
    """A PostScript dictionary with parent chaining (dictstack)."""
    __slots__ = ("data", "parent", "writable", "size_limit")
    def __init__(self, data=None, parent=None, writable=True, size_limit=None):
        self.data = dict(data) if data else {}
        self.parent = parent
        self.writable = writable
        self.size_limit = size_limit
    def get(self, key, default=None):
        node = self
        while node is not None:
            if key in node.data:
                return node.data[key]
            node = node.parent
        return default
    def __contains__(self, key):
        node = self
        while node is not None:
            if key in node.data:
                return True
            node = node.parent
        return False
    def put(self, key, value):
        if not self.writable:
            from .errors import PSInvalidAccess
            raise PSInvalidAccess(f"Dictionary is read-only")
        if self.size_limit is not None and key not in self.data and len(self.data) >= self.size_limit:
            from .errors import PSVMError
            raise PSVMError("Dictionary full")
        self.data[key] = value
    def put_all(self, items):
        for k, v in items.items():
            self.put(k, v)
    def keys(self):
        return list(self.data.keys())
    def values(self):
        return list(self.data.values())
    def items(self):
        return list(self.data.items())
    def __len__(self):
        return len(self.data)
    def copy(self):
        return PSDict(dict(self.data), self.parent, self.writable, self.size_limit)


class PSArray:
    """A PostScript array (supports get/put with bounds checking)."""
    __slots__ = ("data", "writable", "offset", "length")
    def __init__(self, data=None, writable=True, offset=0, length=None):
        self.data = list(data) if data else []
        self.writable = writable
        self.offset = offset
        self.length = length if length is not None else len(self.data)
    def get(self, i):
        if i < 0 or i >= self.length:
            raise PSRangeCheck(f"Array index {i} out of range (len={self.length})")
        return self.data[self.offset + i]
    def put(self, i, val):
        if not self.writable:
            from .errors import PSInvalidAccess
            raise PSInvalidAccess("Array is read-only")
        if i < 0 or i >= self.length:
            raise PSRangeCheck(f"Array index {i} out of range (len={self.length})")
        self.data[self.offset + i] = val
    def __len__(self):
        return self.length
    def __iter__(self):
        for i in range(self.length):
            yield self.data[self.offset + i]
    def __repr__(self):
        return f"[{' '.join(repr(x) for x in self)}]"
    def copy(self):
        return PSArray(list(self), self.writable)


class PSFile:
    """Wraps a Python file-like object."""
    __slots__ = ("file", "readable", "writable", "closed")
    def __init__(self, file, readable=True, writable=False):
        self.file = file
        self.readable = readable
        self.writable = writable
        self.closed = False
    def read(self, n=-1):
        if not self.readable:
            from .errors import PSInvalidAccess
            raise PSInvalidAccess("File not readable")
        return self.file.read(n)
    def write(self, s):
        if not self.writable:
            from .errors import PSInvalidAccess
            raise PSInvalidAccess("File not writable")
        return self.file.write(s)
    def close(self):
        if not self.closed:
            self.file.close()
            self.closed = True
    def readline(self):
        if not self.readable:
            from .errors import PSInvalidAccess
            raise PSInvalidAccess("File not readable")
        return self.file.readline()


# --- Stack helpers -------------------------------------------------------
def pop(stack, n=1, expected_type=None):
    """Pop n items; raise PSStackUnderflow if not enough."""
    if len(stack) < n:
        raise PSStackUnderflow(f"stack underflow (needed {n}, have {len(stack)})")
    if n == 1:
        v = stack.pop()
        if expected_type is not None and not isinstance(v, expected_type):
            raise PSTypeError(f"Expected {expected_type.__name__}, got {type(v).__name__}")
        return v
    items = stack[-n:] if n else []
    del stack[len(stack) - n:]
    if expected_type is not None:
        for it in items:
            if not isinstance(it, expected_type):
                raise PSTypeError(f"Expected {expected_type.__name__}, got {type(it).__name__}")
    return items


def pop_number(stack):
    v = pop(stack)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    raise PSTypeError(f"Expected number, got {type(v).__name__}")


def pop_int(stack):
    v = pop(stack)
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    raise PSTypeError(f"Expected integer, got {type(v).__name__}")


def pop_string(stack):
    v = pop(stack)
    if isinstance(v, str):
        return v
    raise PSTypeError(f"Expected string, got {type(v).__name__}")


def pop_bool(stack):
    v = pop(stack)
    if isinstance(v, bool):
        return v
    raise PSTypeError(f"Expected boolean, got {type(v).__name__}")


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)