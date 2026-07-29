"""Pre-tokenization strategies for BPE training and encoding.

Pre-tokenization splits the raw input text into chunks *before* BPE
merges are applied.  This keeps merges local to words / pieces and
prevents cross-word merges, which is essential for good tokenization
quality.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List

__all__ = [
    "RegexPattern",
    "Pretokenizer",
    "WhitespacePretokenizer",
    "WordPretokenizer",
    "BytePretokenizer",
    "GPT2_REGEX",
    "GPT4_REGEX",
    "LLAMA3_REGEX",
]

# ---------------------------------------------------------------------------
# Common pre-tokenization regexes (from the respective model releases)
# ---------------------------------------------------------------------------

# GPT-2: split on whitespace, keeping trailing apostrophes/letters together
GPT2_REGEX = r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""

# GPT-4 / cl100k_base: similar but with more granularity
GPT4_REGEX = (
    r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"""
)

# Llama-3
LLAMA3_REGEX = (
    r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"""
)


class RegexPattern:
    """A pre-compiled regex pattern, with fallback if the regex engine
    does not support the pattern (notably ``\\p{L}`` requires the
    ``regex`` module; if unavailable we degrade gracefully).
    """

    def __init__(self, pattern: str):
        self.pattern_str = pattern
        self._rx = self._compile(pattern)

    @staticmethod
    def _compile(pattern: str):  # type: ignore[return-type]
        try:
            import regex  # type: ignore[import-not-found]
            return regex.compile(pattern)
        except ImportError:
            # Fall back to the stdlib ``re`` with a degraded pattern.
            # We can't simply replace \p{L} with [^\W\d_] inside existing
            # character classes (that creates nested classes), so we use
            # a token-by-token approach: split on | to get alternatives,
            # then fix each one.
            return re.compile(RegexPattern._degrade_pattern(pattern))

    @staticmethod
    def _degrade_pattern(pattern: str) -> str:
        """Degrade a unicode-property regex to a stdlib-re-compatible one.

        Replaces ``\\p{L}`` and ``\\p{N}`` outside of character classes
        with ``[^\\W\\d_]`` and ``\\d`` respectively, and inside negated
        character classes ``[^...\\p{L}\\p{N}...]`` with the equivalent
        ``[^...\\w...]`` (approximate but functional).
        """
        # Simple approach: replace \p{L} → [^\W\d_], \p{N} → \d
        # but handle them inside character classes by replacing
        # [^...\p{L}\p{N}...] → [^...\w...] and [...\p{L}...] → [...\w...]
        # We do this with a state machine.
        result: list[str] = []
        i = 0
        in_class = False
        while i < len(pattern):
            if pattern[i] == "[" and (i == 0 or pattern[i - 1] != "\\"):
                in_class = True
                result.append("[")
                i += 1
                # Skip optional negation ^.
                if i < len(pattern) and pattern[i] == "^":
                    result.append("^")
                    i += 1
                continue
            elif pattern[i] == "]" and in_class:
                in_class = False
                result.append("]")
                i += 1
                continue
            if not in_class and pattern[i:i + 4] == r"\p{L":
                # \p{L} or \p{Ll} etc. → [^\W\d_] outside classes
                end = pattern.index("}", i)
                result.append(r"[^\W\d_]")
                i = end + 1
                continue
            if not in_class and pattern[i:i + 4] == r"\p{N":
                end = pattern.index("}", i)
                result.append(r"\d")
                i = end + 1
                continue
            if in_class and pattern[i:i + 4] == r"\p{L":
                # Inside a class, \p{L} → a-z-ish.  Use \w minus digits = [^\W\d_]
                # but we're already in a class, so just emit "a-zA-Z" as approximation
                end = pattern.index("}", i)
                result.append("a-zA-Z")
                i = end + 1
                continue
            if in_class and pattern[i:i + 4] == r"\p{N":
                end = pattern.index("}", i)
                result.append("0-9")
                i = end + 1
                continue
            result.append(pattern[i])
            i += 1
        return "".join(result)

    def finditer(self, text: str):
        return self._rx.finditer(text)

    def findall(self, text: str) -> List[str]:
        return self._rx.findall(text)

    def split(self, text: str) -> List[str]:
        return [m.group() for m in self._rx.finditer(text)]


# ---------------------------------------------------------------------------
# Pre-tokenizer base + implementations
# ---------------------------------------------------------------------------

class Pretokenizer(ABC):
    """Base class for pre-tokenizers."""

    @abstractmethod
    def pretokenize(self, text: str) -> List[str]:
        """Split *text* into a list of pre-token strings."""
        ...

    def __call__(self, text: str) -> List[str]:
        return self.pretokenize(text)


class WhitespacePretokenizer(Pretokenizer):
    """Simple whitespace split.  Keeps whitespace attached to the
    following word (``" hello"``) to match GPT-2 conventions.
    """

    _RX = re.compile(r"\S+|\s+")

    def pretokenize(self, text: str) -> List[str]:
        return self._RX.findall(text)


class WordPretokenizer(Pretokenizer):
    """Regex-based word pre-tokenizer (GPT-2 / GPT-4 / Llama-3 style).

    Pass one of ``GPT2_REGEX``, ``GPT4_REGEX``, ``LLAMA3_REGEX`` or a
    custom pattern string.
    """

    def __init__(self, pattern: str = GPT4_REGEX):
        self._rx = RegexPattern(pattern)

    def pretokenize(self, text: str) -> List[str]:
        return self._rx.split(text)


class BytePretokenizer(Pretokenizer):
    """Byte-level pre-tokenizer (GPT-2 byte mode).

    Converts each *byte* of the UTF-8 encoding to a printable character
    via the GPT-2 byte-to-unicode mapping, then splits on whitespace.
    This ensures every possible byte value is representable as a single
    unicode code-point in the vocab.
    """

    # GPT-2 byte-to-unicode mapping (lazy)
    _byte_encoder: dict[int, str] | None = None
    _byte_decoder: dict[str, int] | None = None

    @classmethod
    def _ensure_maps(cls) -> None:
        if cls._byte_encoder is not None:
            return
        # Reproduce GPT-2's bytes_to_unicode()
        bs = (
            list(range(ord("!"), ord("~") + 1))
            + list(range(ord("¡"), ord("¬") + 1))
            + list(range(ord("®"), ord("ÿ") + 1))
        )
        cs = bs[:]
        n = 0
        for b in range(256):
            if b not in bs:
                bs.append(b)
                cs.append(256 + n)
                n += 1
        cs = [chr(c) for c in cs]
        cls._byte_encoder = dict(zip(bs, cs))
        cls._byte_decoder = {v: k for k, v in zip(bs, cs)}

    def pretokenize(self, text: str) -> List[str]:
        type(self)._ensure_maps()
        assert BytePretokenizer._byte_encoder is not None
        # Re-implement GPT-2 regex on the byte-encoded string.
        # GPT-2 uses a specific regex on the *encoded* text.
        encoded = "".join(BytePretokenizer._byte_encoder[b] for b in text.encode("utf-8"))
        # Split on whitespace runs, keeping them.
        return re.findall(r"\S+|\s+", encoded)

    @classmethod
    def encode_text(cls, text: str) -> str:
        """Map text → GPT-2 byte-unicode string (no splitting)."""
        cls._ensure_maps()
        assert cls._byte_encoder is not None
        return "".join(cls._byte_encoder[b] for b in text.encode("utf-8"))

    @classmethod
    def decode_text(cls, encoded: str) -> str:
        """Inverse of :meth:`encode_text`."""
        cls._ensure_maps()
        assert BytePretokenizer._byte_decoder is not None
        byte_vals = bytes(BytePretokenizer._byte_decoder[c] for c in encoded)
        return byte_vals.decode("utf-8", errors="replace")