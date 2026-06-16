"""Import/export utilities for the B+ Tree Database.

Supports:
  - JSON (reuses ``Database.save/load``)
  - CSV (flat key-value dump)
  - Python pickle (fast binary interchange)
"""

from __future__ import annotations

import csv
import io
import json
import pickle
from typing import Any, Dict, Iterator, List, Tuple

from .database import Database
from .serializer import Serializer


def export_csv(db: Database, path: str, delimiter: str = ",") -> int:
    """Export all key-value pairs to a CSV file.

    Each row is ``key,value`` where *value* is the JSON-serialized
    representation.  Returns the number of rows written.
    """
    serializer = Serializer()
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(["key", "value"])
        for key, raw_val in db._tree.range_query():
            value = serializer.deserialize_value(raw_val)
            writer.writerow([key, json.dumps(value, ensure_ascii=False)])
            rows += 1
    return rows


def import_csv(db: Database, path: str, delimiter: str = ",") -> int:
    """Import key-value pairs from a CSV file.

    The file must have a header row with columns ``key,value``.
    Returns the number of rows imported.
    """
    count = 0
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            key = row["key"]
            value = json.loads(row["value"])
            db.put(key, value)
            count += 1
    return count


def export_json_lines(db: Database, path: str) -> int:
    """Export to newline-delimited JSON (JSONL) format.

    Each line is ``{"key": ..., "value": ...}``.  Returns row count.
    """
    serializer = Serializer()
    rows = 0
    with open(path, "w", encoding="utf-8") as f:
        for key, raw_val in db._tree.range_query():
            value = serializer.deserialize_value(raw_val)
            f.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")
            rows += 1
    return rows


def import_json_lines(db: Database, path: str) -> int:
    """Import from a JSONL file.  Returns row count."""
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            db.put(entry["key"], entry["value"])
            count += 1
    return count


def export_pickle(db: Database, path: str) -> int:
    """Export all entries as a Python pickle file.

    Pickle is fast but not human-readable and not cross-language portable.
    Returns entry count.
    """
    serializer = Serializer()
    entries: List[Tuple[str, Any]] = []
    for key, raw_val in db._tree.range_query():
        value = serializer.deserialize_value(raw_val)
        entries.append((key, value))
    with open(path, "wb") as f:
        pickle.dump({"order": db._tree.order, "entries": entries}, f, protocol=pickle.HIGHEST_PROTOCOL)
    return len(entries)


def import_pickle(db: Database, path: str) -> int:
    """Import from a pickle file.  Returns entry count."""
    with open(path, "rb") as f:
        data = pickle.load(f)
    count = 0
    for key, value in data.get("entries", []):
        db.put(key, value)
        count += 1
    return count