#!/usr/bin/env python3
"""Discover directly-follows process models from simple event logs."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def discover(rows: list[dict[str, str]]) -> dict:
    """Summarize cases and directly-follows edges from case, activity, timestamp rows."""
    grouped: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for index, row in enumerate(rows):
        case = row.get("case", "").strip()
        activity = row.get("activity", "").strip()
        timestamp = row.get("timestamp", "").strip()
        if not case or not activity:
            raise ValueError(f"row {index + 1}: case and activity must be non-empty")
        grouped[case].append((timestamp, activity, index))
    edges: Counter[tuple[str, str]] = Counter()
    activities: Counter[str] = Counter()
    starts: Counter[str] = Counter()
    ends: Counter[str] = Counter()
    for events in grouped.values():
        # Input order breaks equal-timestamp ties deterministically.
        events.sort(key=lambda item: (item[0], item[2]))
        sequence = [event[1] for event in events]
        activities.update(sequence)
        starts[sequence[0]] += 1
        ends[sequence[-1]] += 1
        edges.update(zip(sequence, sequence[1:]))
    return {"cases": len(grouped), "activities": dict(sorted(activities.items())),
            "starts": dict(sorted(starts.items())), "ends": dict(sorted(ends.items())),
            "directly_follows": [dict(source=a, target=b, count=n)
                                 for (a, b), n in sorted(edges.items())]}


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV log with case, activity, and timestamp columns."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"case", "activity", "timestamp"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must contain case, activity, timestamp columns")
        return list(reader)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", type=Path)
    parser.add_argument("--demo", action="store_true", help="analyze a built-in sample")
    args = parser.parse_args(argv)
    if not args.demo and args.csv is None:
        parser.error("provide a CSV path or --demo")
    sample = [{"case":"A","activity":"order","timestamp":"1"},
              {"case":"A","activity":"pay","timestamp":"2"},
              {"case":"A","activity":"ship","timestamp":"3"},
              {"case":"B","activity":"order","timestamp":"1"},
              {"case":"B","activity":"cancel","timestamp":"2"}]
    try:
        result = discover(sample if args.demo else read_csv(args.csv))
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
