"""Post-processing of token id sequences.

Provides filters that run *after* encoding, such as truncation
strategies, attention-mask generation, and special-token deduplication.
"""

from __future__ import annotations

from enum import Enum
from typing import Sequence

__all__ = [
    "TruncationStrategy",
    "truncate",
    "make_attention_mask",
    "strip_specials",
]


class TruncationStrategy(Enum):
    """Where to truncate when a sequence is too long."""

    RIGHT = "right"   # Remove tokens from the end
    LEFT = "left"     # Remove tokens from the beginning
    MIDDLE = "middle" # Remove tokens from the middle (keep head & tail)


def truncate(
    ids: list[int],
    max_length: int,
    strategy: TruncationStrategy = TruncationStrategy.RIGHT,
    keep_specials: bool = True,
    special_ids: set[int] | None = None,
) -> list[int]:
    """Truncate *ids* to at most *max_length* tokens.

    If *keep_specials* is True, special tokens (BOS/EOS) at the start/end
    are preserved and only the content tokens are truncated.
    """
    if len(ids) <= max_length:
        return list(ids)

    if not keep_specials or special_ids is None:
        if strategy == TruncationStrategy.RIGHT:
            return ids[:max_length]
        elif strategy == TruncationStrategy.LEFT:
            return ids[-max_length:]
        else:  # MIDDLE
            half = max_length // 2
            return ids[:half] + ids[-(max_length - half):]

    # Separate leading/trailing specials from content.
    lead_specials: list[int] = []
    trail_specials: list[int] = []
    content: list[int] = list(ids)

    # Strip leading specials.
    while content and content[0] in special_ids:
        lead_specials.append(content.pop(0))
    # Strip trailing specials.
    while content and content[-1] in special_ids:
        trail_specials.insert(0, content.pop())

    budget = max_length - len(lead_specials) - len(trail_specials)
    if budget <= 0:
        # Not enough room for any content — just return specials (trimmed).
        return (lead_specials + trail_specials)[:max_length]

    if strategy == TruncationStrategy.RIGHT:
        content = content[:budget]
    elif strategy == TruncationStrategy.LEFT:
        content = content[-budget:]
    else:  # MIDDLE
        half = budget // 2
        content = content[:half] + content[-(budget - half):]

    return lead_specials + content + trail_specials


def make_attention_mask(ids: list[int], pad_id: int) -> list[int]:
    """Create a binary attention mask: 1 for real tokens, 0 for padding."""
    return [0 if tid == pad_id else 1 for tid in ids]


def strip_specials(ids: list[int], special_ids: set[int]) -> list[int]:
    """Remove all special-token ids from *ids*."""
    return [tid for tid in ids if tid not in special_ids]