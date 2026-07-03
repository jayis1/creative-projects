"""PostScript scanner/tokenizer.

Splits a PostScript source string into tokens following the
Adobe PLRM lexical conventions:
  - Comments start with '%' and run to end of line.
  - Numbers: integers, real (decimal), and scientific notation.
  - Strings: ( ... ) with balanced parens and escapes,  and hex <...>.
  - Names: any sequence of regular characters not starting with a delimiter.
  - Procedure bodies are enclosed in { }.
  - Special: '<<' dict-begin and '>>' dict-end (PostScript Level 2).
"""

import re
from .errors import PSSyntaxError

# Regular characters per PLRM: anything that is not a delimiter or whitespace.
DELIMITERS = set("()<>[]{}/%")
WHITESPACE = set(" \t\n\r\f\0")


class Token:
    """One lexical token."""
    __slots__ = ("kind", "value", "pos")
    def __init__(self, kind: str, value, pos: int):
        self.kind = kind
        self.value = value
        self.pos = pos
    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r}, pos={self.pos})"


def _is_regular(ch: str) -> bool:
    return ch not in DELIMITERS and ch not in WHITESPACE


def scan_string(src: str, i: int, n: int):
    """Parse a ( ... ) literal string starting at i (i points at '(')."""
    depth = 1
    i += 1
    out = []
    while i < n:
        ch = src[i]
        if ch == '(':
            depth += 1
            out.append(ch); i += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                i += 1
                break
            out.append(ch); i += 1
        elif ch == '\\':
            i += 1
            if i >= n:
                break
            esc = src[i]
            if esc == 'n': out.append('\n')
            elif esc == 'r': out.append('\r')
            elif esc == 't': out.append('\t')
            elif esc == 'b': out.append('\b')
            elif esc == 'f': out.append('\f')
            elif esc == '\\': out.append('\\')
            elif esc == '(': out.append('(')
            elif esc == ')': out.append(')')
            elif esc == '\n':
                pass  # line continuation
            elif esc in '01234567':
                # up to 3 octal digits
                oct_digits = esc
                j = i + 1
                while j < n and src[j] in '01234567' and len(oct_digits) < 3:
                    oct_digits += src[j]; j += 1
                out.append(chr(int(oct_digits, 8) & 0xFF))
                i = j - 1
            else:
                out.append(esc)
            i += 1
        else:
            out.append(ch); i += 1
    if depth != 0:
        raise PSSyntaxError("Unterminated string literal")
    return ''.join(out), i


def scan_hex_string(src: str, i: int, n: int):
    """Parse a < ... > hex string starting at i (points at '<')."""
    i += 1  # skip '<'
    hexdigits = []
    while i < n:
        ch = src[i]
        if ch == '>':
            i += 1
            break
        if ch in ' \t\n\r\f':
            i += 1
            continue
        if ch in '0123456789abcdefABCDEF':
            hexdigits.append(ch)
            i += 1
        else:
            raise PSSyntaxError(f"Invalid character in hex string: {ch!r}")
    else:
        raise PSSyntaxError("Unterminated hex string")
    if len(hexdigits) % 2 == 1:
        hexdigits.append('0')
    raw = bytes.fromhex(''.join(hexdigits))
    return raw.decode('latin-1'), i


_INT_RE = re.compile(r'[+-]?\d+')
_REAL_RE = re.compile(r'[+-]?(\d+\.\d*|\.\d+|\d+\.?\d*[eE][+-]?\d+)')


def scan_number(src: str, i: int, n: int):
    """Try to scan a number starting at i. Returns (value, new_i) or None."""
    m = _REAL_RE.match(src, i)
    if m:
        val = float(m.group())
        if val.is_integer() and 'e' not in m.group().lower() and '.' not in m.group():
            return int(val), m.end()
        return val, m.end()
    m = _INT_RE.match(src, i)
    if m:
        return int(m.group()), m.end()
    return None


def scan_name(src: str, i: int, n: int):
    """Scan a name token (sequence of regular characters)."""
    start = i
    while i < n and _is_regular(src[i]):
        i += 1
    return src[start:i], i


def scan_literal_name(src: str, i: int, n: int):
    """Scan a /name (name literal)."""
    i += 1  # skip '/'
    if i < n and src[i] == '/':
        # //name  - immediately-evaluated name (rare; treat as regular name)
        i += 1
    start = i
    while i < n and _is_regular(src[i]):
        i += 1
    return src[start:i], i


def tokenize(src: str):
    """Yield Token objects from PostScript source."""
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        # Whitespace
        if ch in WHITESPACE:
            i += 1
            continue
        # Comment
        if ch == '%':
            if i + 1 < n and src[i + 1] == '%':
                # DSC comment - skip but we could store it
                while i < n and src[i] != '\n':
                    i += 1
                continue
            while i < n and src[i] != '\n':
                i += 1
            continue
        # Literal string
        if ch == '(':
            val, i = scan_string(src, i, n)
            yield Token('string', val, i)
            continue
        # Hex string or dict start
        if ch == '<':
            if i + 1 < n and src[i + 1] == '<':
                yield Token('dict_open', '<<', i)
                i += 2
                continue
            val, i = scan_hex_string(src, i, n)
            yield Token('string', val, i)
            continue
        # Dict end
        if ch == '>':
            if i + 1 < n and src[i + 1] == '>':
                yield Token('dict_close', '>>', i)
                i += 2
                continue
            raise PSSyntaxError("Unexpected '>'")
        # Procedure body open / close
        if ch == '{':
            yield Token('proc_open', '{', i)
            i += 1
            continue
        if ch == '}':
            yield Token('proc_close', '}', i)
            i += 1
            continue
        if ch == '[':
            yield Token('lbracket', '[', i)
            i += 1
            continue
        if ch == ']':
            yield Token('rbracket', ']', i)
            i += 1
            continue
        # Literal name
        if ch == '/':
            val, i = scan_literal_name(src, i, n)
            yield Token('name_literal', val, i)
            continue
        # Number?
        if ch in '+-.0123456789' or ch.isdigit():
            result = scan_number(src, i, n)
            if result is not None:
                val, i = result
                yield Token('number', val, i)
                continue
        # Regular name / keyword
        if _is_regular(ch):
            name, i = scan_name(src, i, n)
            yield Token('name', name, i)
            continue
        raise PSSyntaxError(f"Unexpected character {ch!r} at position {i}")
    yield Token('eof', None, i)