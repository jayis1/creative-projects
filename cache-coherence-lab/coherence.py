"""Trace-driven MESI cache-coherence simulator with deterministic bus events."""
from dataclasses import dataclass, field
from collections import Counter

STATES = {"I", "S", "E", "M"}

@dataclass
class Cache:
    lines: dict[int, str] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

class MESISimulator:
    """Simulate private direct-mapped caches and a single snooping bus."""
    def __init__(self, cores: int = 2, capacity: int = 4, line_size: int = 16):
        if cores < 1 or capacity < 1 or line_size < 1:
            raise ValueError("cores, capacity, and line_size must be positive")
        self.caches = [Cache() for _ in range(cores)]
        self.capacity, self.line_size = capacity, line_size
        self.stats = Counter()

    def _tag(self, address: int) -> int:
        return address // self.line_size

    def access(self, core: int, op: str, address: int) -> str:
        """Apply one read (R) or write (W); return resulting MESI state."""
        if not isinstance(core, int) or not 0 <= core < len(self.caches):
            raise ValueError("core index out of range")
        if op not in ("R", "W"):
            raise ValueError("operation must be R or W")
        if not isinstance(address, int) or address < 0:
            raise ValueError("address must be a nonnegative integer")
        tag = self._tag(address)
        cache = self.caches[core]
        state = cache.lines.get(tag, "I")
        if state == "I":
            cache.misses += 1
            self.stats["misses"] += 1
            self._ensure_capacity(cache, tag)
            peers = [c for i, c in enumerate(self.caches) if i != core and c.lines.get(tag, "I") != "I"]
            if op == "R":
                state = "S" if peers else "E"
                if peers:
                    self.stats["read_shared"] += 1
                    for peer in peers:
                        if peer.lines.get(tag) == "E":
                            peer.lines[tag] = "S"
                        elif peer.lines.get(tag) == "M":
                            peer.lines[tag] = "S"
                            self.stats["writebacks"] += 1
            else:
                for peer in peers:
                    if peer.lines.pop(tag) == "M":
                        self.stats["writebacks"] += 1
                self.stats["invalidations"] += len(peers)
                state = "M"
        else:
            cache.hits += 1
            self.stats["hits"] += 1
            if op == "W":
                for i, peer in enumerate(self.caches):
                    if i != core and peer.lines.pop(tag, None) is not None:
                        self.stats["invalidations"] += 1
                state = "M"
            elif state == "E":
                state = "E"
        cache.lines[tag] = state
        self._assert_invariants()
        return state

    def _ensure_capacity(self, cache: Cache, incoming: int) -> None:
        """Bound each private cache; deterministic FIFO-by-insertion eviction."""
        if incoming in cache.lines:
            return
        if len(cache.lines) >= self.capacity:
            victim = next(iter(cache.lines))
            evicted = cache.lines.pop(victim)
            if evicted == "M":
                self.stats["writebacks"] += 1
            self.stats["evictions"] += 1

    def _assert_invariants(self) -> None:
        tags = set().union(*(c.lines.keys() for c in self.caches))
        for tag in tags:
            holders = [c.lines[tag] for c in self.caches if tag in c.lines]
            if "M" in holders and len(holders) != 1:
                raise AssertionError("modified line must be exclusive")
            if "E" in holders and len(holders) != 1:
                raise AssertionError("exclusive line must be exclusive")
            if len(holders) > 1 and any(s != "S" for s in holders):
                raise AssertionError("shared copies must all be shared")

    def run(self, trace):
        """Consume iterable of (core, operation, byte_address) records."""
        results = []
        for index, record in enumerate(trace):
            if not isinstance(record, (list, tuple)) or len(record) != 3:
                raise ValueError(f"trace record {index} must contain core, operation, address")
            results.append(self.access(*record))
        return results

    def report(self):
        return {"cores": len(self.caches), "stats": dict(sorted(self.stats.items())),
                "per_core": [{"hits": c.hits, "misses": c.misses, "lines": dict(sorted(c.lines.items()))} for c in self.caches]}
