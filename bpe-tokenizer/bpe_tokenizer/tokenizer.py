"""Core BPE tokenizer: training, encoding, decoding.

This module implements:

* BPE merge training (greedy most-frequent-pair merging with tie-breaking).
* Greedy-rank encoding (longest-match using the learned merge ranks).
* Byte-level mode (GPT-2 style) or character-level mode.
* Special-token handling (PAD/BOS/EOS/UNK).
* Batch encoding with optional BOS/EOS wrapping.
* LRU encode cache.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from .vocab import (
    DEFAULT_SPECIALS,
    BPE_BOS,
    BPE_EOS,
    BPE_UNK,
    BPE_PAD,
    Vocab,
)
from .pretokenize import (
    GPT4_REGEX,
    BytePretokenizer,
    Pretokenizer,
    WordPretokenizer,
    WhitespacePretokenizer,
)
from .cache import EncodeCache
from .exceptions import TrainingError, EncodingError, SerializationError
from .progress import ProgressCallback, ProgressInfo

__all__ = [
    "BPETokenizer",
    "TrainingConfig",
    "TokenizationResult",
    "TokenizerStats",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TrainingConfig:
    """Configuration for BPE training.

    Parameters
    ----------
    vocab_size:
        Target total vocabulary size (specials + regulars).
    byte_mode:
        If True, operate at the byte level (GPT-2 style).  If False,
        operate at the Unicode-codepoint level.
    pretokenizer:
        Name of the pre-tokenizer to use.  One of ``"gpt2"``, ``"gpt4"``,
        ``"llama3"``, ``"whitespace"``, ``"none"``.
    specials:
        Tuple of special-token strings to reserve.
    min_frequency:
        Minimum frequency for a pair to be considered for merging.
    verbose:
        If True, log merge progress.
    """

    vocab_size: int = 1000
    byte_mode: bool = False
    pretokenizer: str = "gpt4"
    specials: tuple[str, ...] = DEFAULT_SPECIALS
    min_frequency: int = 2
    verbose: bool = False
    normalizer_flags: int = 0  # Normalization flag bitmask (0 = no normalization)

    def __post_init__(self) -> None:
        if self.vocab_size < len(self.specials) + 1:
            raise ValueError(
                f"vocab_size ({self.vocab_size}) must be > #specials "
                f"({len(self.specials)})"
            )
        if self.min_frequency < 1:
            raise ValueError("min_frequency must be >= 1")


@dataclass
class TokenizationResult:
    """Result of encoding a single text."""

    ids: list[int]
    pieces: list[str]
    n_tokens: int
    n_chars: int
    n_bytes: int = 0

    def __iter__(self) -> Iterator[int]:
        return iter(self.ids)


@dataclass
class TokenizerStats:
    """Statistics about the tokenizer state."""

    vocab_size: int
    n_specials: int
    n_regulars: int
    n_merges: int
    byte_mode: bool
    cache_size: int
    cache_hits: int
    cache_misses: int


# ---------------------------------------------------------------------------
# BPE Tokenizer
# ---------------------------------------------------------------------------

class BPETokenizer:
    """Byte Pair Encoding tokenizer.

    Parameters
    ----------
    vocab:
        An existing :class:`Vocab` to load.  If None, the tokenizer is
        untrained until :meth:`train` is called.
    pretokenizer:
        A :class:`Pretokenizer` instance, or None to use the default
        (GPT-4 word regex).  Ignored if ``vocab`` is provided and has a
        stored pretokenizer name.
    cache_capacity:
        LRU encode-cache size.  Set to 0 to disable caching.
    """

    def __init__(
        self,
        vocab: Vocab | None = None,
        pretokenizer: Pretokenizer | None = None,
        cache_capacity: int = 8192,
        normalizer: "Normalizer | None" = None,
    ):
        self.vocab: Vocab = vocab or Vocab()
        self.pretokenizer: Pretokenizer = pretokenizer or WordPretokenizer(GPT4_REGEX)
        self.pretokenizer_name: str = "gpt4"
        self._cache = EncodeCache(cache_capacity) if cache_capacity > 0 else None
        # Merge ranks for encoding: maps (a, b) → rank.
        self._merge_ranks: dict[tuple[str, str], int] = {}
        # Optional text normalizer applied before pre-tokenization.
        self.normalizer = normalizer
        if vocab is not None and vocab.tokens:
            self._rebuild_merge_ranks()

    # ------------------------------------------------------------------
    # Pre-tokenizer helpers
    # ------------------------------------------------------------------

    def _make_pretokenizer(self, name: str) -> Pretokenizer:
        from .pretokenize import GPT2_REGEX, LLAMA3_REGEX
        mapping = {
            "gpt2": lambda: WordPretokenizer(GPT2_REGEX),
            "gpt4": lambda: WordPretokenizer(GPT4_REGEX),
            "llama3": lambda: WordPretokenizer(LLAMA3_REGEX),
            "whitespace": WhitespacePretokenizer,
            "none": lambda: _NoSplitPretokenizer(),
        }
        factory = mapping.get(name)
        if factory is None:
            raise ValueError(f"Unknown pretokenizer: {name!r}")
        return factory()

    def _split_to_units(self, text: str) -> list[str]:
        """Split text into base units (bytes or chars) after pre-tokenization."""
        chunks = self.pretokenizer(text)
        units: list[str] = []
        for chunk in chunks:
            if self.vocab.byte_mode:
                # Byte mode: each chunk is already in GPT-2 byte-unicode
                # encoding (if the pretokenizer is BytePretokenizer).  But
                # if a non-byte pretokenizer was used with byte_mode=True,
                # we need to encode each chunk's bytes here.
                if isinstance(self.pretokenizer, BytePretokenizer):
                    units.extend(list(chunk))
                else:
                    encoded = BytePretokenizer.encode_text(chunk)
                    units.extend(list(encoded))
            else:
                units.extend(list(chunk))
        return units

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        corpus: str | Sequence[str],
        config: TrainingConfig | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Train the BPE tokenizer on *corpus*.

        Parameters
        ----------
        corpus:
            A single string or a sequence of strings (documents).
        config:
            Training configuration.  If None, uses defaults.
        progress_callback:
            Optional callback invoked after each merge.  Receives a
            :class:`~bpe_tokenizer.progress.ProgressInfo` instance.
        """
        cfg = config or TrainingConfig()
        self.vocab = Vocab(byte_mode=cfg.byte_mode)
        self.pretokenizer = self._make_pretokenizer(cfg.pretokenizer)
        self.pretokenizer_name = cfg.pretokenizer
        # Set up normalizer if flags are provided.
        if cfg.normalizer_flags:
            from .normalizer import Normalization, Normalizer
            self.normalizer = Normalizer(Normalization(cfg.normalizer_flags))
        else:
            self.normalizer = None
        if cfg.byte_mode:
            # In byte mode, the pre-tokenizer should produce byte-encoded text.
            self.pretokenizer = BytePretokenizer()
            self.pretokenizer_name = "byte"

        # Add specials.
        for sp in cfg.specials:
            self.vocab.add_special(sp, is_unk=(sp == BPE_UNK))

        # Build the corpus as a list of documents.
        if isinstance(corpus, str):
            docs = [corpus]
        else:
            docs = list(corpus)

        # Pre-tokenize all documents and collect word frequencies.
        word_freqs: Counter[str] = Counter()
        # Each unique word → list of units (symbols).
        word_symbols: dict[str, list[str]] = {}

        for doc in docs:
            # Apply normalization before pre-tokenization during training too.
            if self.normalizer is not None:
                doc = self.normalizer(doc)
            chunks = self.pretokenizer(doc)
            for chunk in chunks:
                if not chunk:
                    continue
                word_freqs[chunk] += 1
                if chunk not in word_symbols:
                    word_symbols[chunk] = self._chunk_to_units(chunk, cfg.byte_mode)

        # Build the initial base vocab from all unique units.
        all_units: set[str] = set()
        for syms in word_symbols.values():
            all_units.update(syms)
        for u in sorted(all_units):
            self.vocab.add_token(u, u.encode("utf-8"), rank=0)

        # Calculate number of merges needed.
        n_specials = len(self.vocab.specials)
        n_base = len(all_units)
        max_merges = max(0, cfg.vocab_size - n_specials - n_base)

        if cfg.verbose:
            logger.info(
                "Training: %d unique words, %d base units, %d specials, "
                "target %d → up to %d merges",
                len(word_freqs), n_base, n_specials, cfg.vocab_size, max_merges,
            )

        # ---- Initial pair counts (computed once) ----
        pair_counts: Counter[tuple[str, str]] = Counter()
        for word, syms in word_symbols.items():
            freq = word_freqs[word]
            for i in range(len(syms) - 1):
                pair_counts[(syms[i], syms[i + 1])] += freq

        # Iteratively merge the most frequent pair.
        merge_rank = 1
        merges_done = 0
        while merges_done < max_merges:
            if not pair_counts:
                break  # nothing left to merge

            # Select the best pair.
            # Tie-breaking: highest count, then lexicographically smallest
            # pair (for deterministic training across runs).
            # We use min() with key (-count, pair) so that:
            #   - higher count → lower -count → preferred
            #   - on ties, lexicographically smaller pair → preferred
            best_pair = min(pair_counts, key=lambda p: (-pair_counts[p], p))
            best_count = pair_counts[best_pair]

            if best_count < cfg.min_frequency:
                break

            # Create the merged symbol.
            merged = best_pair[0] + best_pair[1]
            self.vocab.add_token(
                merged,
                merged.encode("utf-8"),
                rank=merge_rank,
                freq=best_count,
            )
            merge_rank += 1

            # Apply the merge to all words, updating pair_counts incrementally.
            self._apply_merge_incremental(
                word_symbols, word_freqs, best_pair, merged, pair_counts,
            )

            merges_done += 1
            if cfg.verbose and merges_done % 50 == 0:
                logger.info("  merge #%d: %r (count=%d)", merges_done, merged, best_count)

            if progress_callback is not None:
                progress_callback(ProgressInfo(
                    iteration=merges_done,
                    max_merges=max_merges,
                    merged_pair=best_pair,
                    merged_token=merged,
                    merge_count=best_count,
                    current_vocab_size=self.vocab.size(),
                ))

        self._rebuild_merge_ranks()
        if self._cache is not None:
            self._cache.clear()
        if cfg.verbose:
            logger.info("Training complete: %d merges, vocab size %d",
                        merges_done, self.vocab.size())

    def train_from_file(
        self,
        path: str | Path,
        config: TrainingConfig | None = None,
        progress_callback: ProgressCallback | None = None,
        encoding: str = "utf-8",
    ) -> None:
        """Train on a corpus read from a file.

        The file is read as a single string and passed to :meth:`train`.

        Parameters
        ----------
        path:
            Path to the corpus file.
        config:
            Training configuration.
        progress_callback:
            Optional progress callback.
        encoding:
            File encoding (default: utf-8).
        """
        p = Path(path)
        if not p.exists():
            raise TrainingError(f"Corpus file not found: {p}")
        text = p.read_text(encoding=encoding)
        self.train(text, config, progress_callback)

    def _chunk_to_units(self, chunk: str, byte_mode: bool) -> list[str]:
        """Convert a pre-token chunk to a list of base units."""
        if byte_mode:
            encoded = BytePretokenizer.encode_text(chunk)
            return list(encoded)
        return list(chunk)

    @staticmethod
    def _apply_merge(word_symbols: dict[str, list[str]], pair: tuple[str, str], merged: str) -> None:
        """Apply a merge *pair* → *merged* across all words in-place.

        .. deprecated::
            Kept for backward compatibility.  New code should use
            :meth:`_apply_merge_incremental` which also updates pair
            counts incrementally for better performance.
        """
        for word, syms in word_symbols.items():
            if len(syms) < 2:
                continue
            new_syms: list[str] = []
            i = 0
            while i < len(syms):
                if i < len(syms) - 1 and syms[i] == pair[0] and syms[i + 1] == pair[1]:
                    new_syms.append(merged)
                    i += 2
                else:
                    new_syms.append(syms[i])
                    i += 1
            word_symbols[word] = new_syms

    @staticmethod
    def _apply_merge_incremental(
        word_symbols: dict[str, list[str]],
        word_freqs: Counter[str],
        pair: tuple[str, str],
        merged: str,
        pair_counts: Counter[tuple[str, str]],
    ) -> None:
        """Apply a merge and update *pair_counts* incrementally.

        Instead of recomputing all pair counts from scratch each
        iteration (O(total_symbols) per merge), this method only
        adjusts counts for words that contained the merged pair,
        giving a significant speedup for large vocabularies.
        """
        left, right = pair
        merged_sym = merged

        for word, syms in word_symbols.items():
            if len(syms) < 2:
                continue
            # Quick check: does this word contain the pair at all?
            # Only process words that have at least one occurrence.
            has_pair = False
            for i in range(len(syms) - 1):
                if syms[i] == left and syms[i + 1] == right:
                    has_pair = True
                    break
            if not has_pair:
                continue

            freq = word_freqs[word]
            # Build the new symbol list while tracking pair changes.
            new_syms: list[str] = []
            i = 0
            while i < len(syms):
                if i < len(syms) - 1 and syms[i] == left and syms[i + 1] == right:
                    # We're merging syms[i] and syms[i+1] into merged_sym.
                    # Decrement the pair count for (left, right).
                    pair_counts[(left, right)] -= freq

                    # The old pair (syms[i-1], left) is gone — decrement it.
                    # But only if there was a preceding symbol in new_syms.
                    if new_syms:
                        old_left_pair = (new_syms[-1], left)
                        pair_counts[old_left_pair] -= freq
                        # The new pair (new_syms[-1], merged_sym) is created.
                        new_left_pair = (new_syms[-1], merged_sym)
                        pair_counts[new_left_pair] += freq

                    # The old pair (right, syms[i+2]) is gone — decrement.
                    if i + 2 < len(syms):
                        old_right_pair = (right, syms[i + 2])
                        pair_counts[old_right_pair] -= freq
                        # The new pair (merged_sym, syms[i+2]) is created.
                        new_right_pair = (merged_sym, syms[i + 2])
                        pair_counts[new_right_pair] += freq

                    new_syms.append(merged_sym)
                    i += 2
                else:
                    new_syms.append(syms[i])
                    i += 1
            word_symbols[word] = new_syms

        # Remove zero/negative counts to keep the Counter clean.
        # (pair_counts may have entries with 0 or negative counts after
        # decrements; we remove them to avoid selecting them as "best".)
        to_remove = [p for p, c in pair_counts.items() if c <= 0]
        for p in to_remove:
            del pair_counts[p]

    def _rebuild_merge_ranks(self) -> None:
        """Rebuild the merge-rank lookup from the vocab.

        The merge rank for a pair (A, B) is the rank of the token "AB".
        Tokens with rank 0 are base tokens (no merge).

        For each merged token (rank > 0), we reconstruct which (left,
        right) pair produced it by finding a split point where both
        halves exist in the vocab with lower rank.  This is needed
        because we don't store the split point explicitly during
        training.
        """
        self._merge_ranks = {}
        for piece, tok in self.vocab.tokens.items():
            if tok.rank == 0 or len(piece) < 2:
                continue
            # Find the split where both parts are in the vocab with rank < tok.rank.
            best_split = None
            for split_pos in range(1, len(piece)):
                left = piece[:split_pos]
                right = piece[split_pos:]
                if left in self.vocab.tokens and right in self.vocab.tokens:
                    left_rank = self.vocab.tokens[left].rank
                    right_rank = self.vocab.tokens[right].rank
                    if left_rank < tok.rank and right_rank < tok.rank:
                        best_split = (left, right)
                        break
            if best_split is not None:
                self._merge_ranks[best_split] = tok.rank

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def _encode_units(self, units: list[str]) -> list[int]:
        """Apply BPE merges to a list of base units and return token ids.

        Uses the standard greedy-merge algorithm: repeatedly find the
        pair with the lowest merge rank and merge it.
        """
        if not units:
            return []
        # Work with a list of symbols (strings), then convert to ids.
        symbols: list[str] = list(units)

        while len(symbols) > 1:
            # Find the pair with the lowest rank.
            best_rank = None
            best_idx = -1
            for i in range(len(symbols) - 1):
                pair = (symbols[i], symbols[i + 1])
                rank = self._merge_ranks.get(pair)
                if rank is not None and (best_rank is None or rank < best_rank):
                    best_rank = rank
                    best_idx = i
            if best_idx == -1:
                break  # no more merges
            # Merge at best_idx.
            merged = symbols[best_idx] + symbols[best_idx + 1]
            symbols[best_idx:best_idx + 2] = [merged]

        # Convert symbols to ids.
        result: list[int] = []
        unk_id = self.vocab.unk_id()
        for sym in symbols:
            tok = self.vocab.tokens.get(sym)
            if tok is not None:
                result.append(tok.id)
            elif unk_id is not None:
                result.append(unk_id)
            # else: silently drop (no UNK configured)
        return result

    def encode(
        self,
        text: str,
        add_bos: bool = False,
        add_eos: bool = False,
    ) -> list[int]:
        """Encode *text* into a list of token ids.

        If a normalizer is configured, it is applied to *text* before
        pre-tokenization.
        """
        # Normalize before anything else.
        if self.normalizer is not None and text:
            text = self.normalizer(text)

        if not text:
            ids: list[int] = []
            if add_bos:
                ids.append(self._special_id(BPE_BOS, 0))
            if add_eos:
                ids.append(self._special_id(BPE_EOS, 2))
            return ids

        # Check cache (cache key includes normalization result).
        cache_key = f"{add_bos}:{add_eos}:{text}"
        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        units = self._split_to_units(text)
        ids = self._encode_units(units)

        if add_bos:
            ids = [self._special_id(BPE_BOS, 0)] + ids
        if add_eos:
            ids = ids + [self._special_id(BPE_EOS, 2)]

        if self._cache is not None:
            self._cache.put(cache_key, ids)
        return ids

    def encode_advanced(
        self,
        text: str,
        add_bos: bool = False,
        add_eos: bool = False,
        max_length: int | None = None,
        truncation: str = "right",
        return_attention_mask: bool = False,
        pad_id: int | None = None,
    ) -> dict[str, list[int]]:
        """Encode with advanced post-processing options.

        Returns a dict with keys ``"input_ids"`` and optionally
        ``"attention_mask"``.

        Parameters
        ----------
        max_length:
            Maximum sequence length (after BOS/EOS).  Excess tokens are
            truncated according to *truncation*.
        truncation:
            One of ``"right"``, ``"left"``, ``"middle"``.
        return_attention_mask:
            If True, also return a binary attention mask.
        pad_id:
            Padding token id (only used if *return_attention_mask* is
            True and the sequence is shorter than *max_length*).
        """
        from .postprocess import TruncationStrategy, truncate, make_attention_mask

        ids = self.encode(text, add_bos=add_bos, add_eos=add_eos)

        if max_length is not None:
            special_ids = {s.id for s in self.vocab.specials.values()}
            strat = TruncationStrategy(truncation)
            ids = truncate(ids, max_length, strat, keep_specials=True,
                           special_ids=special_ids)

        # Determine the effective pad id.
        eff_pad = pad_id if pad_id is not None else self._special_id(BPE_PAD, 0)

        # Pad if needed: when max_length is set and return_attention_mask
        # is True, always pad to max_length.  Also pad when pad_id is
        # explicitly provided.
        should_pad = (pad_id is not None) or (return_attention_mask and max_length is not None)
        if should_pad and max_length is not None and len(ids) < max_length:
            ids = ids + [eff_pad] * (max_length - len(ids))

        result: dict[str, list[int]] = {"input_ids": ids}
        if return_attention_mask:
            result["attention_mask"] = make_attention_mask(ids, eff_pad)
        return result

    def _special_id(self, piece: str, default: int) -> int:
        """Get the id of a special token, or *default* if absent."""
        st = self.vocab.specials.get(piece)
        return st.id if st is not None else default

    def encode_batch(
        self,
        texts: Sequence[str],
        add_bos: bool = False,
        add_eos: bool = False,
        max_length: int | None = None,
        padding: bool = False,
        pad_id: int | None = None,
    ) -> list[list[int]]:
        """Encode a batch of texts.

        If *padding* is True, all sequences are padded to ``max_length``
        (or the longest sequence if *max_length* is None) with
        ``pad_id`` (default: the PAD special token id, or 0).
        """
        results = [self.encode(t, add_bos=add_bos, add_eos=add_eos) for t in texts]
        if padding:
            from .postprocess import TruncationStrategy, truncate as _truncate
            special_ids = {s.id for s in self.vocab.specials.values()}
            if max_length is None:
                max_length = max(len(r) for r in results) if results else 0
            if pad_id is None:
                pad_id = self._special_id(BPE_PAD, 0)
            for i, r in enumerate(results):
                if len(r) > max_length:
                    # Truncate preserving special tokens at start/end.
                    results[i] = _truncate(r, max_length, TruncationStrategy.RIGHT,
                                           keep_specials=True, special_ids=special_ids)
                if len(results[i]) < max_length:
                    results[i] = results[i] + [pad_id] * (max_length - len(results[i]))
        return results

    def encode_annotated(self, text: str) -> TokenizationResult:
        """Encode and return a :class:`TokenizationResult` with pieces."""
        ids = self.encode(text)
        pieces = self.id_to_pieces(ids)
        return TokenizationResult(
            ids=ids,
            pieces=pieces,
            n_tokens=len(ids),
            n_chars=len(text),
            n_bytes=len(text.encode("utf-8")),
        )

    # ------------------------------------------------------------------
    # Decoding
    # ------------------------------------------------------------------

    def decode(self, ids: list[int]) -> str:
        """Decode a list of token ids back to a string.

        Special tokens are skipped (they have no text content).
        """
        special_ids = {s.id for s in self.vocab.specials.values()}
        pieces: list[str] = []
        for tid in ids:
            if tid in special_ids:
                continue
            tok = self.vocab.get_by_id(tid)
            if tok is None:
                continue
            # Regular token — append its piece.
            pieces.append(tok.piece)

        if self.vocab.byte_mode:
            joined = "".join(pieces)
            return BytePretokenizer.decode_text(joined)
        return "".join(pieces)

    def id_to_pieces(self, ids: list[int]) -> list[str]:
        """Convert a list of ids to their string pieces."""
        result: list[str] = []
        for tid in ids:
            tok = self.vocab.get_by_id(tid)
            if tok is None:
                result.append(BPE_UNK)
            else:
                result.append(tok.piece)
        return result

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        # Serialize normalizer flags if a normalizer is configured.
        norm_flags = 0
        if self.normalizer is not None:
            norm_flags = int(self.normalizer.flags.value)
        return {
            "vocab": self.vocab.to_dict(),
            "pretokenizer": self.pretokenizer_name,
            "normalizer_flags": norm_flags,
            "merge_ranks": [
                {"left": a, "right": b, "rank": r}
                for (a, b), r in sorted(self._merge_ranks.items(), key=lambda x: x[1])
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "BPETokenizer":
        vocab = Vocab.from_dict(d["vocab"])
        norm_flags = d.get("normalizer_flags", 0)
        normalizer = None
        if norm_flags:
            from .normalizer import Normalization, Normalizer
            normalizer = Normalizer(Normalization(norm_flags))
        tok = cls(vocab=vocab, cache_capacity=0, normalizer=normalizer)
        tok.pretokenizer_name = d.get("pretokenizer", "gpt4")
        tok.pretokenizer = tok._make_pretokenizer(tok.pretokenizer_name)
        tok._rebuild_merge_ranks()
        return tok

    @classmethod
    def from_json(cls, s: str) -> "BPETokenizer":
        return cls.from_dict(json.loads(s))

    def save(self, path: str) -> None:
        """Save the tokenizer to a JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "BPETokenizer":
        """Load a tokenizer from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    # ------------------------------------------------------------------
    # Stats / utility
    # ------------------------------------------------------------------

    def stats(self) -> TokenizerStats:
        cache_stats = self._cache.stats() if self._cache else {"size": 0, "hits": 0, "misses": 0}
        return TokenizerStats(
            vocab_size=self.vocab.size(),
            n_specials=len(self.vocab.specials),
            n_regulars=self.vocab.regular_size(),
            n_merges=len(self._merge_ranks),
            byte_mode=self.vocab.byte_mode,
            cache_size=cache_stats["size"],
            cache_hits=cache_stats["hits"],
            cache_misses=cache_stats["misses"],
        )

    def vocab_size(self) -> int:
        return self.vocab.size()

    @property
    def cache(self) -> EncodeCache | None:
        return self._cache

    def clear_cache(self) -> None:
        if self._cache is not None:
            self._cache.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _NoSplitPretokenizer(Pretokenizer):
    """Pre-tokenizer that returns the whole text as a single chunk."""

    def pretokenize(self, text: str) -> list[str]:
        return [text] if text else []


class SpecialTokenStub:
    """Placeholder used in isinstance check in decode().

    This is a workaround: in :meth:`BPETokenizer.decode` we need to check
    whether a token is a SpecialToken, but we can't import SpecialToken
    at that point in the code due to the import structure.  Using a stub
    here lets the isinstance check succeed without circular imports.
    """
    pass


def lexicographic_key(pair: tuple[str, str]) -> tuple[str, str]:
    """Tie-breaking key: lexicographically smallest pair first."""
    return pair