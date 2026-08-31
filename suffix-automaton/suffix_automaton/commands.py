"""Command execution helpers for CLI and config-driven workflows."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Sequence

from .config import JobConfig, parse_job_config
from .core import SuffixAutomaton, longest_common_substring, longest_common_substring_by_pairs


def resolve_text(*, text: str | None, file: Path | None) -> str:
    """Resolve text from a literal string or file path."""
    if text is not None:
        return text
    if file is None:
        raise ValueError("expected either text or file input")
    return file.read_text(encoding="utf-8")


def analysis_payload(automaton: SuffixAutomaton) -> dict[str, Any]:
    """Build a rich analysis report payload."""
    result = asdict(automaton.analysis())
    result["substring_complexity_by_length"] = automaton.substring_complexity_by_length()
    result["minimal_unique_substrings"] = [asdict(item) for item in automaton.minimal_unique_substrings()]
    return result


def execute_text_command(command: str, automaton: SuffixAutomaton, config: JobConfig) -> Any:
    """Execute a single-text command and return a JSON-serializable payload."""
    if command == "analyze":
        return analysis_payload(automaton)
    if command == "contains":
        if config.substring is None:
            raise ValueError("contains requires substring")
        return {"substring": config.substring, "contains": automaton.contains(config.substring)}
    if command == "count":
        if config.substring is None:
            raise ValueError("count requires substring")
        return {"substring": config.substring, "occurrences": automaton.occurrence_count(config.substring)}
    if command == "locate":
        if config.substring is None:
            raise ValueError("locate requires substring")
        return [asdict(item) for item in automaton.locate(config.substring, limit=config.limit)]
    if command == "export":
        return automaton.to_dict()
    if command == "dot":
        return automaton.to_graphviz()
    if command == "kth":
        if config.k is None:
            raise ValueError("kth requires k")
        return {"k": config.k, "substring": automaton.kth_distinct_substring(config.k)}
    if command == "absent":
        alphabet = None if config.alphabet is None else list(config.alphabet)
        return {"substring": automaton.shortest_absent_substring(alphabet=alphabet)}
    if command == "repeats":
        return [
            asdict(item)
            for item in automaton.top_repeated_substrings(
                limit=config.limit or 10,
                min_length=config.min_length or 1,
            )
        ]
    if command == "complexity":
        return automaton.substring_complexity_by_length()
    if command == "mus":
        rows = [asdict(item) for item in automaton.minimal_unique_substrings()]
        return rows if config.limit is None else rows[: config.limit]
    raise ValueError(f"unsupported text command: {command}")


def execute_lcs_command(strings: Sequence[str], *, pairwise: bool) -> dict[str, Any]:
    """Execute a multi-string LCS report."""
    payload: dict[str, Any] = {"longest_common_substring": longest_common_substring(strings)}
    if pairwise:
        payload["pairwise"] = {
            f"{left}-{right}": value
            for (left, right), value in longest_common_substring_by_pairs(strings).items()
        }
    return payload


def render_payload(payload: Any, *, as_json: bool) -> str:
    """Render a payload as JSON or plain text."""
    if isinstance(payload, str):
        return payload
    if as_json:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if isinstance(payload, dict):
        return "\n".join(f"{key}: {value}" for key, value in payload.items())
    if isinstance(payload, list):
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return str(payload)


def execute_batch_jobs(document: dict[str, Any]) -> dict[str, Any]:
    """Execute jobs from a config document."""
    if not isinstance(document, dict):
        raise TypeError("config root must be a dictionary")
    jobs = document.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("config must contain a non-empty jobs list")

    results: list[dict[str, Any]] = []
    for index, raw_job in enumerate(jobs, start=1):
        if not isinstance(raw_job, dict):
            raise TypeError(f"job {index} must be a dictionary")
        command = raw_job.get("command")
        if not isinstance(command, str):
            raise TypeError(f"job {index} command must be a string")
        config = parse_job_config(raw_job)
        if command == "lcs":
            if config.strings is None or len(config.strings) < 2:
                raise ValueError(f"job {index} lcs requires at least two strings")
            payload = execute_lcs_command(config.strings, pairwise=config.pairwise)
        else:
            text = resolve_text(text=config.text, file=config.file)
            automaton = SuffixAutomaton(text)
            payload = execute_text_command(command, automaton, config)
        results.append({"command": command, "payload": payload})
        if config.output is not None:
            config.output.write_text(render_payload(payload, as_json=config.as_json), encoding="utf-8")
    return {"job_count": len(results), "results": results}
