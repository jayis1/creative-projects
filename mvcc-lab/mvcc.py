#!/usr/bin/env python3
"""Deterministic optimistic snapshot-isolation simulator."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any


class ScheduleError(ValueError):
    """Invalid database image or operation schedule."""


@dataclass(frozen=True)
class Version:
    timestamp: int
    value: Any
    deleted: bool = False


class Store:
    def __init__(self, initial: dict[str, Any] | None = None):
        if initial is None:
            initial = {}
        if not isinstance(initial, dict) or any(not isinstance(k, str) for k in initial):
            raise ScheduleError("initial must be an object with string keys")
        self.clock = 0
        self.history: dict[str, list[Version]] = {
            key: [Version(0, value)] for key, value in initial.items()
        }

    def begin(self) -> "Transaction":
        return Transaction(self, self.clock)

    def visible(self, key: str, snapshot: int) -> Version | None:
        versions = self.history.get(key, ())
        for version in reversed(versions):
            if version.timestamp <= snapshot:
                return version
        return None


class Transaction:
    def __init__(self, store: Store, snapshot: int):
        self.store, self.snapshot = store, snapshot
        self.writes: dict[str, Version] = {}
        self.finished: str | None = None

    def get(self, key: str) -> Any:
        self._active()
        staged = self.writes.get(key)
        if staged is not None:
            return None if staged.deleted else staged.value
        version = self.store.visible(key, self.snapshot)
        return None if version is None or version.deleted else version.value

    def scan(self, prefix: str = "") -> dict[str, Any]:
        """Return snapshot-visible rows with prefix, overlaid with own writes."""
        self._active()
        rows: dict[str, Any] = {}
        keys = set(self.store.history) | set(self.writes)
        for key in sorted(keys):
            if not key.startswith(prefix):
                continue
            staged = self.writes.get(key)
            if staged is not None:
                if not staged.deleted:
                    rows[key] = staged.value
                continue
            version = self.store.visible(key, self.snapshot)
            if version is not None and not version.deleted:
                # None is a valid JSON value, so presence must not be tested by truthiness.
                rows[key] = version.value
        return rows

    def put(self, key: str, value: Any) -> None:
        self._active()
        self.writes[key] = Version(-1, value)

    def delete(self, key: str) -> None:
        self._active()
        self.writes[key] = Version(-1, None, True)

    def _active(self) -> None:
        if self.finished is not None:
            raise ScheduleError(f"transaction already {self.finished}")

    def commit(self) -> bool:
        self._active()
        for key in self.writes:
            latest = self.store.history.get(key, [])
            if latest and latest[-1].timestamp > self.snapshot:
                self.finished = "aborted"
                return False
        if self.writes:
            self.store.clock += 1
            for key, staged in self.writes.items():
                self.store.history.setdefault(key, []).append(
                    Version(self.store.clock, staged.value, staged.deleted)
                )
        self.finished = "committed"
        return True


def run_schedule(data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or set(data) - {"initial", "transactions"}:
        raise ScheduleError("input must contain only initial and transactions")
    store = Store(data.get("initial", {}))
    transactions = data.get("transactions", [])
    if not isinstance(transactions, list):
        raise ScheduleError("transactions must be a list")
    active: dict[str, Transaction] = {}
    finished: set[str] = set()
    output: list[dict[str, Any]] = []
    for tx_spec in transactions:
        if not isinstance(tx_spec, dict) or set(tx_spec) != {"name", "ops"}:
            raise ScheduleError("each schedule item requires name and ops")
        name, ops = tx_spec["name"], tx_spec["ops"]
        if not isinstance(name, str) or not name or name in finished:
            raise ScheduleError("transaction names must be unique nonempty strings")
        if not isinstance(ops, list):
            raise ScheduleError(f"{name}: ops must be a list")
        tx = active.get(name)
        if tx is None:
            tx = active[name] = store.begin()
        for op in ops:
            if not isinstance(op, dict) or len(op) != 1:
                raise ScheduleError(f"{name}: each operation must have exactly one action")
            action, arg = next(iter(op.items()))
            if action == "get" and isinstance(arg, str):
                output.append({"transaction": name, "get": arg, "value": tx.get(arg)})
            elif action == "scan" and isinstance(arg, str):
                output.append({"transaction": name, "scan": arg, "rows": tx.scan(arg)})
            elif action == "put" and isinstance(arg, list) and len(arg) == 2 and isinstance(arg[0], str):
                tx.put(arg[0], arg[1])
            elif action == "delete" and isinstance(arg, str):
                tx.delete(arg)
            elif action == "commit" and arg is True:
                success = tx.commit()
                output.append({"transaction": name, "commit": "committed" if success else "aborted"})
                finished.add(name)
                del active[name]
            else:
                raise ScheduleError(f"{name}: invalid operation {op!r}")
    if active:
        raise ScheduleError("unfinished transactions: " + ", ".join(sorted(active)))
    return output


def demo() -> dict[str, Any]:
    return {"initial": {"account": 10}, "transactions": [
        {"name": "T1", "ops": [{"get": "account"}, {"put": ["account", 12]}]},
        {"name": "T2", "ops": [{"get": "account"}, {"put": ["account", 9]}, {"commit": True}]},
        {"name": "T1", "ops": [{"commit": True}]},
    ]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "demo"))
    parser.add_argument("file", nargs="?", help="JSON schedule for run")
    args = parser.parse_args(argv)
    if args.command == "run" and not args.file:
        parser.error("run requires a JSON file")
    if args.command == "demo" and args.file:
        parser.error("demo takes no file")
    try:
        if args.command == "demo":
            data = demo()
        else:
            with open(args.file, encoding="utf-8") as source:
                data = json.load(source)
        print(json.dumps(run_schedule(data), indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, ScheduleError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
