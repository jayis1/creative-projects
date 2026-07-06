"""
Occurrence / match analysis utilities for FM-Index results.

Provides functions to:
  - compute match statistics (count, density, coverage)
  - group matches by proximity into "clusters"
  - detect overlaps between matches
  - build a coverage mask over the text
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .index import FMIndex, FMIndexMatch


@dataclass
class MatchCluster:
    """A group of matches that are close together in the text."""

    start: int
    """First match position in the cluster."""

    end: int
    """End of the last match (exclusive)."""

    matches: List[int]
    """Positions of the matches in the cluster."""

    @property
    def size(self) -> int:
        return len(self.matches)

    @property
    def span(self) -> int:
        return self.end - self.start


def cluster_matches(
    positions: List[int],
    gap: int = 0,
) -> List[MatchCluster]:
    """Group sorted *positions* into clusters where consecutive matches are
    at most *gap* apart.

    A gap of 0 means consecutive matches must be adjacent (differ by 1) to
    cluster.  A larger gap allows looser clustering.
    """
    if not positions:
        return []
    positions = sorted(positions)
    clusters: List[MatchCluster] = []
    current = [positions[0]]
    for p in positions[1:]:
        if p - current[-1] <= gap + 1:
            current.append(p)
        else:
            clusters.append(
                MatchCluster(
                    start=current[0],
                    end=current[-1] + 1,
                    matches=list(current),
                )
            )
            current = [p]
    clusters.append(
        MatchCluster(start=current[0], end=current[-1] + 1, matches=list(current))
    )
    return clusters


def coverage_mask(
    positions: List[int],
    pattern_len: int,
    text_len: int,
) -> List[bool]:
    """Return a boolean mask of length *text_len* marking covered positions."""
    mask = [False] * text_len
    for p in positions:
        for j in range(pattern_len):
            if 0 <= p + j < text_len:
                mask[p + j] = True
    return mask


def coverage_stats(
    positions: List[int],
    pattern_len: int,
    text_len: int,
) -> Dict[str, float]:
    """Return coverage statistics for a set of matches."""
    mask = coverage_mask(positions, pattern_len, text_len)
    covered = sum(mask)
    return {
        "matches": len(positions),
        "covered": covered,
        "text_len": text_len,
        "coverage": covered / text_len if text_len else 0.0,
        "density": len(positions) / text_len if text_len else 0.0,
    }


def find_overlaps(
    matches: List[FMIndexMatch],
) -> List[Tuple[int, int]]:
    """Return pairs of indices into *matches* that overlap each other."""
    sorted_matches = sorted(enumerate(matches), key=lambda x: x[1].position)
    overlaps: List[Tuple[int, int]] = []
    for i in range(len(sorted_matches)):
        idx_i, m_i = sorted_matches[i]
        plen_i = len(m_i.pattern)
        end_i = m_i.position + plen_i
        for j in range(i + 1, len(sorted_matches)):
            idx_j, m_j = sorted_matches[j]
            if m_j.position >= end_i:
                break
            overlaps.append((idx_i, idx_j))
    return overlaps