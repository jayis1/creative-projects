"""Compression analysis and metrics utilities.

Provides tools for analyzing data compressibility: entropy calculation,
optimal compression ratio estimation, frequency analysis, etc.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


def shannon_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data in bits per symbol.

    Entropy measures the average information content per symbol.
    Maximum entropy for byte data is 8 bits (uniform distribution).

    Args:
        data: Input byte sequence.

    Returns:
        Entropy in bits per symbol (0.0 to 8.0).
    """
    if not data:
        return 0.0

    freq: Dict[int, int] = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1

    n = len(data)
    entropy = 0.0
    for count in freq.values():
        if count > 0:
            p = count / n
            entropy -= p * math.log2(p)

    return entropy


def frequency_distribution(data: bytes) -> Dict[int, float]:
    """Calculate frequency distribution of byte values.

    Args:
        data: Input byte sequence.

    Returns:
        Dict mapping byte value to relative frequency.
    """
    if not data:
        return {}
    freq: Dict[int, int] = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    n = len(data)
    return {b: count / n for b, count in freq.items()}


def optimal_compression_ratio(data: bytes) -> float:
    """Estimate the optimal (theoretical) compression ratio.

    Based on Shannon entropy: the theoretical minimum bits per symbol.

    Args:
        data: Input byte sequence.

    Returns:
        Ratio of compressed to original size (0.0 to 1.0).
    """
    if not data:
        return 0.0
    entropy = shannon_entropy(data)
    return entropy / 8.0


def compressibility_score(data: bytes) -> float:
    """Score how compressible data is, from 0.0 (random) to 1.0 (maximally compressible).

    Args:
        data: Input byte sequence.

    Returns:
        Compressibility score.
    """
    if not data:
        return 0.0
    entropy = shannon_entropy(data)
    # 1.0 means entropy=0 (all same byte), 0.0 means entropy=8 (random)
    return 1.0 - (entropy / 8.0)


def byte_histogram(data: bytes) -> List[int]:
    """Build a histogram of byte values (0-255).

    Args:
        data: Input byte sequence.

    Returns:
        List of 256 counts.
    """
    hist = [0] * 256
    for b in data:
        hist[b] += 1
    return hist


def unique_byte_count(data: bytes) -> int:
    """Count the number of distinct byte values in data."""
    return len(set(data))


def redundancy(data: bytes) -> float:
    """Calculate data redundancy as 1 - (actual_entropy / max_entropy).

    High redundancy means data is very compressible.

    Args:
        data: Input byte sequence.

    Returns:
        Redundancy value (0.0 to 1.0).
    """
    if not data:
        return 0.0
    n_unique = unique_byte_count(data)
    if n_unique <= 1:
        return 1.0
    entropy = shannon_entropy(data)
    max_entropy = math.log2(n_unique)
    return 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.0


def analyze(data: bytes) -> Dict[str, float]:
    """Perform a comprehensive analysis of data compressibility.

    Args:
        data: Input byte sequence.

    Returns:
        Dict with analysis metrics.
    """
    return {
        "size_bytes": len(data),
        "unique_bytes": unique_byte_count(data),
        "entropy_bits": shannon_entropy(data),
        "optimal_ratio": optimal_compression_ratio(data),
        "compressibility": compressibility_score(data),
        "redundancy": redundancy(data),
    }