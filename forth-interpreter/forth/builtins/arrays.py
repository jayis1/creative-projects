"""Array words: ARRAY, []!, []@."""

from forth.core import ForthError, Word, _NextIdx


def register_array_ops(i) -> None:
    """Register array-related words on *i*."""

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
        i.variables[name] = arr

        def _push_arr(i2, t2, n2, _name=name):
            i2.push(_name)
        i.define(Word(name=name, native=_push_arr, doc=f"array {name}[{size}]"))
        return _NextIdx(n + 3)
    i._defining_words["ARRAY"] = _array

    def _arr_store(i, t, n):
        """[]! ( val idx addr -- )  Store val at arr[idx]."""
        addr = i.pop()
        idx = i.pop_int()
        val = i.pop()
        if isinstance(addr, str) and addr in i.variables:
            arr = i.variables[addr]
            if not isinstance(arr, list):
                raise ForthError(f"{addr} is not an array")
            if idx < 0 or idx >= len(arr):
                raise ForthError(f"array index {idx} out of range [0,{len(arr)})")
            arr[idx] = val
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("[]!", _arr_store, doc="Array store ( val idx addr -- )")

    def _arr_fetch(i, t, n):
        """[]@ ( idx addr -- val )  Fetch arr[idx]."""
        addr = i.pop()
        idx = i.pop_int()
        if isinstance(addr, str) and addr in i.variables:
            arr = i.variables[addr]
            if not isinstance(arr, list):
                raise ForthError(f"{addr} is not an array")
            if idx < 0 or idx >= len(arr):
                raise ForthError(f"array index {idx} out of range [0,{len(arr)})")
            i.push(arr[idx])
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("[]@", _arr_fetch, doc="Array fetch ( idx addr -- val )")

    # ARRAY-SIZE ( addr -- size )  Get array size
    def _arr_size(i, t, n):
        addr = i.pop()
        if isinstance(addr, str) and addr in i.variables:
            arr = i.variables[addr]
            if isinstance(arr, list):
                i.push(len(arr))
            else:
                raise ForthError(f"{addr} is not an array")
        else:
            raise ForthError(f"bad address: {addr}")
    i.reg("ARRAY-SIZE", _arr_size, doc="Get array size ( addr -- size )")