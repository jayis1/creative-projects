"""Vocabulary data structures for the BPE tokenizer.

This module defines the core vocabulary representation: tokens, the
vocab map, and special-token handling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

__all__ = [
    "Token",
    "SpecialToken",
    "Vocab",
    "BPE_ERROR",
    "BPE_PAD",
    "BPE_BOS",
    "BPE_EOS",
    "BPE_UNK",
    "DEFAULT_SPECIALS",
    "first_available_id",
]


# ---------------------------------------------------------------------------
# Well-known special token strings and default set
# ---------------------------------------------------------------------------

BPE_PAD = "<pad>"
BPE_BOS = "<bos>"
BPE_EOS = "<eos>"
BPE_UNK = "<unk>"
BPE_ERROR = "<error>"


DEFAULT_SPECIALS: tuple[str, ...] = (BPE_PAD, BPE_BOS, BPE_EOS, BPE_UNK)


def first_available_id(existing_ids: Iterable[int]) -> int:
    """Return the smallest non-negative integer not in ``existing_ids``.

    Used to assign ids to special tokens when no explicit mapping is
    provided.  Stable regardless of the iteration order of the input.
    """
    seen = set(existing_ids)
    i = 0
    while i in seen:
        i += 1
    return i


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Token:
    """A single vocabulary entry.

    Attributes
    ----------
    id:
        The integer id assigned to this token.
    piece:
        The unicode string (sequence of code-units) that this token
        decodes to.  When the tokenizer is configured for byte-level
        mode, ``piece`` is the *decoded* string; the raw byte sequence
        is stored in ``bytes_piece``.
    bytes_piece:
        The raw ``bytes`` representation.  For normal (character) mode
        this is simply ``piece.encode("utf-8")``.  For byte mode it is
        the literal byte sequence.
    rank:
        Merge rank — lower rank means the merge was learned earlier and
        therefore has higher priority.  Base vocabulary tokens (single
        code-units / bytes) have rank ``0``.
    freq:
        Training-time frequency of this token in the corpus.  Retained
        for analysis / debugging.
    """

    id: int
    piece: str
    bytes_piece: bytes
    rank: int
    freq: int = 0

    def __repr__(self) -> str:  # pragma: no cover - trivial
        b = self.bytes_piece.decode("utf-8", errors="replace")
        return f"Token(id={self.id}, piece={self.piece!r}, bytes={b!r}, rank={self.rank})"


@dataclass
class SpecialToken:
    """A reserved special token (PAD/BOS/EOS/UNK/...).

    Special tokens are *never* produced by BPE merges — they are only
    inserted explicitly by the encoder or by the user.
    """

    id: int
    piece: str
    is_unk: bool = False

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"SpecialToken(id={self.id}, piece={self.piece!r}, unk={self.is_unk})"


# ---------------------------------------------------------------------------
# Vocab container
# ---------------------------------------------------------------------------

@dataclass
class Vocab:
    """The complete vocabulary: base tokens + merges + specials.

    The vocab is organised as:

    * ``specials`` — dict mapping special-string → SpecialToken
    * ``tokens`` — dict mapping token-piece (str) → Token
    * ``id_to_token`` — dict mapping id → Token or SpecialToken

    The integer ids of special tokens are *not* required to be
    contiguous with the regular token ids, and are not required to be
    0-based, although the default convention is 0..n_specials-1.
    """

    tokens: dict[str, Token] = field(default_factory=dict)
    specials: dict[str, SpecialToken] = field(default_factory=dict)
    id_to_token: dict[int, Token | SpecialToken] = field(default_factory=dict)
    byte_mode: bool = False

    # -- mutation ----------------------------------------------------------

    def add_token(self, piece: str, bytes_piece: bytes, rank: int,
                  freq: int = 0) -> Token:
        """Add a new regular token and return it.  Id is auto-assigned.

        Raises ValueError if *piece* already exists in the vocab.
        """
        if piece in self.tokens:
            raise ValueError(
                f"Token piece {piece!r} already exists in the vocab "
                f"(id={self.tokens[piece].id})"
            )
        # Id = number of existing tokens (regulars) + number of specials.
        # This keeps regular-token ids contiguous starting after specials.
        next_id = self._next_regular_id()
        tok = Token(id=next_id, piece=piece, bytes_piece=bytes_piece,
                    rank=rank, freq=freq)
        self.tokens[piece] = tok
        self.id_to_token[next_id] = tok
        return tok

    def add_special(self, piece: str, is_unk: bool = False) -> SpecialToken:
        """Add a special token.  Id is auto-assigned to the smallest
        unused non-negative integer (typically 0..n-1).
        """
        if piece in self.specials:
            return self.specials[piece]
        sid = first_available_id(self.id_to_token.keys())
        st = SpecialToken(id=sid, piece=piece, is_unk=is_unk)
        self.specials[piece] = st
        self.id_to_token[sid] = st
        return st

    def _next_regular_id(self) -> int:
        """Next id for a regular token.

        Regular token ids start *after* all special-token ids so that
        specials occupy the low ids (the GPT-2 / Llama convention).
        """
        if self.specials:
            max_special = max(s.id for s in self.specials.values())
            base = max_special + 1
        else:
            base = 0
        return base + len(self.tokens)

    # -- query -------------------------------------------------------------

    def size(self) -> int:
        """Total vocab size (specials + regulars)."""
        return len(self.specials) + len(self.tokens)

    def regular_size(self) -> int:
        """Number of regular (non-special) tokens."""
        return len(self.tokens)

    def get_by_piece(self, piece: str) -> Token | SpecialToken | None:
        if piece in self.specials:
            return self.specials[piece]
        return self.tokens.get(piece)

    def get_by_id(self, tid: int) -> Token | SpecialToken | None:
        return self.id_to_token.get(tid)

    def unk_id(self) -> int | None:
        """Id of the UNK token, or None if no UNK is configured."""
        for st in self.specials.values():
            if st.is_unk:
                return st.id
        return None

    def has_unk(self) -> bool:
        return any(s.is_unk for s in self.specials.values())

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "tokens": [
                {
                    "id": t.id,
                    "piece": t.piece,
                    "bytes_hex": t.bytes_piece.hex(),
                    "rank": t.rank,
                    "freq": t.freq,
                }
                for t in sorted(self.tokens.values(), key=lambda t: t.id)
            ],
            "specials": [
                {"id": s.id, "piece": s.piece, "is_unk": s.is_unk}
                for s in sorted(self.specials.values(), key=lambda s: s.id)
            ],
            "byte_mode": self.byte_mode,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Vocab":
        v = cls(byte_mode=bool(d.get("byte_mode", False)))
        for s in d.get("specials", []):
            st = SpecialToken(id=int(s["id"]), piece=str(s["piece"]),
                              is_unk=bool(s.get("is_unk", False)))
            v.specials[st.piece] = st
            v.id_to_token[st.id] = st
        for t in d.get("tokens", []):
            tok = Token(id=int(t["id"]), piece=str(t["piece"]),
                        bytes_piece=bytes.fromhex(t["bytes_hex"]),
                        rank=int(t["rank"]), freq=int(t.get("freq", 0)))
            v.tokens[tok.piece] = tok
            v.id_to_token[tok.id] = tok
        return v

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "Vocab":
        return cls.from_dict(json.loads(s))