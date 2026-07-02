"""
Event subscription system for btreestore.

Provides an observer pattern for monitoring store operations.
Clients can subscribe to events like put, delete, commit, and
receive callbacks when they occur.

Usage:
    from btreestore import Store
    from btreestore.events import EventBus

    with Store("mydb.btree") as store:
        bus = EventBus(store)

        @bus.on("put")
        def on_put(key, value):
            print(f"PUT: {key} = {value}")

        @bus.on("delete")
        def on_delete(key):
            print(f"DELETE: {key}")

        store.put("hello", "world")  # triggers on_put
        store.delete("hello")        # triggers on_delete
"""

from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Union
from .logging_util import get_logger

logger = get_logger()

# Event types
EVENT_PUT = "put"
EVENT_DELETE = "delete"
EVENT_COMMIT = "commit"
EVENT_COMPACT = "compact"
EVENT_CHECKPOINT = "checkpoint"
EVENT_OPEN = "open"
EVENT_CLOSE = "close"


class EventBus:
    """Event bus for subscribing to store operations.

    Wraps a Store instance and intercepts operations to emit events.
    Subscribers receive callbacks synchronously — long-running callbacks
    will block the operation. For async processing, use a queue.
    """

    def __init__(self, store):
        self.store = store
        self._handlers: Dict[str, List[Callable]] = {
            EVENT_PUT: [],
            EVENT_DELETE: [],
            EVENT_COMMIT: [],
            EVENT_COMPACT: [],
            EVENT_CHECKPOINT: [],
            EVENT_OPEN: [],
            EVENT_CLOSE: [],
        }
        self._lock = threading.RLock()
        self._enabled = True
        self._wrap_store()

    def _wrap_store(self) -> None:
        """Wrap the store's methods to emit events."""
        original_put = self.store.put
        original_delete = self.store.delete
        original_commit = self.store.commit
        original_compact = self.store.compact
        original_checkpoint = self.store.checkpoint
        original_close = self.store.close
        bus = self

        def wrapped_put(key, value):
            result = original_put(key, value)
            bus._emit(EVENT_PUT, key=bus._to_bytes(key), value=bus._to_bytes(value))
            return result

        def wrapped_delete(key):
            existed = original_delete(key)
            if existed:
                bus._emit(EVENT_DELETE, key=bus._to_bytes(key))
            return existed

        def wrapped_commit(txn):
            original_commit(txn)
            bus._emit(EVENT_COMMIT, txn_id=txn.txn_id)

        def wrapped_compact():
            result = original_compact()
            bus._emit(EVENT_COMPACT, keys_compacted=result)
            return result

        def wrapped_checkpoint():
            original_checkpoint()
            bus._emit(EVENT_CHECKPOINT)

        def wrapped_close():
            bus._emit(EVENT_CLOSE)
            original_close()

        self.store.put = wrapped_put  # type: ignore
        self.store.delete = wrapped_delete  # type: ignore
        self.store.commit = wrapped_commit  # type: ignore
        self.store.compact = wrapped_compact  # type: ignore
        self.store.checkpoint = wrapped_checkpoint  # type: ignore
        self.store.close = wrapped_close  # type: ignore

    def on(self, event: str, handler: Optional[Callable] = None):
        """Subscribe to an event.

        Can be used as a decorator or called directly:

            @bus.on("put")
            def handler(key, value):
                ...

            bus.on("put", handler)
        """
        if handler is not None:
            self._subscribe(event, handler)
            return None

        def decorator(fn: Callable):
            self._subscribe(event, fn)
            return fn
        return decorator

    def _subscribe(self, event: str, handler: Callable) -> None:
        if event not in self._handlers:
            raise ValueError(f"Unknown event: {event}")
        with self._lock:
            self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> bool:
        """Unsubscribe a handler from an event.

        Returns True if the handler was removed, False if not found.
        """
        if event not in self._handlers:
            return False
        with self._lock:
            try:
                self._handlers[event].remove(handler)
                return True
            except ValueError:
                return False

    def _emit(self, event: str, **kwargs) -> None:
        """Emit an event to all subscribers."""
        if not self._enabled:
            return
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.warning(f"Event handler error ({event}): {e}")

    def enable(self) -> None:
        """Enable event emission."""
        self._enabled = True

    def disable(self) -> None:
        """Disable event emission (all events are silently dropped)."""
        self._enabled = False

    def handler_count(self, event: Optional[str] = None) -> int:
        """Return the number of handlers for an event, or all events."""
        with self._lock:
            if event is not None:
                return len(self._handlers.get(event, []))
            return sum(len(h) for h in self._handlers.values())

    @staticmethod
    def _to_bytes(val: Union[str, bytes]) -> bytes:
        if isinstance(val, str):
            return val.encode("utf-8")
        return val