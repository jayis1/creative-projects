"""Bloom filter and Counting Bloom filter implementations."""
import math
import struct
from .hashing import double_hash


class BloomFilter:
    """Classic Bloom filter for approximate set membership.

    Provides O(k) add/lookup where k is the number of hash functions.
    No false negatives; false positive rate is bounded by the configured
    ``error_rate``.

    Parameters
    ----------
    capacity : int
        Expected number of distinct elements to store.
    error_rate : float
        Target false-positive probability (e.g. 0.01 for 1%).
    """

    def __init__(self, capacity: int, error_rate: float = 0.01):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not (0 < error_rate < 1):
            raise ValueError("error_rate must be in (0, 1)")

        self.capacity = capacity
        self.error_rate = error_rate
        # Optimal bit array size
        self.num_bits = self._optimal_m(capacity, error_rate)
        # Optimal number of hash functions
        self.num_hashes = self._optimal_k(self.num_bits, capacity)
        # Bit array stored as bytearray (8 bits per cell)
        self._bits = bytearray((self.num_bits + 7) // 8)
        self.count = 0

    @staticmethod
    def _optimal_m(n: int, p: float) -> int:
        return max(1, int(math.ceil(-n * math.log(p) / (math.log(2) ** 2))))

    @staticmethod
    def _optimal_k(m: int, n: int) -> int:
        return max(1, int(round((m / n) * math.log(2))))

    def _positions(self, item) -> list[int]:
        data = self._serialize(item)
        h1, h2 = double_hash(data)
        # Use Kirsch-Mitzenmacher double hashing: g_i(x) = h1 + i*h2
        return [(h1 + i * h2) % self.num_bits for i in range(self.num_hashes)]

    @staticmethod
    def _serialize(item) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        return repr(item).encode("utf-8")

    def add(self, item) -> None:
        """Add an item to the filter."""
        for pos in self._positions(item):
            byte_idx = pos >> 3
            bit_idx = pos & 7
            self._bits[byte_idx] |= (1 << bit_idx)
        self.count += 1

    def __contains__(self, item) -> bool:
        """Check membership — may return false positives, never false negatives."""
        for pos in self._positions(item):
            byte_idx = pos >> 3
            bit_idx = pos & 7
            if not (self._bits[byte_idx] & (1 << bit_idx)):
                return False
        return True

    def __len__(self) -> int:
        return self.count

    @property
    def estimated_false_positive_rate(self) -> float:
        """Current estimated FPR based on number of items inserted."""
        # Standard formula: (1 - e^(-k*n/m))^k
        n = self.count
        return (1 - math.exp(-self.num_hashes * n / self.num_bits)) ** self.num_hashes

    def to_bytes(self) -> bytes:
        """Serialize to a portable byte string."""
        # Use consistent format: capacity(Q), error_rate(d double),
        # num_bits(Q), num_hashes(Q), count(Q) = 8+8+8+8+8 = 40 bytes
        header = struct.pack(
            "<QdQQQ",
            self.capacity,
            self.error_rate,
            self.num_bits,
            self.num_hashes,
            self.count,
        )
        return header + bytes(self._bits)

    @classmethod
    def from_bytes(cls, data: bytes) -> "BloomFilter":
        """Deserialize from bytes produced by ``to_bytes``."""
        capacity, error_rate, num_bits, num_hashes, count = struct.unpack(
            "<QdQQQ", data[:40]
        )
        bf = cls(capacity, error_rate)
        bf.num_bits = num_bits
        bf.num_hashes = num_hashes
        bf.count = count
        bf._bits = bytearray(data[40:])
        return bf


class CountingBloomFilter:
    """Counting Bloom filter supporting deletion.

    Uses 4-bit counters (values 0-15) instead of single bits.  An item
    is present when *all* of its k counters are >= 1.  Counter saturation
    at 15 is possible but rare for reasonable load factors.

    Parameters
    ----------
    capacity : int
        Expected number of distinct elements.
    error_rate : float
        Target false-positive probability.
    """

    def __init__(self, capacity: int, error_rate: float = 0.01):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not (0 < error_rate < 1):
            raise ValueError("error_rate must be in (0, 1)")

        self.capacity = capacity
        self.error_rate = error_rate
        self.num_bits = BloomFilter._optimal_m(capacity, error_rate)
        self.num_hashes = BloomFilter._optimal_k(self.num_bits, capacity)
        # 4-bit counters stored 2 per byte
        self._counters = bytearray((self.num_bits + 1) // 2)
        self.count = 0

    def _positions(self, item) -> list[int]:
        data = BloomFilter._serialize(item)
        h1, h2 = double_hash(data)
        return [(h1 + i * h2) % self.num_bits for i in range(self.num_hashes)]

    def _get_counter(self, pos: int) -> int:
        byte_idx = pos >> 1
        if pos & 1:
            return self._counters[byte_idx] >> 4
        return self._counters[byte_idx] & 0x0F

    def _set_counter(self, pos: int, val: int) -> None:
        byte_idx = pos >> 1
        if pos & 1:
            self._counters[byte_idx] = (self._counters[byte_idx] & 0x0F) | ((val & 0x0F) << 4)
        else:
            self._counters[byte_idx] = (self._counters[byte_idx] & 0xF0) | (val & 0x0F)

    def add(self, item) -> None:
        for pos in self._positions(item):
            c = self._get_counter(pos)
            if c < 15:  # saturate at 15
                self._set_counter(pos, c + 1)
        self.count += 1

    def remove(self, item) -> bool:
        """Remove an item. Returns True if item was (probabilistically) present.

        Note: If the item is a false positive (never actually added but
        counters happen to be set), this will still decrement counters.
        The ``count`` field is only decremented if removal succeeds, which
        keeps the count accurate relative to successful add/remove pairs.
        """
        positions = self._positions(item)
        if not all(self._get_counter(p) > 0 for p in positions):
            return False
        for pos in positions:
            c = self._get_counter(pos)
            if c > 0:
                self._set_counter(pos, c - 1)
        # Only decrement count if we're confident this was a real element.
        # Since we can't distinguish false positives from real elements,
        # we decrement to maintain add/remove balance.  Users should be
        # aware that count reflects net (adds - successful_removes).
        self.count -= 1
        return True

    def __contains__(self, item) -> bool:
        return all(self._get_counter(p) > 0 for p in self._positions(item))

    def __len__(self) -> int:
        return self.count