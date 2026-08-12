"""Event/callback system for the boids simulation.

Provides a simple observer pattern that allows external code to hook into
simulation lifecycle events without modifying the core simulation class.

Supported events:
    - "step_start": fired at the beginning of each step (args: tick)
    - "step_end": fired at the end of each step (args: tick)
    - "boid_added": fired when a boid is added (args: boid)
    - "boid_removed": fired when a boid is removed (args: boid)
    - "predator_added": fired when a predator is added (args: predator)
    - "obstacle_added": fired when an obstacle is added (args: obstacle)
    - "collision": fired when a predator catches a boid (args: predator, boid)

Usage::

    sim = BoidSimulation(cfg)
    sim.events.on("step_end", lambda tick: print(f"Tick {tick}: {sim.stats()}"))
    sim.events.on("collision", lambda pred, boid: print(f"Caught boid {boid.id}!"))
    for _ in range(100):
        sim.step()
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    """A simple event bus supporting subscribe/publish for named events.

    Multiple listeners can subscribe to the same event. They are called in
    subscription order. Exceptions in listeners are caught and reported via
    the error handler (default: print to stderr) so one bad listener doesn't
    break the simulation.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable]] = defaultdict(list)
        self._error_handler: Callable[[Exception], None] = self._default_error_handler

    @staticmethod
    def _default_error_handler(exc: Exception) -> None:
        """Default handler that prints exceptions to stderr."""
        import sys
        print(f"[EventBus] listener error: {exc}", file=sys.stderr)

    def set_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Set a custom error handler for listener exceptions."""
        self._error_handler = handler

    def on(self, event: str, callback: Callable) -> None:
        """Subscribe *callback* to *event*.

        The callback will be called with whatever arguments the event provides.
        """
        if not callable(callback):
            raise TypeError(f"callback must be callable, got {type(callback)}")
        self._listeners[event].append(callback)

    def off(self, event: str, callback: Callable) -> None:
        """Unsubscribe *callback* from *event*."""
        if event in self._listeners:
            try:
                self._listeners[event].remove(callback)
            except ValueError:
                pass  # callback wasn't subscribed

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit *event*, calling all subscribed listeners.

        Exceptions in listeners are caught and passed to the error handler
        so one failing listener doesn't break the simulation step.
        """
        for callback in self._listeners.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as exc:
                self._error_handler(exc)

    def listener_count(self, event: str) -> int:
        """Return the number of listeners for *event*."""
        return len(self._listeners.get(event, []))

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()