"""I/O words: ., EMIT, CR, SPACE, BL, .S, TYPE, DUMP, .R, U., SPACES."""

from forth.core import ForthError


def register_io_ops(i) -> None:
    """Register I/O words on *i*."""

    def _dot(i, t, n):
        v = i.pop()
        if isinstance(v, float):
            i.emit(f"{v:g} ")
        elif isinstance(v, bool):
            i.emit("-1 " if v else "0 ")
        else:
            i.emit(f"{v} ")
    i.reg(".", _dot, doc="Print top + space")

    # .R ( n width -- )  Print n right-justified in width columns
    def _dot_r(i, t, n):
        width = i.pop_int()
        val = i.pop()
        if isinstance(val, float):
            s = f"{val:g}"
        else:
            s = f"{val}"
        i.emit(f"{s:>{width}} ")
    i.reg(".R", _dot_r, doc="Print right-justified ( n width -- )")

    # U. ( n -- )  Print unsigned
    def _u_dot(i, t, n):
        val = i.pop_int()
        if val < 0:
            val += (1 << 64)  # treat as 64-bit unsigned
        i.emit(f"{val} ")
    i.reg("U.", _u_dot, doc="Print unsigned")

    def _emit(i, t, n):
        i.emit(chr(i.pop_int()))
    i.reg("EMIT", _emit, doc="Print char")

    i.reg("CR", lambda i, t, n: i.emit("\n"), doc="Newline")
    i.reg("SPACE", lambda i, t, n: i.emit(" "), doc="Space")
    i.reg("BL", lambda i, t, n: i.push(32), doc="Blank char code")

    # SPACES ( n -- )  Print n spaces
    def _spaces(i, t, n):
        count = i.pop_int()
        if count > 0:
            i.emit(" " * count)
    i.reg("SPACES", _spaces, doc="Print n spaces")

    def _dots(i, t, n):
        i.emit("<" + " ".join(str(v) for v in i.stack) + ">")
    i.reg(".S", _dots, doc="Show stack")

    i.reg("TYPE", lambda i, t, n: i.emit(str(i.pop())), doc="Print top as string")

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
    i.reg("DUMP", _dump, doc="Hex dump of stack")