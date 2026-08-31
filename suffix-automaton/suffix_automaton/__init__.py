"""Suffix automaton toolkit."""

from .core import (
    AnalysisResult,
    MatchLocation,
    RepeatedSubstring,
    StateSummary,
    SuffixAutomaton,
    longest_common_substring,
    longest_common_substring_by_pairs,
)

__all__ = [
    "AnalysisResult",
    "MatchLocation",
    "RepeatedSubstring",
    "StateSummary",
    "SuffixAutomaton",
    "longest_common_substring",
    "longest_common_substring_by_pairs",
]
