"""String words: .\" (compiled string printing), STRING, STRLEN, STRCAT, CMP-STR."""

from forth.core import ForthError, _NextIdx


def register_string_ops(i) -> None:
    """Register string-related words on *i*."""

    # ── ." immediate — compiled string printing ──
    # The tokenizer produces ." followed by a "..." string token
    # containing the text between ." and the closing ".
    def _dot_quote(i, t, n):
        if n + 1 >= len(t):
            raise ForthError('.\" needs a string')
        s = t[n + 1]
        # The tokenizer wraps the content in quotes
        if s.startswith('"') and s.endswith('"') and len(s) >= 2:
            text = s[1:-1]
        else:
            text = s
        if i.compiling:
            i.current_def.append(("lit", text))
            i.current_def.append(("call", "TYPE"))
        else:
            i.emit(text)
        return _NextIdx(n + 2)
    i.reg('."', _dot_quote, immediate=True, doc='Print string at runtime')

    # ── STRLEN ( str -- len )  Push string length ──
    def _strlen(i, t, n):
        s = i.pop()
        if not isinstance(s, str):
            raise ForthError("STRLEN needs a string")
        i.push(len(s))
    i.reg("STRLEN", _strlen, doc="String length ( str -- len )")

    # ── STRCAT ( str2 str1 -- str1+str2 )  Concatenate strings ──
    def _strcat(i, t, n):
        s1 = i.pop()
        s2 = i.pop()
        if not isinstance(s1, str) or not isinstance(s2, str):
            raise ForthError("STRCAT needs strings")
        i.push(s1 + s2)
    i.reg("STRCAT", _strcat, doc="String concat ( str2 str1 -- result )")

    # ── CMP-STR ( str2 str1 -- flag )  Compare strings for equality ──
    def _cmp_str(i, t, n):
        s2 = i.pop()
        s1 = i.pop()
        if not isinstance(s1, str) or not isinstance(s2, str):
            raise ForthError("CMP-STR needs strings")
        i.push(-1 if s1 == s2 else 0)
    i.reg("CMP-STR", _cmp_str, doc="String compare ( str2 str1 -- flag )")

    # ── SUBSTR ( start len str -- substr )  Extract substring ──
    def _substr(i, t, n):
        s = i.pop()
        length = i.pop_int()
        start = i.pop_int()
        if not isinstance(s, str):
            raise ForthError("SUBSTR needs a string")
        if start < 0 or start > len(s):
            raise ForthError("SUBSTR start out of range")
        i.push(s[start:start + length])
    i.reg("SUBSTR", _substr, doc="Extract substring ( start len str -- substr )")

    # ── CHAR ( "name" -- char )  Push ASCII value of first char of next token ──
    def _char(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("CHAR needs a word")
        name = t[n + 1]
        i.push(ord(name[0]))
        return _NextIdx(n + 2)
    i._defining_words["CHAR"] = _char

    # ── [CHAR] ( compile-time: "name" -- )  Compile char as literal ──
    def _bracket_char(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("[CHAR] needs a word")
        name = t[n + 1]
        i.current_def.append(("lit", ord(name[0])))
        return _NextIdx(n + 2)
    i.reg("[CHAR]", _bracket_char, immediate=True, doc="Compile char literal")

    # ── C" — compile a counted string (push as string literal at runtime) ──
    def _c_quote(i, t, n):
        if n + 1 >= len(t):
            raise ForthError('C" needs a string')
        s = t[n + 1]
        if s.startswith('"') and s.endswith('"') and len(s) >= 2:
            text = s[1:-1]
        else:
            text = s
        if i.compiling:
            i.current_def.append(("lit", text))
        else:
            i.push(text)
        return _NextIdx(n + 2)
    i.reg('C"', _c_quote, immediate=True, doc='Compile counted string')

    # ── .( — print string immediately (even in compile mode) ──
    # Tokenizer produces ".(" followed by a text token (already stripped of )
    def _dot_paren(i, t, n):
        if n + 1 >= len(t):
            raise ForthError('.( needs text')
        text = t[n + 1]
        i.emit(text)
        return _NextIdx(n + 2)
    i.reg('.(', _dot_paren, immediate=True, doc='Print string immediately')