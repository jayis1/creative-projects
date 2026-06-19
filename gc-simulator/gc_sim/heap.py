"""Simulated heap and object graph.

This module defines the core data structures used by every garbage collector
implemented in the package.  The model is intentionally simple but faithful to
the essential mechanics of real managed runtimes:

* A :class:`Heap` owns a fixed-size block of *cells* (think words).  Every
  :class:`Object` occupies a contiguous run of cells.  Objects are placed on
  the heap via an :class:`Allocator <gc_sim.allocators.Allocator>`.
* Objects carry a small amount of metadata (size, mark bit, age, forwarding
  pointer) and a list of outgoing references represented by
  :class:`ObjectRef` -- a weak handle that becomes *dead* when the object it
  points to is freed.  This avoids dangling pointers after a collection.
* A global :class:`RootSet` holds the current GC roots (global variables,
  stack slots, registers).  Collectors walk this set to discover live objects.

The design deliberately avoids Python ``id()``-based pointers; instead every
object is identified by a monotonically increasing integer ``oid`` that is
*stable* across collections.  This makes tracing and statistics easy to reason
about.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Iterator, List, Optional


class HeapError(Exception):
    """Raised for heap-level violations (out of memory, double free, ...)."""


# ---------------------------------------------------------------------------
# Object references
# ---------------------------------------------------------------------------

@dataclass
class ObjectRef:
    """A weak-ish reference from one object to another.

    ``target`` is the referenced :class:`Object` (or ``None`` if it has been
    collected).  Keeping the Python reference alive would prevent the object
    from ever being freed in a real GC; here we model liveness explicitly via
    :attr:`Object.alive`, but ``ObjectRef`` still clears itself on free so
    that stale pointers are visible as ``None`` rather than silently pointing
    at reused memory.
    """

    target: Optional["Object"] = None
    name: str = ""

    @property
    def is_dead(self) -> bool:
        """True if the referenced object has been freed."""
        return self.target is None or not self.target.alive

    def __repr__(self) -> str:  # pragma: no cover - trivial
        if self.target is None:
            return f"ObjectRef(dead{f' {self.name}' if self.name else ''})"
        return f"ObjectRef(#{self.target.oid}{f' {self.name}' if self.name else ''})"


# ---------------------------------------------------------------------------
# Heap objects
# ---------------------------------------------------------------------------

_next_oid = itertools.count(1)


def _new_oid() -> int:
    return next(_next_oid)


@dataclass
class Object:
    """A single allocation on the simulated heap.

    Attributes
    ----------
    oid : int
        Stable object identity, never reused.
    size : int
        Number of cells consumed.
    address : int
        Starting cell index on the heap, or -1 if not currently placed
        (e.g. after being freed, or before an allocator places it).
    refs : list[ObjectRef]
        Outgoing references.
    mark : bool
        Mark bit used by tracing collectors.
    alive : bool
        Whether the object is currently allocated (not yet collected).
    age : int
        Number of collections the object has survived (generational GC).
    forwarding : int
        New address during compaction/copying; -1 otherwise.
    name : str
        Optional human-readable label for visualisation.
    """

    oid: int = field(default_factory=_new_oid)
    size: int = 0
    address: int = -1
    refs: List[ObjectRef] = field(default_factory=list)
    mark: bool = False
    alive: bool = True
    age: int = 0
    forwarding: int = -1
    name: str = ""
    # -- weak references ------------------------------------------------------
    weak_refs: list = field(default_factory=list)
    """List of callables invoked when this object is freed (finalizers)."""

    # -- reference management ------------------------------------------------
    def add_ref(self, target: "Object", name: str = "") -> ObjectRef:
        """Add an outgoing reference to ``target`` and return the handle."""
        ref = ObjectRef(target=target, name=name)
        self.refs.append(ref)
        return ref

    def add_weak_ref(self, target: "Object", name: str = "") -> ObjectRef:
        """Add a weak reference — does not prevent collection of ``target``.

        The returned :class:`ObjectRef` behaves like a normal ref but is
        tracked separately in :attr:`weak_refs` so that collectors can ignore
        it during marking.  When the target is freed the ref's ``target``
        becomes ``None``.
        """
        ref = ObjectRef(target=target, name=name)
        self.weak_refs.append(ref)
        return ref

    def add_finalizer(self, fn) -> None:
        """Register a callable ``fn(obj)`` to be called when this object is
        freed by the GC."""
        if not callable(fn):
            raise TypeError("finalizer must be callable")
        self._finalizers.append(fn)

    _finalizers: list = field(default_factory=list)

    def clear_dead_refs(self) -> None:
        """Drop references whose target has been freed."""
        self.refs = [r for r in self.refs if not r.is_dead]
        self.weak_refs = [r for r in self.weak_refs if not r.is_dead]

    def run_finalizers(self) -> None:
        """Invoke all registered finalizers (called by Heap.free_obj)."""
        for fn in self._finalizers:
            try:
                fn(self)
            except Exception:
                pass  # finalizers must not crash the GC
        self._finalizers.clear()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        tag = self.name or f"#{self.oid}"
        return f"Object({tag}, size={self.size}, addr={self.address})"


# ---------------------------------------------------------------------------
# Root set
# ---------------------------------------------------------------------------

@dataclass
class RootSet:
    """The set of GC roots (globals, stack slots, registers).

    Implemented as an ordered mapping from a string label to an
    :class:`Object`.  A root may be *cleared* (set to ``None``) without being
    removed from the mapping, which models a variable going out of scope.
    """

    _roots: dict = field(default_factory=dict)

    def add(self, name: str, obj: Object) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("root name must be a non-empty string")
        if not isinstance(obj, Object):
            raise TypeError("root target must be an Object")
        self._roots[name] = obj

    def remove(self, name: str) -> None:
        self._roots.pop(name, None)

    def clear_root(self, name: str) -> None:
        """Set root ``name`` to ``None`` (variable outlived its scope)."""
        if name in self._roots:
            self._roots[name] = None

    def __contains__(self, name: str) -> bool:
        return name in self._roots and self._roots[name] is not None

    def __getitem__(self, name: str) -> Optional[Object]:
        return self._roots.get(name)

    def __iter__(self) -> Iterator[Object]:
        """Iterate over live (non-None) roots."""
        for obj in self._roots.values():
            if obj is not None and obj.alive:
                yield obj

    def labels(self) -> List[str]:
        return list(self._roots.keys())

    def items(self):
        for name, obj in self._roots.items():
            if obj is not None and obj.alive:
                yield name, obj

    def __len__(self) -> int:
        return sum(1 for o in self._roots.values() if o is not None and o.alive)


# ---------------------------------------------------------------------------
# Heap
# ---------------------------------------------------------------------------

class Heap:
    """A fixed-size simulated heap.

    The heap is modelled as a list of ``size`` *cells*, each either free
    (``None``) or occupied by the :class:`Object` whose ``address`` points at
    it.  This representation makes fragmentation and compaction effects
    directly observable.
    """

    def __init__(self, size: int):
        if size <= 0:
            raise ValueError("heap size must be positive")
        self.size = size
        # ``cells[i]`` is the Object occupying cell ``i``, or ``None`` if free.
        self.cells: List[Optional[Object]] = [None] * size
        # All objects ever allocated (including dead ones, for stats).
        self._all_objects: List[Object] = []
        # Objects that currently occupy heap cells.
        self._live_list: List[Object] = []
        self.high_water_mark = 0  # max bytes ever allocated simultaneously

    # -- queries -------------------------------------------------------------
    @property
    def used(self) -> int:
        """Number of cells currently occupied."""
        return sum(1 for c in self.cells if c is not None)

    @property
    def free(self) -> int:
        return self.size - self.used

    @property
    def live_objects(self) -> List[Object]:
        """List of currently-allocated objects (shallow copy)."""
        return [o for o in self._live_list if o.alive]

    @property
    def num_live(self) -> int:
        return sum(1 for o in self._live_list if o.alive)

    def fragmentation(self) -> float:
        """Return external-fragmentation ratio in ``[0, 1]``.

        Defined as ``1 - (largest_free_block / total_free)``.  ``0`` means all
        free space is contiguous; ``1`` means it is maximally scattered (the
        largest free block is tiny relative to total free space).
        """
        total_free = self.free
        if total_free == 0:
            return 0.0
        # find largest run of None cells
        best = cur = 0
        for c in self.cells:
            if c is None:
                cur += 1
                if cur > best:
                    best = cur
            else:
                cur = 0
        if best == 0:
            return 0.0
        return 1.0 - (best / total_free)

    # -- placement -----------------------------------------------------------
    def place(self, obj: Object, address: int) -> None:
        """Record that ``obj`` occupies ``[address, address+size)``."""
        if address < 0 or address + obj.size > self.size:
            raise HeapError(
                f"cannot place object {obj.oid} at {address}: out of bounds")
        if obj.size <= 0:
            raise HeapError("object size must be positive")
        # ensure region is free
        for i in range(address, address + obj.size):
            if self.cells[i] is not None:
                occ = self.cells[i]
                raise HeapError(
                    f"cell {i} already occupied by "
                    f"{occ.oid if occ is not None else '?'}")
        for i in range(address, address + obj.size):
            self.cells[i] = obj
        obj.address = address
        obj.alive = True
        if obj not in self._live_list:
            self._live_list.append(obj)
        self._all_objects.append(obj)
        self.high_water_mark = max(self.high_water_mark, self.used)

    def free_obj(self, obj: Object) -> None:
        """Mark the cells of ``obj`` as free and run its finalizers."""
        if not obj.alive:
            return
        if obj.address < 0:
            raise HeapError(f"object {obj.oid} has no address to free")
        # run finalizers before clearing cells
        obj.run_finalizers()
        for i in range(obj.address, obj.address + obj.size):
            if i < 0 or i >= self.size:
                continue
            if self.cells[i] is obj:
                self.cells[i] = None
        obj.alive = False
        obj.address = -1
        # clear any refs pointing *out of* this object
        for ref in obj.refs:
            ref.target = None
        for ref in obj.weak_refs:
            ref.target = None
        # clear weak refs pointing *to* this object from other live objects
        for other in self._live_list:
            if other is obj or not other.alive:
                continue
            for ref in other.weak_refs:
                if ref.target is obj:
                    ref.target = None

    def move(self, obj: Object, new_address: int) -> None:
        """Relocate ``obj`` to ``new_address`` (used by compact/copy GC).

        The target cells must be free *or* already occupied by ``obj`` itself
        (overlapping move).
        """
        old_address = obj.address
        size = obj.size
        if new_address < 0 or new_address + size > self.size:
            raise HeapError("move target out of bounds")
        # tolerate overlap with own region
        for i in range(new_address, new_address + size):
            cur = self.cells[i]
            if cur is not None and cur is not obj:
                raise HeapError(
                    f"cell {i} occupied by {cur.oid} during move of {obj.oid}")
        # detach old cells
        if old_address >= 0:
            for i in range(old_address, old_address + size):
                if i < 0 or i >= self.size:
                    continue
                if self.cells[i] is obj:
                    self.cells[i] = None
        # attach new
        for i in range(new_address, new_address + size):
            self.cells[i] = obj
        obj.address = new_address

    # -- bulk operations -----------------------------------------------------
    def clear_all_marks(self) -> None:
        for o in self._live_list:
            if o.alive:
                o.mark = False
                o.forwarding = -1

    def reset(self) -> None:
        """Free every object on the heap (used by tests / scenario restart)."""
        for o in list(self._live_list):
            if o.alive:
                self.free_obj(o)
        self._live_list.clear()
        self.high_water_mark = 0

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (f"Heap(size={self.size}, used={self.used}, "
                f"live={self.num_live})")

    # -- serialization -------------------------------------------------------
    def snapshot(self) -> dict:
        """Return a JSON-serialisable snapshot of the heap state.

        Captures heap size, cell layout, and object metadata (not the Python
        identity of objects, which is not serialisable).  Useful for
        debugging, reproducibility and visualisation.
        """
        return {
            "size": self.size,
            "used": self.used,
            "free": self.free,
            "high_water_mark": self.high_water_mark,
            "fragmentation": self.fragmentation(),
            "cells": [
                (cell.oid if cell is not None else -1)
                for cell in self.cells
            ],
            "objects": [
                {
                    "oid": o.oid,
                    "size": o.size,
                    "address": o.address,
                    "name": o.name,
                    "age": o.age,
                    "alive": o.alive,
                    "refs": [
                        {"target_oid": r.target.oid if r.target else -1,
                         "name": r.name}
                        for r in o.refs
                    ],
                }
                for o in self._all_objects
            ],
        }