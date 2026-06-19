"""Allocation and collection event tracing.

Provides an event-sourcing model for GC simulations. Every significant
operation (allocation, root add/remove, link/unlink, collection) is recorded
as an :class:`Event` so that a simulation can be replayed deterministically,
exported as JSON, and analysed offline.

This is invaluable for reproducing fragmentation bugs, comparing collector
behaviour on the exact same allocation stream, and building visualisations.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional


class EventType(str, Enum):
    """Kinds of events that can be recorded during a simulation."""

    ALLOCATE = "allocate"
    ADD_ROOT = "add_root"
    REMOVE_ROOT = "remove_root"
    CLEAR_ROOT = "clear_root"
    LINK = "link"
    UNLINK = "unlink"
    WEAK_LINK = "weak_link"
    ADD_FINALIZER = "add_finalizer"
    COLLECT = "collect"
    # Extended events
    SCENARIO_START = "scenario_start"
    SCENARIO_END = "scenario_end"
    HEAP_RESET = "heap_reset"
    NOTE = "note"


@dataclass
class Event:
    """A single recorded event in the simulation trace.

    Attributes
    ----------
    seq : int
        Sequence number (auto-incremented, 1-based).
    timestamp : float
        Wall-clock time (``time.time()``) when the event was recorded.
    event_type : str
        One of :class:`EventType` values.
    data : dict
        Event-specific payload (e.g. ``{"size": 8, "name": "a"}``).
    """

    seq: int
    timestamp: float
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Event":
        return cls(
            seq=d["seq"],
            timestamp=d.get("timestamp", 0.0),
            event_type=d["event_type"],
            data=d.get("data", {}),
        )


class EventTracer:
    """Records simulation events for replay and analysis.

    The tracer is opt-in: pass ``trace=True`` to
    :class:`~gc_sim.simulator.GCSimulator` to enable it.  Events are stored
    in an in-memory list and can be exported to JSON for persistence.

    Example
    -------
    >>> sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
    >>> sim.allocate(8, "a")
    >>> sim.add_root("r", sim.live_objects[0])
    >>> sim.collect()
    >>> trace = sim.tracer.export()
    >>> len(trace)
    3
    """

    def __init__(self) -> None:
        self._events: List[Event] = []
        self._seq = 0
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def record(self, event_type: EventType | str, **data: Any) -> Event:
        """Record an event and return it."""
        if not self._enabled:
            return Event(seq=0, timestamp=0.0, event_type="", data={})
        self._seq += 1
        et = event_type.value if isinstance(event_type, EventType) else event_type
        event = Event(
            seq=self._seq,
            timestamp=time.time(),
            event_type=et,
            data=data,
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> List[Event]:
        """Return a shallow copy of all recorded events."""
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)

    def filter(self, event_type: str) -> List[Event]:
        """Return all events of a given type."""
        return [e for e in self._events if e.event_type == event_type]

    def counts(self) -> Dict[str, int]:
        """Return a dict of ``{event_type: count}``."""
        result: Dict[str, int] = {}
        for e in self._events:
            result[e.event_type] = result.get(e.event_type, 0) + 1
        return result

    def export(self) -> List[Dict[str, Any]]:
        """Export all events as a list of JSON-serialisable dicts."""
        return [e.to_dict() for e in self._events]

    def export_json(self, path: str, *, indent: int = 2) -> None:
        """Write all events to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.export(), f, indent=indent)

    def clear(self) -> None:
        """Remove all recorded events (does not reset seq counter)."""
        self._events.clear()

    @classmethod
    def from_json(cls, path: str) -> "EventTracer":
        """Load a tracer from a JSON trace file (events only, no replay)."""
        tracer = cls()
        with open(path) as f:
            data = json.load(f)
        for d in data:
            event = Event.from_dict(d)
            tracer._events.append(event)
            if event.seq > tracer._seq:
                tracer._seq = event.seq
        return tracer