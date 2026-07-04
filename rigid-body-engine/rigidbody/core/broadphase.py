"""Broad-phase collision: sweep-and-prune (sort & sweep).

The broad phase is a cheap culling step.  Its job is to produce a list of
candidate body-index pairs whose AABBs overlap, so the (expensive) narrow
phase only runs on plausible pairs.

We use the classic 3-axis sort-and-sweep on x, y, and a body-id tie-breaker
axis.  Bodies whose AABBs overlap on all axes are reported.  For simplicity
and determinism this implementation sweeps along a single axis (x) and then
does a quick y-overlap test — adequate for the sizes of scene this engine
targets.
"""

from __future__ import annotations

from typing import List, Tuple

from .body import RigidBody

__all__ = ["BroadPhase"]


class BroadPhase:
    """Sweep-and-prune broad phase tracking per-body AABB extents."""

    def __init__(self) -> None:
        # maps body_index -> (min_x, max_x)
        self._bodies: List[RigidBody] = []

    def update(self, bodies: List[RigidBody]) -> List[Tuple[int, int]]:
        """Recompute AABBs and return candidate overlapping index pairs.

        ``bodies`` is the world's body list; indices in the returned pairs
        refer to positions in that list.
        """
        self._bodies = bodies
        # Ensure every body has a fresh AABB.
        for b in bodies:
            if b.aabb is None:
                b.update_aabb()

        # Build (min_x, is_start, index) and (max_x, is_start=False, index)
        # events, then sweep.
        events: List[Tuple[float, int, int]] = []
        for i, b in enumerate(bodies):
            aabb = b.aabb
            events.append((aabb.min.x, 1, i))   # start
            events.append((aabb.max.x, 0, i))   # end (processed first on ties)

        # Sort: on a tie, ends come before starts so touching AABBs don't pair.
        events.sort(key=lambda e: (e[0], e[1]))

        active: List[int] = []
        pairs: List[Tuple[int, int]] = []
        for _, kind, idx in events:
            if kind == 1:  # start
                # Check against all currently active AABBs on the y-axis.
                aabb_i = bodies[idx].aabb
                for other in active:
                    aabb_o = bodies[other].aabb
                    if (
                        aabb_i.min.y <= aabb_o.max.y
                        and aabb_i.max.y >= aabb_o.min.y
                    ):
                        a, b = (idx, other) if idx < other else (other, idx)
                        pairs.append((a, b))
                active.append(idx)
            else:  # end
                # Remove idx from active.  Membership removal is O(n); for the
                # expected scene sizes this is fine and keeps code simple.
                if idx in active:
                    active.remove(idx)

        # De-duplicate while preserving order.
        seen = set()
        unique = []
        for p in pairs:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return unique