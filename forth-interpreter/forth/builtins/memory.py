"""Memory words: !, @, +!, CELLS, CELL+, ALLOT, ERASE, FILL, MOVE."""

from forth.core import ForthError


def register_memory_ops(i) -> None:
    """Register memory and variable-access words on *i*."""

    def _store(i, t, n):
        addr = i.pop()
        val = i.pop()
        if isinstance(addr, str) and addr in i.variables:
            cell = i.variables[addr]
            if isinstance(cell, list) and len(cell) == 1:
                cell[0] = val
            elif isinstance(cell, list) and len(cell) != 1:
                raise ForthError(f"{addr} is an array; use []!")
            else:
                raise ForthError(f"bad variable: {addr}")
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("!", _store, doc="Store ( val addr -- )")

    def _fetch(i, t, n):
        addr = i.pop()
        if isinstance(addr, str) and addr in i.variables:
            cell = i.variables[addr]
            if isinstance(cell, list) and len(cell) == 1:
                i.push(cell[0])
            elif isinstance(cell, list) and len(cell) != 1:
                raise ForthError(f"{addr} is an array; use []@")
            else:
                raise ForthError(f"bad variable: {addr}")
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("@", _fetch, doc="Fetch ( addr -- val )")

    def _plus_store(i, t, n):
        addr = i.pop()
        val = i.pop()
        if isinstance(addr, str) and addr in i.variables:
            cell = i.variables[addr]
            if isinstance(cell, list) and len(cell) == 1:
                cell[0] += val
            else:
                raise ForthError(f"{addr} is not a scalar variable")
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("+!", _plus_store, doc="Add to stored ( n addr -- )")

    # ── SP@ (stack pointer) ──
    i.reg("SP@", lambda i, t, n: i.push(len(i.stack)), doc="Push stack depth")
    i.reg("SP!", lambda i, t, n: None, doc="Set stack pointer (no-op)")

    # ── cell-related (mostly no-ops in this model) ──
    i.reg("CELLS", lambda i, t, n: None, doc="Cell size (no-op, 1 cell = 1)")
    i.reg("CELL+", lambda i, t, n: i.push(i.pop() + 1), doc="Add 1 cell")
    i.reg("ALLOT", lambda i, t, n: i.pop(), doc="Allot memory (no-op)")

    # ── ERASE ( addr len -- )  Fill *len* cells of array *addr* with 0
    # addr is deeper, len is on top
    def _erase(i, t, n):
        length = i.pop_int()
        addr = i.pop()
        if isinstance(addr, str) and addr in i.variables:
            arr = i.variables[addr]
            if isinstance(arr, list):
                for k in range(min(length, len(arr))):
                    arr[k] = 0
            else:
                raise ForthError(f"{addr} is not an array")
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("ERASE", _erase, doc="Zero array cells ( addr len -- )")

    # ── FILL ( addr len val -- )  Fill *len* cells with *val*
    # addr deepest, len middle, val on top
    def _fill(i, t, n):
        val = i.pop()
        length = i.pop_int()
        addr = i.pop()
        if isinstance(addr, str) and addr in i.variables:
            arr = i.variables[addr]
            if isinstance(arr, list):
                for k in range(min(length, len(arr))):
                    arr[k] = val
            else:
                raise ForthError(f"{addr} is not an array")
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("FILL", _fill, doc="Fill array cells ( addr len val -- )")

    # ── MOVE ( src dst len -- )  Copy *len* cells from src array to dst array
    # src deepest, dst middle, len on top
    def _move(i, t, n):
        length = i.pop_int()
        dst_addr = i.pop()
        src_addr = i.pop()
        if not (isinstance(src_addr, str) and isinstance(dst_addr, str)):
            raise ForthError("MOVE needs array addresses")
        if src_addr not in i.variables or dst_addr not in i.variables:
            raise ForthError("bad array address")
        src = i.variables[src_addr]
        dst = i.variables[dst_addr]
        if not isinstance(src, list) or not isinstance(dst, list):
            raise ForthError("MOVE needs arrays")
        for k in range(min(length, len(src), len(dst))):
            dst[k] = src[k]
    i.reg("MOVE", _move, doc="Copy array cells ( src dst len -- )")