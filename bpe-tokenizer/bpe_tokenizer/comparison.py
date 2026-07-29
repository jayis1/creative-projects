"""Tokenizer comparison tool.

Compares two tokenizers on a shared corpus, reporting:
    - Agreement rate (fraction of identical id sequences)
    - Average token count difference
    - Compression comparison (chars/token for each)
    - Per-text side-by-side comparison
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .tokenizer import BPETokenizer

__all__ = [
    "ComparisonResult",
    "TokenizerComparison",
]


@dataclass
class ComparisonResult:
    """Results of comparing two tokenizers."""

    n_texts: int = 0
    agreement_count: int = 0          # how many texts produced identical ids
    avg_tokens_a: float = 0.0
    avg_tokens_b: float = 0.0
    avg_token_diff: float = 0.0       # mean(abs(len_a - len_b))
    chars_per_token_a: float = 0.0
    chars_per_token_b: float = 0.0
    total_chars: int = 0
    total_tokens_a: int = 0
    total_tokens_b: int = 0
    per_text: list[dict] = field(default_factory=list)

    @property
    def agreement_rate(self) -> float:
        """Fraction of texts that produced identical id sequences."""
        return self.agreement_count / self.n_texts if self.n_texts > 0 else 0.0


class TokenizerComparison:
    """Compare two trained :class:`BPETokenizer` instances.

    Parameters
    ----------
    tokenizer_a:
        The first tokenizer.
    tokenizer_b:
        The second tokenizer.
    """

    def __init__(self, tokenizer_a: BPETokenizer, tokenizer_b: BPETokenizer):
        self.tok_a = tokenizer_a
        self.tok_b = tokenizer_b

    def compare(self, texts: Sequence[str]) -> ComparisonResult:
        """Compare tokenizers on *texts* and return detailed results."""
        result = ComparisonResult()
        total_chars = 0
        total_tokens_a = 0
        total_tokens_b = 0
        agreement = 0
        total_diff = 0.0

        for i, text in enumerate(texts):
            if not text:
                continue
            result.n_texts += 1
            total_chars += len(text)

            ids_a = self.tok_a.encode(text)
            ids_b = self.tok_b.encode(text)

            total_tokens_a += len(ids_a)
            total_tokens_b += len(ids_b)
            total_diff += abs(len(ids_a) - len(ids_b))

            if ids_a == ids_b:
                agreement += 1

            result.per_text.append({
                "index": i,
                "text": text[:80],  # truncate for readability
                "ids_a": ids_a,
                "ids_b": ids_b,
                "len_a": len(ids_a),
                "len_b": len(ids_b),
                "match": ids_a == ids_b,
            })

        result.agreement_count = agreement
        result.total_chars = total_chars
        result.total_tokens_a = total_tokens_a
        result.total_tokens_b = total_tokens_b

        if result.n_texts > 0:
            result.avg_tokens_a = total_tokens_a / result.n_texts
            result.avg_tokens_b = total_tokens_b / result.n_texts
            result.avg_token_diff = total_diff / result.n_texts

        if total_tokens_a > 0:
            result.chars_per_token_a = total_chars / total_tokens_a
        if total_tokens_b > 0:
            result.chars_per_token_b = total_chars / total_tokens_b

        return result

    def summary(self, texts: Sequence[str]) -> str:
        """Produce a human-readable comparison summary."""
        r = self.compare(texts)
        lines = [
            "Tokenizer Comparison",
            "=" * 50,
            f"Texts compared:      {r.n_texts}",
            f"Total characters:    {r.total_chars}",
            f"",
            f"Tokenizer A:",
            f"  Total tokens:      {r.total_tokens_a}",
            f"  Avg tokens/text:   {r.avg_tokens_a:.2f}",
            f"  Chars/token:       {r.chars_per_token_a:.2f}",
            f"  Vocab size:        {self.tok_a.vocab_size()}",
            f"",
            f"Tokenizer B:",
            f"  Total tokens:      {r.total_tokens_b}",
            f"  Avg tokens/text:   {r.avg_tokens_b:.2f}",
            f"  Chars/token:       {r.chars_per_token_b:.2f}",
            f"  Vocab size:        {self.tok_b.vocab_size()}",
            f"",
            f"Agreement rate:      {r.agreement_rate:.1%} ({r.agreement_count}/{r.n_texts})",
            f"Avg token diff:      {r.avg_token_diff:.2f}",
        ]

        # Show mismatches (up to 5).
        mismatches = [t for t in r.per_text if not t["match"]][:5]
        if mismatches:
            lines.append("")
            lines.append(f"Mismatches (showing {len(mismatches)} of "
                         f"{r.n_texts - r.agreement_count}):")
            for m in mismatches:
                lines.append(f"  [{m['index']}] {m['text']!r}")
                lines.append(f"    A: {m['ids_a']} (len={m['len_a']})")
                lines.append(f"    B: {m['ids_b']} (len={m['len_b']})")

        return "\n".join(lines)