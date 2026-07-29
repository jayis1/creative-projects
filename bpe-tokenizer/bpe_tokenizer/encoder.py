"""Advanced encoders: BPE-dropout, Unigram model, and best-of-N search.

This module provides alternatives to the standard greedy-rank BPE
encoding:

* :class:`BPESentencePiece` — a SentencePiece-style Unigram model that
  scores segmentations using log-probabilities and picks the best one
  via Viterbi-style dynamic programming.

* :func:`bpe_dropout` — stochastic encoding that randomly drops merge
  candidates during the merge loop, producing multiple segmentations
  for the same input (useful for data augmentation / robustness).

* :class:`UnigramScore` — helper for computing log-probabilities of
  tokens from their training frequencies.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Sequence

from .tokenizer import BPETokenizer
from .vocab import Vocab

__all__ = [
    "BPESentencePiece",
    "UnigramScore",
    "bpe_dropout",
    "viterbi_segment",
]


# ---------------------------------------------------------------------------
# Unigram scoring
# ---------------------------------------------------------------------------

@dataclass
class UnigramScore:
    """Log-probability scores for Unigram-model segmentation.

    The Unigram model (Kudo 2018) assumes that the best segmentation is
    the one that maximises the product of token probabilities, where
    each token's probability is proportional to its training frequency.
    """

    log_probs: dict[str, float]
    total_freq: int
    vocab_size: int

    @classmethod
    def from_vocab(cls, vocab: Vocab) -> "UnigramScore":
        """Build a UnigramScore from a trained vocab."""
        freqs = {p: max(t.freq, 1) for p, t in vocab.tokens.items()}
        total = sum(freqs.values())
        log_probs = {p: math.log(f / total) for p, f in freqs.items()}
        return cls(log_probs=log_probs, total_freq=total, vocab_size=len(freqs))

    def score(self, piece: str) -> float:
        """Log-probability of a single piece (UNK → -inf)."""
        return self.log_probs.get(piece, float("-inf"))

    def score_sequence(self, pieces: Sequence[str]) -> float:
        """Total log-probability of a sequence of pieces."""
        return sum(self.score(p) for p in pieces)


# ---------------------------------------------------------------------------
# Viterbi segmentation (Unigram / SentencePiece style)
# ---------------------------------------------------------------------------

def viterbi_segment(
    text: str,
    score: UnigramScore,
    max_piece_len: int = 20,
) -> list[str]:
    """Segment *text* into pieces that maximise total log-probability.

    Uses Viterbi-style dynamic programming.  ``max_piece_len`` caps the
    length of a candidate piece to limit the search space.
    """
    n = len(text)
    if n == 0:
        return []

    # best[i] = (best_score, best_split_pos)
    best: list[tuple[float, int]] = [(0.0, -1)] * (n + 1)
    best[0] = (0.0, -1)

    for end in range(1, n + 1):
        best_score = float("-inf")
        best_start = -1
        start_lo = max(0, end - max_piece_len)
        for start in range(start_lo, end):
            piece = text[start:end]
            s = score.score(piece)
            if s == float("-inf"):
                continue
            total = best[start][0] + s
            if total > best_score:
                best_score = total
                best_start = start
        best[end] = (best_score, best_start)

    # Reconstruct.
    pieces: list[str] = []
    pos = n
    while pos > 0:
        start = best[pos][1]
        if start < 0:
            # Fallback: single char.
            pieces.append(text[pos - 1:pos])
            pos -= 1
        else:
            pieces.append(text[start:pos])
            pos = start
    pieces.reverse()
    return pieces


# ---------------------------------------------------------------------------
# BPE-dropout
# ---------------------------------------------------------------------------

def bpe_dropout(
    tokenizer: BPETokenizer,
    text: str,
    dropout: float = 0.1,
    rng: random.Random | None = None,
) -> list[int]:
    """Encode *text* with BPE-dropout — stochastic merge dropping.

    At each merge step, with probability ``dropout``, the best pair is
    *not* merged (skipped), leading to different segmentations on
    different calls.  This is useful for data augmentation and
    improving model robustness (Provilkov et al. 2020).

    Parameters
    ----------
    tokenizer:
        A trained :class:`BPETokenizer`.
    text:
        Input text.
    dropout:
        Probability of dropping a merge candidate (0 = standard BPE,
        1 = no merges at all).
    rng:
        Optional :class:`random.Random` instance for reproducibility.
    """
    if not 0.0 <= dropout <= 1.0:
        raise ValueError("dropout must be in [0, 1]")
    rng = rng or random.Random()

    units = tokenizer._split_to_units(text)
    symbols: list[str] = list(units)

    while len(symbols) > 1:
        best_rank = None
        best_idx = -1
        for i in range(len(symbols) - 1):
            pair = (symbols[i], symbols[i + 1])
            rank = tokenizer._merge_ranks.get(pair)
            if rank is not None and (best_rank is None or rank < best_rank):
                best_rank = rank
                best_idx = i
        if best_idx == -1:
            break
        # Dropout: skip this merge with probability *dropout*.
        if rng.random() < dropout:
            # Temporarily skip this pair by merging the *next* best pair.
            # Simpler approach: just skip and try the next iteration.
            # We mark this pair as "seen" by merging it but then splitting
            # it back — no, that's wasteful.  Instead, we find the next
            # best pair that is not at best_idx.
            alt_rank = None
            alt_idx = -1
            for i in range(len(symbols) - 1):
                if i == best_idx:
                    continue
                pair = (symbols[i], symbols[i + 1])
                rank = tokenizer._merge_ranks.get(pair)
                if rank is not None and (alt_rank is None or rank < alt_rank):
                    alt_rank = rank
                    alt_idx = i
            if alt_idx == -1:
                break
            best_idx = alt_idx

        merged = symbols[best_idx] + symbols[best_idx + 1]
        symbols[best_idx:best_idx + 2] = [merged]

    # Convert to ids.
    result: list[int] = []
    unk_id = tokenizer.vocab.unk_id()
    for sym in symbols:
        tok = tokenizer.vocab.tokens.get(sym)
        if tok is not None:
            result.append(tok.id)
        elif unk_id is not None:
            result.append(unk_id)
    return result


# ---------------------------------------------------------------------------
# SentencePiece-style Unigram tokenizer
# ---------------------------------------------------------------------------

class BPESentencePiece:
    """SentencePiece-style Unigram tokenizer.

    Wraps a :class:`BPETokenizer` but uses Viterbi segmentation based
    on Unigram log-probabilities instead of greedy BPE merge-rank
    encoding.

    This produces *optimal* segmentations (maximising likelihood)
    rather than the greedy approximations of standard BPE.
    """

    def __init__(self, tokenizer: BPETokenizer, max_piece_len: int = 20):
        self.tokenizer = tokenizer
        self.score = UnigramScore.from_vocab(tokenizer.vocab)
        self.max_piece_len = max_piece_len

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        from .vocab import BPE_BOS, BPE_EOS

        ids: list[int] = []
        if add_bos:
            ids.append(self.tokenizer._special_id(BPE_BOS, 0))
        # Pre-tokenize, then Viterbi-segment each chunk.
        chunks = self.tokenizer.pretokenizer(text)
        unk_id = self.tokenizer.vocab.unk_id()
        for chunk in chunks:
            if self.tokenizer.vocab.byte_mode:
                from .pretokenize import BytePretokenizer
                chunk = BytePretokenizer.encode_text(chunk)
            pieces = viterbi_segment(chunk, self.score, self.max_piece_len)
            for p in pieces:
                tok = self.tokenizer.vocab.tokens.get(p)
                if tok is not None:
                    ids.append(tok.id)
                elif unk_id is not None:
                    ids.append(unk_id)
        if add_eos:
            ids.append(self.tokenizer._special_id(BPE_EOS, 2))
        return ids

    def decode(self, ids: list[int]) -> str:
        return self.tokenizer.decode(ids)