"""BNF grammar file loader.

Supports a simple but practical BNF-ish syntax::

    %token   NUMBER  ID  '+'  '-'  '*'  '/'  '('  ')'
    %start   expr

    expr   : term '+' expr
           | term
           ;

    term   : factor '*' term
           | factor
           ;

    factor : '(' expr ')'
           | NUMBER
           ;

Lines starting with ``#`` or ``//`` are comments.  Multiple alternatives
are separated by ``|``.  Productions end with ``;``.  Terminals are
typically quoted (``'+'``) or declared via ``%token``; everything else
on the RHS that isn't a non-terminal (identifier starting with lowercase
or uppercase letter) is treated as a terminal.

Quoted terminals can contain any character, e.g. ``'('``  ``'->'``.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .grammar import Grammar


class GrammarParseError(Exception):
    pass


def load_bnf(text: str) -> Grammar:
    """Parse a BNF grammar definition string into a Grammar object."""
    # Strip comments
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        lines.append(raw)

    text = "\n".join(lines)

    # Extract directives
    tokens_decl: List[str] = []
    start_decl: Optional[str] = None

    directive_re = re.compile(r"%(\w+)\s+(.+)")
    # Process directives line by line (they must be on their own lines)
    remaining_lines = []
    for line in text.splitlines():
        m = directive_re.match(line.strip())
        if m:
            directive = m.group(1)
            args = m.group(2).split()
            if directive == "token":
                tokens_decl.extend(args)
            elif directive == "start":
                if len(args) != 1:
                    raise GrammarParseError(
                        f"%start expects exactly one argument, got: {args}"
                    )
                start_decl = args[0]
            elif directive == "left":
                # associativity directive (parsed but only stored for reference)
                pass
            elif directive == "right":
                pass
            elif directive == "nonassoc":
                pass
            else:
                # Unknown directive — ignore but warn
                remaining_lines.append(line)
        else:
            remaining_lines.append(line)

    text = "\n".join(remaining_lines)

    # Now parse productions.
    # Tokenize the production section: split into tokens handling quoted strings
    quoted_re = re.compile(r"'([^']*)'")
    # Replace quoted strings with placeholders, then restore
    quoted_tokens: List[str] = []

    def _save_quote(m: re.Match) -> str:
        quoted_tokens.append(m.group(1))
        return f"__Q{len(quoted_tokens) - 1}__"

    text = quoted_re.sub(_save_quote, text)

    # Split into productions by ';'
    chunks = text.split(";")
    productions: List[Tuple[str, List[str]]] = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Split head from body by ':'
        if ":" not in chunk:
            raise GrammarParseError(f"Production missing ':': {chunk!r}")
        head, body_str = chunk.split(":", 1)
        head = head.strip()
        if not head:
            raise GrammarParseError(f"Empty production head in: {chunk!r}")

        # Split alternatives by '|' (but not inside quotes — already handled)
        alternatives = body_str.split("|")
        for alt in alternatives:
            symbols = _tokenize_rhs(alt.strip(), quoted_tokens)
            productions.append((head, symbols))

    if not productions:
        raise GrammarParseError("No productions found in grammar definition")

    start = start_decl if start_decl is not None else productions[0][0]
    grammar = Grammar(productions, start=start)

    # Validate that %token declarations match
    _ = tokens_decl  # Could verify these exist; for now just accept.

    return grammar


def _tokenize_rhs(s: str, quoted_tokens: List[str]) -> List[str]:
    """Tokenize the right-hand side of a production."""
    if not s:
        return []
    # Handle epsilon notation
    if s in ("ε", "epsilon", "<empty>"):
        return []
    parts = s.split()
    symbols: List[str] = []
    for part in parts:
        if part.startswith("__Q") and part.endswith("__"):
            # Restore quoted terminal
            idx = int(part[3:-2])
            symbols.append(quoted_tokens[idx])
        else:
            symbols.append(part)
    return symbols