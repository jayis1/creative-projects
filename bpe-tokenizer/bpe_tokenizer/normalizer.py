"""Text normalization utilities for BPE tokenizers.

Provides configurable normalization pipelines that run *before*
pre-tokenization, matching the behavior of SentencePiece and HuggingFace
tokenizers.
"""

from __future__ import annotations

import re
import unicodedata
from enum import Flag, auto

__all__ = [
    "Normalization",
    "Normalizer",
]


class Normalization(Flag):
    """Flags selecting which normalizations to apply."""

    NONE = 0
    LOWERCASE = auto()
    NFC = auto()           # Unicode NFC composition
    NFD = auto()           # Unicode NFD decomposition
    NFKC = auto()          # Compatibility composition
    NFKD = auto()          # Compatibility decomposition
    STRIP_ACCENTS = auto() # Remove diacritics (requires NFD first)
    STRIP_WHITESPACE = auto()  # Collapse multiple whitespace → single space
    REMOVE_CONTROL = auto()    # Remove control characters
    CRLF_TO_LF = auto()        # \r\n → \n
    REPLACE_ZWSP = auto()      # Zero-width space → regular space


class Normalizer:
    """Configurable text normalizer.

    Apply normalizations in a fixed order:
    1. Unicode decomposition (NFD/NFKD) or composition (NFC/NFKC)
    2. Strip accents (if NFD/NFKD was applied)
    3. CRLF → LF
    4. Replace zero-width spaces
    5. Remove control characters
    6. Collapse whitespace
    7. Lowercase

    Parameters
    ----------
    flags:
        Bitwise-OR of :class:`Normalization` flags.
    """

    def __init__(self, flags: Normalization = Normalization.NONE):
        self.flags = flags

    def normalize(self, text: str) -> str:
        f = self.flags

        # 1. Unicode normalization
        if f & Normalization.NFKD:
            text = unicodedata.normalize("NFKD", text)
        elif f & Normalization.NFD:
            text = unicodedata.normalize("NFD", text)
        elif f & Normalization.NFKC:
            text = unicodedata.normalize("NFKC", text)
        elif f & Normalization.NFC:
            text = unicodedata.normalize("NFC", text)

        # 2. Strip accents (only meaningful after NFD/NFKD)
        if f & Normalization.STRIP_ACCENTS:
            text = "".join(
                c for c in unicodedata.normalize("NFD", text)
                if unicodedata.category(c) != "Mn"
            )

        # 3. CRLF → LF
        if f & Normalization.CRLF_TO_LF:
            text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Replace zero-width spaces
        if f & Normalization.REPLACE_ZWSP:
            text = text.replace("\u200b", " ")

        # 5. Remove control characters (keep \n and \t)
        if f & Normalization.REMOVE_CONTROL:
            text = "".join(
                c for c in text
                if unicodedata.category(c)[0] != "C" or c in "\n\t"
            )

        # 6. Collapse whitespace
        if f & Normalization.STRIP_WHITESPACE:
            text = re.sub(r"\s+", " ", text).strip()

        # 7. Lowercase
        if f & Normalization.LOWERCASE:
            text = text.lower()

        return text

    def __call__(self, text: str) -> str:
        return self.normalize(text)