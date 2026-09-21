"""Causal event tracing with Lamport and vector clocks."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Iterable


class TraceError(ValueError):
    """Raised for invalid trace operations."""


@dataclass(frozen=True)
class Event:
    process: str
    kind: str = "local"
    peer: str | None = None
    payload: str = ""
    lamport: int = 0
    vector: tuple[int, ...] = ()

    def to_dict(self, processes: tuple[str, ...]) -> dict:
        return {"process": self.process, "kind": self.kind, "peer": self.peer,
                "payload": self.payload, "lamport": self.lamport,
                "vector": dict(zip(processes, self.vector))}


@dataclass
class Trace:
    processes: tuple[str, ...]
    events: list[Event] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.processes or len(set(self.processes)) != len(self.processes):
            raise TraceError("processes must be non-empty and unique")
        if any(not p or not isinstance(p, str) for p in self.processes):
            raise TraceError("process names must be non-empty strings")

    def _index(self, process: str) -> int:
        try:
            return self.processes.index(process)
        except ValueError as exc:
            raise TraceError(f"unknown process: {process}") from exc

    def _append(self, process: str, kind: str, peer: str | None, payload: str,
                clock: list[int], lamport: int) -> Event:
        idx = self._index(process)
        if kind == "send" and peer is None:
            raise TraceError("send requires a peer")
        if kind == "receive":
            if peer is None:
                raise TraceError("receive requires a peer")
            self._index(peer)
        clock[idx] += 1
        event = Event(process, kind, peer, payload, lamport + 1, tuple(clock))
        self.events.append(event)
        return event

    def record(self, actions: Iterable[tuple]) -> list[Event]:
        """Record (process, kind[, peer[, payload]]) actions in order."""
        # Every process has its own view. Independent local events must not
        # accidentally observe another process merely because they are listed later.
        views = {process: [0] * len(self.processes) for process in self.processes}
        lamport = self.events[-1].lamport if self.events else 0
        result: list[Event] = []
        for action in actions:
            if not 2 <= len(action) <= 4:
                raise TraceError("actions need process, kind, optional peer/payload")
            process, kind = action[0], action[1]
            if kind not in {"local", "send", "receive"}:
                raise TraceError(f"invalid event kind: {kind}")
            peer = action[2] if len(action) >= 3 else None
            payload = action[3] if len(action) == 4 else ""
            self._index(process)
            clock = views[process]
            if kind == "receive" and peer is not None:
                self._index(peer)
                prior = next((e for e in reversed(self.events) if e.process == peer and e.kind == "send"), None)
                if prior:
                    clock[:] = [max(a, b) for a, b in zip(clock, prior.vector)]
                    lamport = max(lamport, prior.lamport)
            event = self._append(process, kind, peer, str(payload), clock, lamport)
            views[process] = list(event.vector)
            lamport = event.lamport
            result.append(event)
        return result

    def happens_before(self, left: Event, right: Event) -> bool:
        """Return whether left causally precedes right by vector-clock order."""
        if len(left.vector) != len(right.vector):
            raise TraceError("events belong to incompatible traces")
        return all(a <= b for a, b in zip(left.vector, right.vector)) and left.vector != right.vector

    def concurrent_pairs(self) -> list[tuple[Event, Event]]:
        return [(a, b) for i, a in enumerate(self.events) for b in self.events[i + 1:]
                if not self.happens_before(a, b) and not self.happens_before(b, a)]

    def to_json(self) -> str:
        return json.dumps({"processes": self.processes,
                           "events": [e.to_dict(self.processes) for e in self.events]}, indent=2)


def load_json(text: str) -> Trace:
    """Load a trace produced by :meth:`Trace.to_json`, validating its shape."""
    try:
        raw = json.loads(text)
        processes = tuple(raw["processes"])
        trace = Trace(processes)
        for item in raw["events"]:
            if not isinstance(item, dict):
                raise TraceError("event must be an object")
            process, kind = item["process"], item["kind"]
            trace.events.append(Event(process, kind, item.get("peer"), str(item.get("payload", "")),
                                      int(item["lamport"]), tuple(item["vector"].get(p, 0) for p in processes)))
        return trace
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TraceError(f"invalid trace JSON: {exc}") from exc
