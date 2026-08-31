"""Suffix automaton toolkit."""

from .commands import analysis_payload, execute_batch_jobs
from .config import JobConfig, load_config, parse_job_config
from .core import (
    AnalysisResult,
    MatchLocation,
    MinimalUniqueSubstring,
    RepeatedSubstring,
    StateSummary,
    SuffixAutomaton,
    longest_common_substring,
    longest_common_substring_by_pairs,
)

__all__ = [
    "AnalysisResult",
    "JobConfig",
    "MatchLocation",
    "MinimalUniqueSubstring",
    "RepeatedSubstring",
    "StateSummary",
    "SuffixAutomaton",
    "analysis_payload",
    "execute_batch_jobs",
    "load_config",
    "longest_common_substring",
    "longest_common_substring_by_pairs",
    "parse_job_config",
]
