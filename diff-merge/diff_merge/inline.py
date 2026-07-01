"""
Intra-line (word-level) diff highlighting.

Given two lines, compute the word-level differences and produce a
highlighted representation showing which words changed.
"""

from __future__ import annotations

import re
from typing import List, Tuple

__all__ = ["word_diff", "highlight_inline"]


def _tokenize(text: str) -> List[Tuple[str, str]]:
    """Tokenize text into (token, separator) pairs.

    Whitespace and punctuation are treated as separators.  Each token
    is followed by its separator (which may be empty).
    """
    tokens: List[Tuple[str, str]] = []
    # Split into word + whitespace/punctuation groups
    parts = re.split(r"(\s+|[^\w\s]+|\b)", text)
    i = 0
    while i < len(parts):
        word = parts[i] if i < len(parts) else ""
        sep = parts[i + 1] if i + 1 < len(parts) else ""
        if word or sep:
            tokens.append((word, sep))
        i += 2
    # Fallback: if tokenization produced nothing meaningful, use chars
    if not tokens:
        tokens = [(text, "")]
    return tokens


def word_diff(a: str, b: str) -> List[Tuple[str, str, str]]:
    """Compute a word-level diff between two lines.

    Returns a list of (tag, a_part, b_part) tuples where tag is
    'equal', 'delete', 'insert', or 'replace'.
    """
    from .myers import myers_diff, Operation

    a_tokens = [tok for tok, _ in _tokenize(a)]
    b_tokens = [tok for tok, _ in _tokenize(b)]

    # Also need separators
    a_seps = [sep for _, sep in _tokenize(a)]
    b_seps = [sep for _, sep in _tokenize(b)]

    ops = myers_diff(a_tokens, b_tokens)

    result: List[Tuple[str, str, str]] = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                result.append(("equal", a_tokens[i] + a_seps[i], b_tokens[j] + b_seps[j]))
        elif op.tag == Operation.DELETE:
            for i in range(op.i1, op.i2):
                result.append(("delete", a_tokens[i] + a_seps[i], ""))
        elif op.tag == Operation.INSERT:
            for j in range(op.j1, op.j2):
                result.append(("insert", "", b_tokens[j] + b_seps[j]))
        elif op.tag == Operation.REPLACE:
            a_words = [a_tokens[i] + a_seps[i] for i in range(op.i1, op.i2)]
            b_words = [b_tokens[j] + b_seps[j] for j in range(op.j1, op.j2)]
            result.append(("replace", "".join(a_words), "".join(b_words)))

    return result


def highlight_inline(
    a: str, b: str, *, use_color: bool = True
) -> Tuple[str, str]:
    """Produce highlighted versions of *a* and *b* showing word-level changes.

    If *use_color* is True, uses ANSI escape codes.  Otherwise uses
    ``[...]``/``{...}`` bracket markers.

    Returns (highlighted_a, highlighted_b).
    """
    parts = word_diff(a, b)

    a_out: List[str] = []
    b_out: List[str] = []

    for tag, a_part, b_part in parts:
        if tag == "equal":
            a_out.append(a_part)
            b_out.append(b_part)
        elif tag == "delete":
            if use_color:
                a_out.append(f"\033[31m{a_part}\033[0m")  # red
            else:
                a_out.append(f"[-{a_part}-]")
        elif tag == "insert":
            if use_color:
                b_out.append(f"\033[32m{b_part}\033[0m")  # green
            else:
                b_out.append(f"[+{b_part}+]")
        elif tag == "replace":
            if use_color:
                a_out.append(f"\033[31m{a_part}\033[0m")
                b_out.append(f"\033[32m{b_part}\033[0m")
            else:
                a_out.append(f"[-{a_part}-]")
                b_out.append(f"[+{b_part}+]")

    return ("".join(a_out), "".join(b_out))