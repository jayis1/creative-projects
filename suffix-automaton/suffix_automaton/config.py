"""Configuration loading for batch suffix automaton jobs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import Any


@dataclass(slots=True)
class JobConfig:
    """Normalized configuration for a batch job."""

    text: str | None = None
    file: Path | None = None
    strings: list[str] | None = None
    substring: str | None = None
    k: int | None = None
    alphabet: str | None = None
    limit: int | None = None
    min_length: int | None = None
    pairwise: bool = False
    as_json: bool = True
    output: Path | None = None


def load_config(path: Path) -> dict[str, Any]:
    """Load a JSON or TOML config file."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix == ".toml":
        return tomllib.loads(path.read_text(encoding="utf-8"))
    raise ValueError("config files must use .json or .toml")


def parse_job_config(raw: dict[str, Any]) -> JobConfig:
    """Validate and normalize a job config mapping."""
    if not isinstance(raw, dict):
        raise TypeError("job config must be a dictionary")
    text = raw.get("text")
    file_value = raw.get("file")
    strings = raw.get("strings")
    substring = raw.get("substring")
    alphabet = raw.get("alphabet")
    output = raw.get("output")
    k = raw.get("k")
    limit = raw.get("limit")
    min_length = raw.get("min_length")
    pairwise = raw.get("pairwise", False)
    as_json = raw.get("json", True)

    if text is not None and not isinstance(text, str):
        raise TypeError("job.text must be a string when provided")
    if file_value is not None and not isinstance(file_value, str):
        raise TypeError("job.file must be a string path when provided")
    if strings is not None and (
        not isinstance(strings, list) or any(not isinstance(item, str) for item in strings)
    ):
        raise TypeError("job.strings must be a list of strings when provided")
    if substring is not None and not isinstance(substring, str):
        raise TypeError("job.substring must be a string when provided")
    if alphabet is not None and not isinstance(alphabet, str):
        raise TypeError("job.alphabet must be a string when provided")
    if output is not None and not isinstance(output, str):
        raise TypeError("job.output must be a string path when provided")
    if k is not None and not isinstance(k, int):
        raise TypeError("job.k must be an integer when provided")
    if limit is not None and not isinstance(limit, int):
        raise TypeError("job.limit must be an integer when provided")
    if min_length is not None and not isinstance(min_length, int):
        raise TypeError("job.min_length must be an integer when provided")
    if not isinstance(pairwise, bool):
        raise TypeError("job.pairwise must be a boolean")
    if not isinstance(as_json, bool):
        raise TypeError("job.json must be a boolean")

    return JobConfig(
        text=text,
        file=None if file_value is None else Path(file_value),
        strings=strings,
        substring=substring,
        k=k,
        alphabet=alphabet,
        limit=limit,
        min_length=min_length,
        pairwise=pairwise,
        as_json=as_json,
        output=None if output is None else Path(output),
    )
