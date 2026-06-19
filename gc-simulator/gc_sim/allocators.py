"""Allocation strategies for the simulated heap.

An :class:`Allocator` decides *where* on the heap a new object should be
placed.  Different strategies have different fragmentation and speed
characteristics, which interact in interesting ways with the choice of
garbage collector.

Two allocators are provided:

* :class:`BumpAllocator` -- classic fast pointer-bump, no reuse of freed
  memory until a compaction resets the bump pointer.
* :class:`FreeListAllocator` -- maintains a free-block list and reuses freed
  space, with first-fit / best-fit / worst-fit policies.

A bump allocator combined with a copying/compacting collector mirrors the
behaviour of the Java young generation; a free-list allocator combined with
mark-sweep mirrors the old generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

from .heap import Heap, HeapError, Object

if TYPE_CHECKING:
    pass


class Allocator(ABC):
    """Abstract base class for allocation strategies."""

    def __init__(self, heap: Heap):
        self.heap = heap

    @abstractmethod
    def allocate(self, size: int, name: str = "") -> Optional[Object]:
        """Return a newly placed :class:`Object` of ``size`` cells, or
        ``None`` if the request cannot be satisfied."""

    @abstractmethod
    def reset(self) -> None:
        """Reset any internal state (called after a full compaction)."""


# ---------------------------------------------------------------------------
# Bump allocator
# ---------------------------------------------------------------------------

class BumpAllocator(Allocator):
    """A simple bump-pointer allocator.

    Allocates sequentially from a ``cursor`` that only moves forward.  Freed
    memory is *not* reused until :meth:`reset` is called (typically by a
    compacting or copying collector).  This gives O(1) allocation and no
    fragmentation while space remains, which is exactly why young-generation
    collectors pair with it.
    """

    def __init__(self, heap: Heap):
        super().__init__(heap)
        self.cursor = 0

    def allocate(self, size: int, name: str = "") -> Optional[Object]:
        if size <= 0:
            raise ValueError("allocation size must be positive")
        if self.cursor + size > self.heap.size:
            return None  # out of memory in this bump region
        obj = Object(size=size, name=name)
        self.heap.place(obj, self.cursor)
        self.cursor += size
        return obj

    def reset(self) -> None:
        self.cursor = 0
        # Re-anchor cursor at the end of the last live object so subsequent
        # bumps continue packing tightly.  After a compaction all live objects
        # are at the bottom of the heap, so cursor = used is correct.
        self.cursor = self.heap.used


# ---------------------------------------------------------------------------
# Free-list allocator
# ---------------------------------------------------------------------------

class FreeListAllocator(Allocator):
    """A free-list allocator that reuses freed blocks.

    A *free block* is a maximal contiguous run of ``None`` cells.  The
    allocator searches the list for a block large enough to hold the request
    and, depending on ``policy``, picks one of:

    * ``"first_fit"``  -- the first block that is large enough (fast scan).
    * ``"best_fit"``   -- the smallest block that is large enough (reduces
      waste from internal fragmentation).
    * ``"worst_fit"``  -- the largest block (reduces external fragmentation by
      leaving big blocks behind for future big allocations).
    """

    POLICIES = ("first_fit", "best_fit", "worst_fit")

    def __init__(self, heap: Heap, policy: str = "first_fit"):
        super().__init__(heap)
        if policy not in self.POLICIES:
            raise ValueError(f"unknown policy {policy!r}")
        self.policy = policy

    # -- free-block discovery ------------------------------------------------
    def _free_blocks(self) -> List[tuple]:
        """Return ``[(start, length), ...]`` for every maximal free run."""
        blocks: List[tuple] = []
        i = 0
        cells = self.heap.cells
        n = self.heap.size
        while i < n:
            if cells[i] is None:
                start = i
                while i < n and cells[i] is None:
                    i += 1
                blocks.append((start, i - start))
            else:
                i += 1
        return blocks

    def _select(self, blocks: List[tuple], size: int) -> Optional[int]:
        """Return the start address of the chosen block, or ``None``."""
        fitting = [(s, length) for s, length in blocks if length >= size]
        if not fitting:
            return None
        if self.policy == "first_fit":
            return fitting[0][0]
        if self.policy == "best_fit":
            return min(fitting, key=lambda b: (b[1], b[0]))[0]
        # worst_fit
        return max(fitting, key=lambda b: (b[1], -b[0]))[0]

    def allocate(self, size: int, name: str = "") -> Optional[Object]:
        if size <= 0:
            raise ValueError("allocation size must be positive")
        blocks = self._free_blocks()
        addr = self._select(blocks, size)
        if addr is None:
            return None
        obj = Object(size=size, name=name)
        self.heap.place(obj, addr)
        return obj

    def reset(self) -> None:
        # Free-list allocator derives its state from the heap itself, so a
        # reset is a no-op.  Provided for API symmetry with BumpAllocator.
        pass