"""Deterministic discrete-event simulator for small synchronous logic circuits."""
from __future__ import annotations

import heapq
import json
from dataclasses import asdict, dataclass
from typing import Callable


@dataclass(frozen=True)
class Trace:
    time: int
    wire: str
    old: int
    new: int
    cause: str


class Wire:
    def __init__(self, name: str, value: int = 0):
        self.name = name
        self.value = _bit(value)
        self._listeners: list[Callable[[int], None]] = []


def _bit(value: int) -> int:
    if type(value) is not int or value not in (0, 1):
        raise ValueError("logic values must be integer 0 or 1")
    return value


class Circuit:
    """A bounded event simulator. Equal-time events execute in insertion order."""
    def __init__(self, max_events_at_time: int = 10000):
        if type(max_events_at_time) is not int or max_events_at_time < 1:
            raise ValueError("max_events_at_time must be a positive integer")
        self.time = 0
        self.max_events_at_time = max_events_at_time
        self.wires: dict[str, Wire] = {}
        self._queue: list[tuple[int, int, Callable[[], None]]] = []
        self._sequence = 0
        self.trace: list[Trace] = []
        self._drivers: set[str] = set()

    def _wire(self, name: str, value: int = 0) -> Wire:
        if not isinstance(name, str) or not name or name in self.wires:
            raise ValueError(f"wire name must be nonempty and unique: {name!r}")
        wire = Wire(name, value)
        self.wires[name] = wire
        return wire

    def input(self, name: str, value: int = 0) -> Wire:
        wire = self._wire(name, value)
        self._drivers.add(name)
        return wire

    def _schedule(self, when: int, action: Callable[[], None]) -> None:
        if type(when) is not int or when < self.time:
            raise ValueError("event time must be an integer not earlier than current time")
        self._sequence += 1
        heapq.heappush(self._queue, (when, self._sequence, action))

    def _gate(self, name: str, inputs: tuple[Wire, ...], fn: Callable[..., int], delay: int) -> Wire:
        if type(delay) is not int or delay < 0:
            raise ValueError("gate delay must be a nonnegative integer")
        if any(w not in self.wires.values() for w in inputs):
            raise ValueError("gate inputs must belong to this circuit")
        out = self._wire(name)
        generation = 0

        def evaluate(_: int = 0) -> None:
            nonlocal generation
            generation += 1
            token = generation
            result = _bit(fn(*(w.value for w in inputs)))
            at = self.time + delay

            def commit() -> None:
                if token == generation:
                    self._set(out, result, name)
            self._schedule(at, commit)

        for wire in inputs:
            wire._listeners.append(evaluate)
        evaluate()
        return out

    def and_gate(self, name: str, a: Wire, b: Wire, delay: int = 1) -> Wire:
        return self._gate(name, (a, b), lambda x, y: x & y, delay)

    def or_gate(self, name: str, a: Wire, b: Wire, delay: int = 1) -> Wire:
        return self._gate(name, (a, b), lambda x, y: x | y, delay)

    def xor_gate(self, name: str, a: Wire, b: Wire, delay: int = 1) -> Wire:
        return self._gate(name, (a, b), lambda x, y: x ^ y, delay)

    def not_gate(self, name: str, a: Wire, delay: int = 1) -> Wire:
        return self._gate(name, (a,), lambda x: 1 - x, delay)

    def register(self, name: str, data: Wire, clock: Wire, delay: int = 1) -> Wire:
        if type(delay) is not int or delay < 0:
            raise ValueError("register delay must be a nonnegative integer")
        if data not in self.wires.values() or clock not in self.wires.values():
            raise ValueError("register inputs must belong to this circuit")
        out = self._wire(name)
        previous = clock.value

        def edge(_: int = 0) -> None:
            nonlocal previous
            current = clock.value
            if previous == 0 and current == 1:
                sampled = data.value
                self._schedule(self.time + delay, lambda: self._set(out, sampled, name))
            previous = current
        clock._listeners.append(edge)
        return out

    def _set(self, wire: Wire, value: int, cause: str) -> None:
        value = _bit(value)
        if wire.value == value:
            return
        old = wire.value
        wire.value = value
        self.trace.append(Trace(self.time, wire.name, old, value, cause))
        for listener in tuple(wire._listeners):
            listener(value)

    def set_input(self, name: str, value: int, at: int | None = None) -> None:
        if name not in self._drivers:
            raise ValueError(f"not an input wire: {name!r}")
        bit = _bit(value)
        when = self.time if at is None else at
        if type(when) is not int or when < self.time:
            raise ValueError("input time must be an integer not earlier than current time")
        self._schedule(when, lambda: self._set(self.wires[name], bit, "input"))

    def run(self, until: int | None = None, max_events: int = 100000) -> list[Trace]:
        if type(max_events) is not int or max_events < 1:
            raise ValueError("max_events must be a positive integer")
        if until is not None and (type(until) is not int or until < self.time):
            raise ValueError("until must be an integer not earlier than current time")
        processed = 0
        active_time: int | None = None
        at_time = 0
        while self._queue and (until is None or self._queue[0][0] <= until):
            when = self._queue[0][0]
            next_at_time = at_time + 1 if when == active_time else 1
            if next_at_time > self.max_events_at_time or processed + 1 > max_events:
                # Leave the event queued so callers can continue with a larger budget.
                raise RuntimeError("event budget exceeded; possible zero-delay oscillation")
            when, _, action = heapq.heappop(self._queue)
            if when != active_time:
                active_time, at_time = when, 0
            at_time += 1
            processed += 1
            self.time = when
            action()
        if until is not None:
            self.time = until
        return list(self.trace)

    def trace_json(self) -> str:
        return json.dumps([asdict(row) for row in self.trace], indent=2)

    def trace_vcd(self) -> str:
        """Return a compact VCD waveform for interoperability with viewers."""
        names = list(self.wires)
        identifiers = {name: f"w{index}" for index, name in enumerate(names)}
        lines = [
            "$date generated by temporal-circuit $end",
            "$version temporal-circuit stdlib simulator $end",
            "$timescale 1ns $end",
            "$scope module circuit $end",
        ]
        for name in names:
            lines.append(f"$var wire 1 {identifiers[name]} {name} $end")
        lines.extend(["$upscope $end", "$enddefinitions $end", "#0"])
        initial = {name: self.wires[name].value for name in names}
        for event in reversed(self.trace):
            initial[event.wire] = event.old
        for name in names:
            lines.append(f"{initial[name]}{identifiers[name]}")
        current_time = 0
        for event in self.trace:
            if event.time != current_time:
                current_time = event.time
                lines.append(f"#{current_time}")
            lines.append(f"{event.new}{identifiers[event.wire]}")
        return "\n".join(lines) + "\n"
