"""Analysis and diagnostics for trained BPE tokenizers.

Provides tools to evaluate tokenizer quality: compression ratio,
token-length statistics, coverage, merge-frequency analysis, and
subword fertility.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

from .tokenizer import BPETokenizer

__all__ = [
    "AnalysisResult",
    "TokenizerAnalyzer",
]


@dataclass
class AnalysisResult:
    """Results of tokenizer analysis on a corpus."""

    n_texts: int = 0
    n_chars: int = 0
    n_bytes: int = 0
    n_tokens: int = 0
    n_pieces: int = 0
    # Compression metrics
    chars_per_token: float = 0.0
    bytes_per_token: float = 0.0
    tokens_per_char: float = 0.0
    # Token length distribution
    mean_token_len: float = 0.0
    median_token_len: float = 0.0
    max_token_len: int = 0
    min_token_len: int = 0
    # Fertility (tokens per word)
    mean_fertility: float = 0.0
    # Coverage
    coverage: float = 0.0      # fraction of chars covered by known tokens
    unk_count: int = 0         # number of UNK tokens produced
    unk_rate: float = 0.0      # unk_count / n_tokens
    # Vocab stats
    vocab_size: int = 0
    n_single_chars: int = 0    # tokens that are single characters
    n_merges: int = 0
    # Token frequency (top-20)
    top_tokens: list[tuple[int, int]] = field(default_factory=list)  # (id, count)
    # Piece-length histogram
    length_histogram: dict[int, int] = field(default_factory=dict)


class TokenizerAnalyzer:
    """Analyze a trained :class:`BPETokenizer` on a test corpus."""

    def __init__(self, tokenizer: BPETokenizer):
        self.tokenizer = tokenizer

    def analyze(self, texts: Sequence[str]) -> AnalysisResult:
        result = AnalysisResult()
        unk_id = self.tokenizer.vocab.unk_id()
        special_ids = {s.id for s in self.tokenizer.vocab.specials.values()}

        all_token_ids: list[int] = []
        all_piece_lens: list[int] = []
        n_words = 0
        token_counter: Counter[int] = Counter()

        for text in texts:
            if not text:
                continue
            result.n_texts += 1
            result.n_chars += len(text)
            result.n_bytes += len(text.encode("utf-8"))

            # Count words (pre-tokens).
            chunks = self.tokenizer.pretokenizer(text)
            n_words += len([c for c in chunks if c.strip()])

            ids = self.tokenizer.encode(text)
            pieces = self.tokenizer.id_to_pieces(ids)

            result.n_tokens += len(ids)
            result.n_pieces += len(pieces)

            for tid, piece in zip(ids, pieces):
                all_token_ids.append(tid)
                token_counter[tid] += 1
                plen = len(piece)
                all_piece_lens.append(plen)
                result.length_histogram[plen] = result.length_histogram.get(plen, 0) + 1
                if tid == unk_id:
                    result.unk_count += 1
                if tid in special_ids:
                    # Don't count specials in piece-length stats.
                    pass

        # Compression
        if result.n_tokens > 0:
            result.chars_per_token = result.n_chars / result.n_tokens
            result.bytes_per_token = result.n_bytes / result.n_tokens
            result.tokens_per_char = result.n_tokens / result.n_chars if result.n_chars > 0 else 0.0
            result.unk_rate = result.unk_count / result.n_tokens

        # Token length stats (excluding specials)
        non_special_lens = [
            plen for tid, plen in zip(all_token_ids, all_piece_lens)
            if tid not in special_ids
        ]
        if non_special_lens:
            result.mean_token_len = sum(non_special_lens) / len(non_special_lens)
            sorted_lens = sorted(non_special_lens)
            n = len(sorted_lens)
            result.median_token_len = sorted_lens[n // 2] if n % 2 == 1 else (sorted_lens[n // 2 - 1] + sorted_lens[n // 2]) / 2
            result.max_token_len = max(non_special_lens)
            result.min_token_len = min(non_special_lens)

        # Fertility
        if n_words > 0:
            non_special_tokens = sum(1 for tid in all_token_ids if tid not in special_ids)
            result.mean_fertility = non_special_tokens / n_words

        # Vocab stats
        result.vocab_size = self.tokenizer.vocab.size()
        result.n_merges = len(self.tokenizer._merge_ranks)
        result.n_single_chars = sum(1 for t in self.tokenizer.vocab.tokens.values() if len(t.piece) == 1)

        # Coverage: fraction of tokens that are not UNK
        non_unk = sum(1 for tid in all_token_ids if tid != unk_id and tid not in special_ids)
        total_non_special = sum(1 for tid in all_token_ids if tid not in special_ids)
        result.coverage = non_unk / total_non_special if total_non_special > 0 else 0.0

        # Top tokens
        result.top_tokens = token_counter.most_common(20)

        return result

    def summary(self, texts: Sequence[str]) -> str:
        """Produce a human-readable summary string."""
        r = self.analyze(texts)
        lines = [
            f"Tokenizer Analysis",
            f"{'=' * 40}",
            f"Texts:          {r.n_texts}",
            f"Characters:     {r.n_chars}",
            f"Bytes (UTF-8):  {r.n_bytes}",
            f"Tokens:         {r.n_tokens}",
            f"",
            f"Compression:",
            f"  Chars/token:  {r.chars_per_token:.2f}",
            f"  Bytes/token:  {r.bytes_per_token:.2f}",
            f"  Tokens/char:  {r.tokens_per_char:.3f}",
            f"",
            f"Token length:",
            f"  Mean:         {r.mean_token_len:.2f}",
            f"  Median:       {r.median_token_len:.2f}",
            f"  Min/Max:      {r.min_token_len}/{r.max_token_len}",
            f"",
            f"Fertility (tokens/word): {r.mean_fertility:.2f}",
            f"Coverage:                {r.coverage:.1%}",
            f"UNK rate:                {r.unk_rate:.2%} ({r.unk_count} tokens)",
            f"",
            f"Vocabulary:",
            f"  Total size:  {r.vocab_size}",
            f"  Merges:      {r.n_merges}",
            f"  Single-char: {r.n_single_chars}",
            f"",
            f"Top 20 tokens (id: count):",
        ]
        for tid, count in r.top_tokens:
            tok = self.tokenizer.vocab.get_by_id(tid)
            piece = tok.piece if tok else "?"
            lines.append(f"  {tid:6d} ({piece!r:20s}): {count}")
        return "\n".join(lines)