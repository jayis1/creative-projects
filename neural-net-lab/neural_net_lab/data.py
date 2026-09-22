"""Small, dependency-free dataset adapters for experiments."""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Sequence


Dataset = tuple[list[list[float]], list[list[float]]]


def _numbers(values: Sequence[Any], context: str) -> list[float]:
    try:
        result = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must contain only numeric values") from exc
    if not result:
        raise ValueError(f"{context} must not be empty")
    return result


def load_dataset(path: str | Path, target_column: str | None = None) -> Dataset:
    """Load numeric features and targets from CSV or JSONL.

    CSV files require a header; ``target_column`` names the target column and
    defaults to the final column. JSONL records use ``features`` and ``target``
    keys, where target may be a scalar or a list.
    """
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"dataset does not exist: {source}")
    if source.suffix.lower() == ".csv":
        with source.open(newline="", encoding="utf8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or not rows[0]:
            raise ValueError("CSV dataset must contain a header and at least one row")
        columns = list(rows[0])
        targets = [name.strip() for name in (target_column or columns[-1]).split(",")]
        if not targets or any(name not in columns for name in targets):
            missing = next(name for name in targets if name not in columns)
            raise ValueError(f"target column {missing!r} is not present in CSV header")
        feature_columns = [column for column in columns if column not in targets]
        if not feature_columns:
            raise ValueError("CSV dataset needs at least one feature column")
        xs = [_numbers([row[column] for column in feature_columns], "CSV features") for row in rows]
        ys = [_numbers([row[name] for name in targets], "CSV targets") for row in rows]
        return xs, ys
    if source.suffix.lower() in {".jsonl", ".ndjson"}:
        xs: list[list[float]] = []
        ys: list[list[float]] = []
        try:
            with source.open(encoding="utf8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if not isinstance(record, dict) or "features" not in record or "target" not in record:
                        raise ValueError(f"JSONL line {line_number} needs features and target")
                    xs.append(_numbers(record["features"], f"JSONL line {line_number} features"))
                    target = record["target"] if isinstance(record["target"], list) else [record["target"]]
                    ys.append(_numbers(target, f"JSONL line {line_number} target"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid JSONL dataset {source}: {exc}") from exc
        if not xs:
            raise ValueError("JSONL dataset must contain at least one record")
        if len({len(row) for row in xs}) != 1 or len({len(row) for row in ys}) != 1:
            raise ValueError("all dataset rows must have consistent feature and target widths")
        return xs, ys
    raise ValueError("dataset format must be .csv, .jsonl, or .ndjson")


def train_test_split(xs: Sequence[Sequence[float]], ys: Sequence[Sequence[float]], test_size: float = 0.2, seed: int = 0) -> tuple[Dataset, Dataset]:
    """Deterministically split aligned samples into train and validation sets."""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("split requires at least two aligned samples")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    validation_count = max(1, min(len(xs) - 1, round(len(xs) * test_size)))
    indices = list(range(len(xs)))
    random.Random(seed).shuffle(indices)
    validation_ids = set(indices[:validation_count])
    train = ([list(map(float, xs[i])) for i in indices if i not in validation_ids], [list(map(float, ys[i])) for i in indices if i not in validation_ids])
    validation = ([list(map(float, xs[i])) for i in indices if i in validation_ids], [list(map(float, ys[i])) for i in indices if i in validation_ids])
    return train, validation
