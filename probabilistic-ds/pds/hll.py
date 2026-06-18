"""HyperLogLog: approximate cardinality estimation.

Estimates the number of distinct elements in a stream using O(2^p) bytes
of memory, with relative error ≈ 1.04/sqrt(2^p).
"""
import math
from .hashing import md5_128


class HyperLogLog:
    """HyperLogLog cardinality estimator.

    Parameters
    ----------
    precision : int
        Number of bits used for register index (4-16).  Uses 2^precision
        registers, each 5 bits.  Standard error ≈ 1.04/sqrt(2^precision).

    Examples
    --------
    >>> hll = HyperLogLog(precision=12)
    >>> for i in range(10000):
    ...     hll.add(str(i))
    >>> abs(hll.estimate() - 10000) / 10000 < 0.05
    True
    """

    def __init__(self, precision: int = 14):
        if not (4 <= precision <= 16):
            raise ValueError("precision must be in [4, 16]")
        self.precision = precision
        self.m = 1 << precision
        self._registers = bytearray(self.m)  # each register stores 0-255 (we use 0-50)
        self._alpha = self._compute_alpha(self.m)

    @staticmethod
    def _compute_alpha(m: int) -> float:
        if m == 16:
            return 0.673
        if m == 32:
            return 0.697
        if m == 64:
            return 0.709
        return 0.7213 / (1 + 1.079 / m)

    def add(self, item) -> None:
        """Add an item to the estimator."""
        data = self._serialize(item)
        x = md5_128(data)
        # Use top `precision` bits as register index
        idx = x >> (128 - self.precision)
        # Count leading zeros in the remaining (128 - precision) bits + 1
        remaining_bits = 128 - self.precision
        remaining = x & ((1 << remaining_bits) - 1)
        # rank = number of leading zeros in the remaining field + 1
        if remaining == 0:
            rank = remaining_bits + 1
        else:
            rank = remaining_bits - remaining.bit_length() + 1
        if rank > self._registers[idx]:
            self._registers[idx] = rank

    def estimate(self) -> float:
        """Estimate the number of distinct elements seen."""
        raw = self._alpha * self.m * self.m / sum(2 ** (-r) for r in self._registers)

        # Small range correction
        if raw <= 2.5 * self.m:
            # Correct for linear counting if there are zero registers
            zeros = self._registers.count(0)
            if zeros != 0:
                return self.m * math.log(self.m / zeros)
        # Large range correction
        if raw > (1 << 128) / 30:
            return -(1 << 128) * math.log(1 - raw / (1 << 128))
        return raw

    def merge(self, other: "HyperLogLog") -> None:
        """Merge another HLL into this one (take register-wise max)."""
        if self.precision != other.precision:
            raise ValueError("Cannot merge HLLs with different precision")
        for i in range(self.m):
            if other._registers[i] > self._registers[i]:
                self._registers[i] = other._registers[i]

    @staticmethod
    def _serialize(item) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        return repr(item).encode("utf-8")

    @property
    def relative_error(self) -> float:
        """Theoretical standard error for this precision."""
        return 1.04 / math.sqrt(self.m)