"""BNF grammar file loader.

Supports a simple but practical BNF-ish syntax::

    %token   NUMBER  ID  '+'  '-'  '*'  '/'  '('  ')'
    %start   expr
    %left    '+'  '-'
    %left    '*'
    %right   '^'
    %nonassoc UMINUS

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

Precedence/associativity directives (``%left``, ``%right``, ``%nonassoc``)
are parsed and returned alongside the grammar.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .grammar import Grammar
from .precedence import PrecedenceTable


class GrammarParseError(Exception):
    pass


def load_bnf(text: str) -> Grammar:
    """Parse a BNF grammar definition string into a Grammar object.

    This is a convenience wrapper that returns just the grammar.
    Use ``load_bnf_full`` to also get precedence information.
    """
    grammar, _ = load_bnf_full(text)
    return grammar


def load_bnf_full(text: str) -> Tuple[Grammar, PrecedenceTable]:
    """Parse a BNF grammar definition string, returning both the
    Grammar and a PrecedenceTable (from %left/%right/%nonassoc directives).
    """
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
    precedence = PrecedenceTable()
    prec_level = 0

    directive_re = re.compile(r"%(\w+)\s+(.+)")
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
            elif directive in ("left", "right", "nonassoc"):
                prec_level += 1
                assoc = "left" if directive == "left" else (
                    "right" if directive == "right" else "nonassoc"
                )
                # Strip quotes from terminal names in precedence declarations
                clean_args = []
                for a in args:
                    if len(a) >= 2 and a[0] == "'" and a[-1] == "'":
                        clean_args.append(a[1:-1])
                    else:
                        clean_args.append(a)
                precedence.add_level(prec_level, assoc, clean_args)
            else:
                # Unknown directive — keep in remaining lines
                remaining_lines.append(line)
        else:
            remaining_lines.append(line)

    text = "\n".join(remaining_lines)

    # Now parse productions.
    quoted_re = re.compile(r"'([^']*)'")
    quoted_tokens: List[str] = []

    def _save_quote(m: re.Match) -> str:
        quoted_tokens.append(m.group(1))
        return f"__Q{len(quoted_tokens) - 1}__"

    text = quoted_re.sub(_save_quote, text)

    chunks = text.split(";")
    productions: List[Tuple[str, List[str]]] = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise GrammarParseError(f"Production missing ':': {chunk!r}")
        head, body_str = chunk.split(":", 1)
        head = head.strip()
        if not head:
            raise GrammarParseError(f"Empty production head in: {chunk!r}")

        alternatives = body_str.split("|")
        for alt in alternatives:
            symbols = _tokenize_rhs(alt.strip(), quoted_tokens)
            productions.append((head, symbols))

    if not productions:
        raise GrammarParseError("No productions found in grammar definition")

    start = start_decl if start_decl is not None else productions[0][0]
    grammar = Grammar(productions, start=start)

    _ = tokens_decl
    return grammar, precedence


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