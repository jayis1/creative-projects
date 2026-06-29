"""Exception handling words: CATCH, THROW, ABORT, ABORT\"."""

from forth.core import ForthError, ForthThrow, _NextIdx


def register_exception_words(i) -> None:
    """Register exception-handling words on *i*."""

    # ── THROW ( code -- )  Throw a Forth exception ──
    def _throw(i, t, n):
        code = i.pop_int()
        raise ForthThrow(code, f"THROW {code}")
    i.reg("THROW", _throw, doc="Throw exception ( code -- )")

    # ── CATCH ( xt -- code )  Execute word; if it throws, push code; else push 0 ──
    # In our model we can't easily get an XT (execution token), so CATCH
    # takes a word name and runs it.  This is a simplified version.
    def _catch(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("CATCH needs a word name")
        name = t[n + 1].upper()
        word = i.lookup(name)
        if word is None:
            raise ForthError(f"CATCH: unknown word {name}")
        try:
            if word.native is not None:
                word.native(i, [], 0)
            else:
                i._execute_body(word.data)
            i.push(0)
        except ForthThrow as e:
            i.push(e.code)
        except ForthError as e:
            i.push(-1)
        return _NextIdx(n + 2)
    i._defining_words["CATCH"] = _catch

    # ── ABORT ( -- )  Clear stack and raise error ──
    def _abort(i, t, n):
        i.stack.clear()
        raise ForthError("ABORT")
    i.reg("ABORT", _abort, doc="Abort, clear stack")

    # ── ABORT" ( f -- )  If flag is true, abort with message ──
    def _abort_quote(i, t, n):
        if n + 1 >= len(t):
            raise ForthError('ABORT" needs a string')
        s = t[n + 1]
        if s.startswith('"') and s.endswith('"') and len(s) >= 2:
            text = s[1:-1]
        else:
            text = s
        if i.compiling:
            i.current_def.append(("lit", text))
            i.current_def.append(("call", "ABORT-MESSAGE"))
        else:
            flag = i.pop()
            if flag != 0:
                raise ForthError(f"ABORT: {text}")
        return _NextIdx(n + 2)
    i.reg('ABORT"', _abort_quote, immediate=True, doc='Abort if flag true ( f "msg" -- )')

    # ── ABORT-MESSAGE ( msg flag -- )  Helper for compiled ABORT" ──
    def _abort_message(i, t, n):
        msg = i.pop()
        flag = i.pop()
        if flag != 0:
            raise ForthError(f"ABORT: {msg}")
    i.reg("ABORT-MESSAGE", _abort_message, doc="Abort helper ( msg flag -- )")