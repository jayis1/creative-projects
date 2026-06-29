"""Defining words: : ; VARIABLE, CONSTANT, VALUE, TO, CREATE, ALLOT."""

from forth.core import ForthError, Word, _NextIdx
from forth.builtins._helpers import NativeFn


def register_defining_words(i) -> None:
    """Register defining words on *i*."""

    def _variable(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("VARIABLE needs a name")
        name = t[n + 1].upper()
        i.variables[name] = [0]

        def _push_addr(i2, t2, n2, _name=name):
            i2.push(_name)
        i.define(Word(name=name, native=_push_addr, doc=f"variable {name}"))
        return _NextIdx(n + 2)
    i._defining_words["VARIABLE"] = _variable

    def _constant(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("CONSTANT needs a name")
        name = t[n + 1].upper()
        val = i.pop()

        def _push_const(i2, t2, n2, _v=val):
            i2.push(_v)
        i.define(Word(name=name, native=_push_const, doc=f"constant {name}"))
        return _NextIdx(n + 2)
    i._defining_words["CONSTANT"] = _constant

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
    i._defining_words["VALUE"] = _value

    def _to(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("TO needs a name")
        name = t[n + 1].upper()
        if name not in i.variables:
            raise ForthError(f"TO: {name} is not a value")
        i.variables[name][0] = i.pop()
        return _NextIdx(n + 2)
    i._defining_words["TO"] = _to

    # CREATE — like VARIABLE but does not initialise (just creates a 1-cell var)
    def _create(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("CREATE needs a name")
        name = t[n + 1].upper()
        i.variables[name] = [0]

        def _push_addr(i2, t2, n2, _name=name):
            i2.push(_name)
        i.define(Word(name=name, native=_push_addr, doc=f"create {name}"))
        return _NextIdx(n + 2)
    i._defining_words["CREATE"] = _create

    # VARIABLE-aliased 2VARIABLE (creates a 2-cell variable, represented as [0, 0])
    def _2variable(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("2VARIABLE needs a name")
        name = t[n + 1].upper()
        i.variables[name] = [0, 0]

        def _push_addr(i2, t2, n2, _name=name):
            i2.push(_name)
        i.define(Word(name=name, native=_push_addr, doc=f"2variable {name}"))
        return _NextIdx(n + 2)
    i._defining_words["2VARIABLE"] = _2variable