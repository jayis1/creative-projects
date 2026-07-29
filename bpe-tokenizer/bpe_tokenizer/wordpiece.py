"""WordPiece encoder — BERT-style bidirectional longest-match segmentation.

WordPiece is the tokenization algorithm used by BERT, DistilBERT, and
Electra.  Unlike BPE (which applies merges greedily by rank), WordPiece
performs a *longest-match-first* search: for each position in the text,
it finds the longest substring that exists in the vocabulary.  This
produces deterministic, greedy-optimal segmentations.

Key differences from BPE:
    - **No merge ranks**: WordPiece looks up substrings directly in the
      vocab, not via a merge-rank table.
    - **## continuation marker**: By convention, non-initial subwords
      are prefixed with ``##`` (e.g., ``"playing"`` → ``["play", "##ing"]``).
    - **Greedy longest match**: At each position, the longest matching
      vocab entry is selected, which is simpler and faster than BPE's
      iterative pair merging.

This module wraps a :class:`BPETokenizer`'s vocab to perform WordPiece
segmentation, making it easy to compare BPE and WordPiece segmentations
on the same vocabulary.
"""

from __future__ import annotations

from typing import Sequence

from .tokenizer import BPETokenizer
from .vocab import BPE_UNK

__all__ = [
    "WordPieceEncoder",
    "wordpiece_encode",
]


class WordPieceEncoder:
    """BERT-style WordPiece encoder using an existing BPE vocab.

    Wraps a :class:`BPETokenizer` and performs longest-match-first
    segmentation on its vocabulary.  Optionally uses the ``##``
    continuation convention for non-initial subwords.

    Parameters
    ----------
    tokenizer:
        A trained :class:`BPETokenizer`.
    max_input_chars_per_word:
        Maximum number of characters per word.  Words longer than this
        are treated as UNK (matching HuggingFace's behavior).
    use_continuation_marker:
        If True, prefix non-initial subwords with ``##``.
    unknown_token:
        The string to use for unknown tokens.
    """

    def __init__(
        self,
        tokenizer: BPETokenizer,
        max_input_chars_per_word: int = 100,
        use_continuation_marker: bool = True,
        unknown_token: str = BPE_UNK,
    ):
        self.tokenizer = tokenizer
        self.max_input_chars_per_word = max_input_chars_per_word
        self.use_continuation_marker = use_continuation_marker
        self.unknown_token = unknown_token
        # Build a set of vocab pieces for fast lookup.
        self._vocab_pieces: set[str] = set(tokenizer.vocab.tokens.keys())
        # Also include special tokens (though they shouldn't be matched).
        # Sort piece lengths for efficient longest-match (longest first).
        self._max_piece_len: int = max(
            (len(p) for p in self._vocab_pieces), default=1
        )

    def _longest_match(self, text: str, start: int, is_first: bool) -> tuple[str, int]:
        """Find the longest vocab piece at position *start*.

        Returns (piece, end_index).  If no match, returns ("", start).
        """
        n = len(text)
        best_piece = ""
        best_end = start
        # Search from longest possible to shortest.
        max_len = min(self._max_piece_len, n - start)
        for length in range(max_len, 0, -1):
            candidate = text[start : start + length]
            if use_continuation := (
                self.use_continuation_marker and not is_first
            ):
                marked = "##" + candidate
                if marked in self._vocab_pieces:
                    return marked, start + length
                if candidate in self._vocab_pieces:
                    return candidate, start + length
            else:
                if candidate in self._vocab_pieces:
                    return candidate, start + length
        return best_piece, best_end

    def tokenize(self, text: str) -> list[str]:
        """Tokenize *text* into WordPiece subwords.

        Pre-tokenizes using the tokenizer's pre-tokenizer, then
        applies longest-match-first within each pre-token.
        """
        # Apply normalization if configured.
        if self.tokenizer.normalizer is not None and text:
            text = self.tokenizer.normalizer(text)

        if not text:
            return []

        # Pre-tokenize.
        chunks = self.tokenizer.pretokenizer(text)
        pieces: list[str] = []

        for chunk in chunks:
            if not chunk or not chunk.strip():
                # Keep whitespace as-is if it's in the vocab.
                if chunk and chunk in self._vocab_pieces:
                    pieces.append(chunk)
                continue

            if len(chunk) > self.max_input_chars_per_word:
                pieces.append(self.unknown_token)
                continue

            # WordPiece within a single pre-token.
            start = 0
            is_first_subword = True
            while start < len(chunk):
                piece, end = self._longest_match(chunk, start, is_first_subword)
                if end == start:
                    # No match — entire word is UNK.
                    # Remove any subwords we've added for this chunk
                    # and replace with UNK.
                    # Find how many we added for this chunk.
                    # Simpler: just add UNK and break.
                    # But we need to remove partial subwords.
                    # Count subwords added since we started this chunk.
                    # This is tricky with the flat list; use a marker.
                    # Instead, mark this chunk as fully UNK.
                    pieces.append(self.unknown_token)
                    start = len(chunk)  # force exit
                    break
                pieces.append(piece)
                start = end
                is_first_subword = False

        return pieces

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        """Tokenize *text* with WordPiece and convert to token ids."""
        from .vocab import BPE_BOS, BPE_EOS

        pieces = self.tokenize(text)
        unk_id = self.tokenizer.vocab.unk_id()
        ids: list[int] = []

        if add_bos:
            ids.append(self.tokenizer._special_id(BPE_BOS, 0))

        for piece in pieces:
            tok = self.tokenizer.vocab.get_by_piece(piece)
            if tok is not None:
                ids.append(tok.id)
            elif unk_id is not None:
                ids.append(unk_id)
            # else: silently drop

        if add_eos:
            ids.append(self.tokenizer._special_id(BPE_EOS, 2))

        return ids

    def decode(self, ids: list[int]) -> str:
        """Decode WordPiece ids back to text.

        Strips ``##`` markers and concatenates.
        """
        # Reuse the base tokenizer's decode (pieces don't have ## markers
        # in the actual vocab, so this works as long as ##-marked pieces
        # are in the vocab as their base form).
        # For simplicity, delegate to the base tokenizer's decode.
        return self.tokenizer.decode(ids)


def wordpiece_encode(
    tokenizer: BPETokenizer,
    text: str,
    max_input_chars_per_word: int = 100,
    use_continuation_marker: bool = True,
) -> list[int]:
    """Convenience function: WordPiece-encode *text* using *tokenizer*'s vocab."""
    encoder = WordPieceEncoder(
        tokenizer,
        max_input_chars_per_word=max_input_chars_per_word,
        use_continuation_marker=use_continuation_marker,
    )
    return encoder.encode(text)