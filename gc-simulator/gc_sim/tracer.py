"""Graph-traversal utilities used by tracing collectors.

Provides DFS and BFS marking from a root set, plus helpers for computing the
transitive closure and detecting reference cycles.  Keeping these in one
place lets every collector share a single, well-tested traversal
implementation rather than re-rolling its own.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable, List, Set

from .heap import Object, RootSet


def mark_dfs(roots: Iterable[Object]) -> Set[int]:
    """Mark all objects reachable from ``roots`` using iterative DFS.

    Returns the set of marked object ids (for accounting).  Uses an explicit
    stack so deeply nested object graphs do not overflow the Python recursion
    limit -- the same reason real JVMs avoid recursive marking.
    """
    marked: Set[int] = set()
    stack: List[Object] = []
    for r in roots:
        if r is not None and r.alive and r.oid not in marked:
            marked.add(r.oid)
            r.mark = True
            stack.append(r)
    while stack:
        obj = stack.pop()
        for ref in obj.refs:
            tgt = ref.target
            if tgt is not None and tgt.alive and tgt.oid not in marked:
                marked.add(tgt.oid)
                tgt.mark = True
                stack.append(tgt)
    return marked


def mark_bfs(roots: Iterable[Object]) -> Set[int]:
    """Mark all objects reachable from ``roots`` using BFS."""
    marked: Set[int] = set()
    queue: deque[Object] = deque()
    for r in roots:
        if r is not None and r.alive and r.oid not in marked:
            marked.add(r.oid)
            r.mark = True
            queue.append(r)
    while queue:
        obj = queue.popleft()
        for ref in obj.refs:
            tgt = ref.target
            if tgt is not None and tgt.alive and tgt.oid not in marked:
                marked.add(tgt.oid)
                tgt.mark = True
                queue.append(tgt)
    return marked


def reachable_set(roots: Iterable[Object]) -> Set[int]:
    """Return the oid set of all objects reachable from ``roots``.

    Does not mutate mark bits (uses a local visited set).  Handy for tests
    and for verifying that a collector's marking phase agrees with the true
    reachable closure.
    """
    visited: Set[int] = set()
    stack: List[Object] = [r for r in roots if r is not None and r.alive]
    while stack:
        obj = stack.pop()
        if obj.oid in visited:
            continue
        visited.add(obj.oid)
        for ref in obj.refs:
            tgt = ref.target
            if tgt is not None and tgt.alive and tgt.oid not in visited:
                stack.append(tgt)
    return visited


def detect_cycles(roots: Iterable[Object]) -> List[List[int]]:
    """Return a list of cycles found in the object graph.

    Each cycle is returned as a list of oids.  Uses Tarjan's strongly
    connected component algorithm; an SCC with more than one node is a cycle,
    and a single-node SCC is a cycle only if the node has a self-reference.
    """
    index_counter = [0]
    stack: List[Object] = []
    on_stack: Set[int] = set()
    indices: dict = {}
    lowlinks: dict = {}
    result: List[List[int]] = []

    def strongconnect(v: Object) -> None:
        indices[v.oid] = index_counter[0]
        lowlinks[v.oid] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v.oid)
        for ref in v.refs:
            w = ref.target
            if w is None or not w.alive:
                continue
            if w.oid not in indices:
                strongconnect(w)
                lowlinks[v.oid] = min(lowlinks[v.oid], lowlinks[w.oid])
            elif w.oid in on_stack:
                lowlinks[v.oid] = min(lowlinks[v.oid], indices[w.oid])
        if lowlinks[v.oid] == indices[v.oid]:
            # pop SCC
            comp: List[int] = []
            while True:
                w = stack.pop()
                on_stack.discard(w.oid)
                comp.append(w.oid)
                if w.oid == v.oid:
                    break
            is_cycle = len(comp) > 1 or (
                len(comp) == 1 and any(r.target is not None
                                       and r.target.oid == comp[0]
                                       for r in v.refs))
            if is_cycle:
                result.append(comp)

    for r in roots:
        if r is not None and r.alive and r.oid not in indices:
            strongconnect(r)
    return result


def clear_marks(objects: Iterable[Object]) -> None:
    """Reset the mark bit on every object in ``objects``."""
    for o in objects:
        if o.alive:
            o.mark = False
            o.forwarding = -1