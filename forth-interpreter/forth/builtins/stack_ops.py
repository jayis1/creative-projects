"""Stack manipulation words: DUP, DROP, SWAP, OVER, ROT, PICK, ROLL, etc."""

from forth.core import ForthError


def register_stack_ops(i) -> None:
    """Register stack-manipulation words on *i*."""

    # ── basic stack ops ──
    i.reg("DUP", lambda i, t, n: i.push(i.peek()), doc="Duplicate top")
    i.reg("DROP", lambda i, t, n: i.pop(), doc="Remove top")
    i.reg("?DUP", lambda i, t, n: i.push(i.peek()) if i.peek() != 0 else None, doc="Dup if nonzero")

    def _swap(i, t, n):
        a, b = i.pop(), i.pop()
        i.push(a)
        i.push(b)
    i.reg("SWAP", _swap, doc="Swap top two")

    def _over(i, t, n):
        if len(i.stack) < 2:
            raise ForthError("OVER needs 2 items")
        i.push(i.stack[-2])
    i.reg("OVER", _over, doc="Copy second to top")

    def _rot(i, t, n):
        if len(i.stack) < 3:
            raise ForthError("ROT needs 3 items")
        c = i.stack.pop()
        b = i.stack.pop()
        a = i.stack.pop()
        i.push(b)
        i.push(c)
        i.push(a)
    i.reg("ROT", _rot, doc="Rotate top three")

    def _minus_rot(i, t, n):
        if len(i.stack) < 3:
            raise ForthError("-ROT needs 3 items")
        c = i.stack.pop()
        b = i.stack.pop()
        a = i.stack.pop()
        i.push(c)
        i.push(a)
        i.push(b)
    i.reg("-ROT", _minus_rot, doc="Rotate top three (reverse)")

    def _nip(i, t, n):
        if len(i.stack) < 2:
            raise ForthError("NIP needs 2 items")
        i.stack.pop(-2)
    i.reg("NIP", _nip, doc="Remove second item")

    def _tuck(i, t, n):
        if len(i.stack) < 2:
            raise ForthError("TUCK needs 2 items")
        top = i.stack[-1]
        i.stack.insert(-2, top)
    i.reg("TUCK", _tuck, doc="Dup top, insert under second")

    i.reg("DEPTH", lambda i, t, n: i.push(len(i.stack)), doc="Push stack depth")

    # ── double stack ops ──
    def _2dup(i, t, n):
        if len(i.stack) < 2:
            raise ForthError("2DUP needs 2 items")
        i.stack.append(i.stack[-2])
        i.stack.append(i.stack[-2])
    i.reg("2DUP", _2dup, doc="Duplicate top two items")

    def _2drop(i, t, n):
        i.pop()
        i.pop()
    i.reg("2DROP", _2drop, doc="Remove top two items")

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
    i.reg("2SWAP", _2swap, doc="Swap top two pairs")

    def _2over(i, t, n):
        if len(i.stack) < 4:
            raise ForthError("2OVER needs 4 items")
        i.push(i.stack[-4])
        i.push(i.stack[-4])
    i.reg("2OVER", _2over, doc="Copy third/fourth to top")

    # ── return stack ──
    def _to_r(i, t, n):
        i.return_stack.append(i.pop())
    i.reg(">R", _to_r, doc="Push to return stack")

    def _r_from(i, t, n):
        if not i.return_stack:
            raise ForthError("return stack underflow")
        i.push(i.return_stack.pop())
    i.reg("R>", _r_from, doc="Pop from return stack")

    def _r_fetch(i, t, n):
        if not i.return_stack:
            raise ForthError("return stack underflow")
        i.push(i.return_stack[-1])
    i.reg("R@", _r_fetch, doc="Copy return stack top")

    # ── PICK and ROLL ──
    def _pick(i, t, n):
        """PICK ( n -- item[n] )  Copy the nth item to top (0 = top)."""
        idx = i.pop_int()
        if idx < 0 or idx >= len(i.stack):
            raise ForthError(f"PICK: index {idx} out of range")
        i.push(i.stack[-1 - idx])
    i.reg("PICK", _pick, doc="Copy nth stack item to top")

    def _roll(i, t, n):
        """ROLL ( n -- )  Remove the nth item and place it on top (0 = top, no-op)."""
        idx = i.pop_int()
        if idx < 0 or idx >= len(i.stack):
            raise ForthError(f"ROLL: index {idx} out of range")
        if idx == 0:
            return
        item = i.stack.pop(-1 - idx)
        i.push(item)
    i.reg("ROLL", _roll, doc="Rotate nth stack item to top")

    # ── WITHIN: test if n is within lo <= n < hi ──
    def _within(i, t, n):
        """WITHIN ( n lo hi -- flag )  True if lo <= n < hi."""
        hi = i.pop()
        lo = i.pop()
        val = i.pop()
        i.push(-1 if (lo <= val < hi) else 0)
    i.reg("WITHIN", _within, doc="Test if n is in [lo, hi)")

    # ── BOUNDS: convert ( addr len -- addr+len addr ) for loop idioms ──
    def _bounds(i, t, n):
        """BOUNDS ( addr len -- addr+len addr )"""
        length = i.pop_int()
        addr = i.pop()
        i.push(addr)
        i.push(length)
    i.reg("BOUNDS", _bounds, doc="Convert to address range")