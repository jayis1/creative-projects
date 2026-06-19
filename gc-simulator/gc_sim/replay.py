"""Replay engine — re-creates a simulation from a recorded trace.

Given a :class:`~gc_sim.events.EventTracer` or a JSON trace file,
:class:`TraceReplayer` reconstructs the exact same allocation pattern on a
fresh :class:`~gc_sim.simulator.GCSimulator` and optionally re-runs
collections.  This lets you:

* Reproduce a fragmentation or OOM bug on a different collector.
* Benchmark all five collectors on the *same* allocation stream.
* Compare the effect of heap size changes on the same workload.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .events import EventTracer, Event, EventType
from .simulator import GCSimulator
from .collectors import available_collectors
from .heap import Object


class TraceReplayer:
    """Replay a recorded trace onto a simulator.

    Parameters
    ----------
    trace : EventTracer or list of dicts
        The event source to replay.
    collector : str
        Collector to use for the replay simulation.
    heap_size : int
        Heap size for the replay simulation.
    allocator : str
        Allocator name.
    allocator_policy : str
        Free-list policy.
    **collector_kwargs
        Extra collector constructor arguments.
    """

    def __init__(
        self,
        trace: EventTracer | List[Event] | List[Dict[str, Any]],
        collector: str = "mark_sweep",
        heap_size: int = 1024,
        allocator: str = "bump",
        allocator_policy: str = "first_fit",
        **collector_kwargs,
    ) -> None:
        if isinstance(trace, EventTracer):
            self.events: List[Event] = list(trace)
        elif isinstance(trace, list):
            # Could be List[Event] or List[dict]
            if trace and isinstance(trace[0], Event):
                self.events = list(trace)
            else:
                self.events = [Event.from_dict(d) for d in trace]
        else:
            raise TypeError("trace must be an EventTracer or list of Events/dicts")

        self.sim = GCSimulator(
            heap_size=heap_size,
            collector=collector,
            allocator=allocator,
            allocator_policy=allocator_policy,
            **collector_kwargs,
        )
        # Disable tracing on the replay sim to avoid duplicating events
        if self.sim.tracer is not None:
            self.sim.tracer.disable()
        # Map of oid -> Object for resolving references during replay
        self._oid_map: Dict[int, Object] = {}

    def replay(self, run_collections: bool = True) -> GCSimulator:
        """Replay all events onto the simulator and return it.

        Parameters
        ----------
        run_collections : bool
            If ``True``, collection events are replayed as real
            collections on the new simulator.  If ``False``, collection
            events are skipped (useful when you want to replay only the
            allocation pattern and then run your own collections).
        """
        for ev in self.events:
            self._replay_event(ev, run_collections)
        return self.sim

    def _replay_event(self, ev: Event, run_collections: bool) -> None:
        et = ev.event_type
        d = ev.data

        if et == EventType.ALLOCATE.value:
            size = d["size"]
            name = d.get("name", "")
            obj = self.sim.allocate(size, name=name)
            self._oid_map[d["oid"]] = obj

        elif et == EventType.ADD_ROOT.value:
            name = d["name"]
            oid = d["oid"]
            obj = self._oid_map.get(oid)
            if obj is not None:
                self.sim.add_root(name, obj)

        elif et == EventType.REMOVE_ROOT.value:
            self.sim.remove_root(d["name"])

        elif et == EventType.CLEAR_ROOT.value:
            self.sim.clear_root(d["name"])

        elif et == EventType.LINK.value:
            src = self._oid_map.get(d["src_oid"])
            tgt = self._oid_map.get(d["tgt_oid"])
            if src is not None and tgt is not None:
                self.sim.link(src, tgt, name=d.get("name", ""))

        elif et == EventType.UNLINK.value:
            # Unlink by ref index if stored
            src = self._oid_map.get(d.get("src_oid"))
            idx = d.get("ref_index")
            if src is not None and idx is not None and idx < len(src.refs):
                ref = src.refs[idx]
                self.sim.unlink(src, ref)

        elif et == EventType.WEAK_LINK.value:
            src = self._oid_map.get(d["src_oid"])
            tgt = self._oid_map.get(d["tgt_oid"])
            if src is not None and tgt is not None:
                self.sim.weak_link(src, tgt, name=d.get("name", ""))

        elif et == EventType.COLLECT.value:
            if run_collections:
                kwargs = {}
                if d.get("force_major"):
                    kwargs["force_major"] = True
                self.sim.collect(**kwargs)

        elif et == EventType.HEAP_RESET.value:
            self.sim.heap.reset()
            self._oid_map.clear()

        elif et == EventType.NOTE.value:
            pass  # notes are informational only

    def replay_all_collectors(
        self, heap_size: int = 0, run_collections: bool = True
    ) -> Dict[str, GCSimulator]:
        """Replay the trace on every available collector.

        Returns a dict mapping collector name to the resulting simulator.
        """
        results: Dict[str, GCSimulator] = {}
        for cname in available_collectors():
            replayer = TraceReplayer(
                self.events, collector=cname, heap_size=heap_size or self.sim.heap.size,
            )
            replayer.replay(run_collections=run_collections)
            results[cname] = replayer.sim
        return results


def load_trace(path: str) -> List[Dict[str, Any]]:
    """Load a JSON trace file and return the list of event dicts."""
    with open(path) as f:
        return json.load(f)


def replay_from_file(
    path: str,
    collector: str = "mark_sweep",
    heap_size: int = 1024,
    run_collections: bool = True,
) -> GCSimulator:
    """Convenience: load a trace file and replay it."""
    events = load_trace(path)
    replayer = TraceReplayer(events, collector=collector, heap_size=heap_size)
    return replayer.replay(run_collections=run_collections)