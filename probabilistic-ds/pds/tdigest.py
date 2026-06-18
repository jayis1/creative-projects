"""T-Digest: approximate streaming quantiles.

Maintains a set of centroids that adaptively compress toward the tails
of the distribution, giving high accuracy at extreme quantiles (1st/99th
percentile) and moderate accuracy at the median.

Based on Dunning's t-digest (2019).  This implementation uses the
"alternating sort" merging variant.
"""
import math
import bisect


class _Centroid:
    __slots__ = ("mean", "count")

    def __init__(self, mean: float, count: float):
        self.mean = mean
        self.count = count

    def add(self, mean: float, count: float) -> None:
        self.mean = (self.mean * self.count + mean * count) / (self.count + count)
        self.count += count

    def __repr__(self):
        return f"_Centroid(mean={self.mean:.4f}, count={self.count:.1f})"


class TDigest:
    """Approximate streaming quantile estimator.

    Parameters
    ----------
    compression : float
        Controls accuracy vs. memory tradeoff.  Higher = more centroids
        = better accuracy.  Default 100.

    Examples
    --------
    >>> import random
    >>> td = TDigest(compression=100)
    >>> data = [random.gauss(0, 1) for _ in range(10000)]
    >>> for x in data:
    ...     td.add(x)
    >>> abs(td.quantile(0.5)) < 0.2  # median near 0
    True
    """

    def __init__(self, compression: float = 100):
        if compression < 10:
            raise ValueError("compression must be >= 10")
        self.compression = compression
        self._centroids: list[_Centroid] = []
        self._total_count = 0.0
        self._min = math.inf
        self._max = -math.inf
        self._sorted = True

    def add(self, value: float, count: float = 1.0) -> None:
        """Add a value (with optional weight)."""
        if count <= 0:
            return
        if not math.isfinite(value):
            raise ValueError("value must be finite")

        self._min = min(self._min, value)
        self._max = max(self._max, value)
        self._total_count += count
        self._sorted = False

        # Find nearest centroid by mean
        # For simplicity, insert as a new centroid; compress periodically
        self._centroids.append(_Centroid(value, count))

        # Compress when we have too many centroids
        if len(self._centroids) > self.compression * 10:
            self._compress()

    def _ensure_sorted(self) -> None:
        if not self._sorted:
            self._centroids.sort(key=lambda c: c.mean)
            self._sorted = True

    def _compress(self) -> None:
        """Merge nearby centroids to bound total count."""
        self._ensure_sorted()
        if len(self._centroids) <= 1:
            return

        total = self._total_count
        new_centroids: list[_Centroid] = []
        # Alternate starting point to avoid bias
        start = 0
        # Shuffle-like: process in order, accumulate while size function allows

        i = 0
        while i < len(self._centroids):
            cur = self._centroids[i]
            # Cumulative quantile up to this centroid
            cum_count = sum(c.count for c in new_centroids)
            q = (cum_count + cur.count / 2) / total
            # Size function: k1 scale
            k_size = self.compression * 4 * total * q * (1 - q) / len(self._centroids)

            # Try to merge next centroid into current
            j = i + 1
            while j < len(self._centroids):
                next_c = self._centroids[j]
                merged_count = cur.count + next_c.count
                new_q = (cum_count + merged_count / 2) / total
                new_k_size = self.compression * 4 * total * new_q * (1 - new_q) / len(self._centroids)
                if merged_count <= new_k_size and merged_count <= k_size + 1:
                    cur.add(next_c.mean, next_c.count)
                    j += 1
                else:
                    break
                k_size = new_k_size

            new_centroids.append(cur)
            i = j

        self._centroids = new_centroids
        self._sorted = True

    def quantile(self, q: float) -> float:
        """Estimate the q-th quantile (0 <= q <= 1)."""
        if not (0 <= q <= 1):
            raise ValueError("q must be in [0, 1]")
        if not self._centroids:
            return float("nan")
        self._ensure_sorted()
        if len(self._centroids) == 1:
            return self._centroids[0].mean

        if q == 0:
            return self._min
        if q == 1:
            return self._max

        target = q * self._total_count
        # Linear interpolation between centroids
        cum = 0.0
        for i, c in enumerate(self._centroids):
            if cum + c.count / 2 >= target:
                if i == 0:
                    # Interpolate between min and first centroid mean
                    half = c.count / 2
                    if half > 0:
                        return self._min + (c.mean - self._min) * (target / half)
                    return self._min
                prev = self._centroids[i - 1]
                # Interpolate between prev centroid center and current center
                prev_center = cum  # center of prev centroid = cum (after adding prev)
                # cum at this point = sum of counts of centroids 0..i-1
                # prev centroid center is at cum - prev.count/2 + prev.count = cum
                # Actually: cum = total count of centroids before this one
                # prev center = cum - prev.count / 2... but we need to be precise.
                # The center of centroid i-1 is at position cum (end of i-1's range
                # start is cum - prev.count, center is cum - prev.count/2).
                # We want to interpolate between prev center and current center.
                prev_c = self._centroids[i - 1]
                prev_center_pos = cum - prev_c.count / 2  # center of prev
                cur_center_pos = cum + c.count / 2         # center of current
                if cur_center_pos > prev_center_pos:
                    return prev_c.mean + (c.mean - prev_c.mean) * \
                        (target - prev_center_pos) / (cur_center_pos - prev_center_pos)
                return c.mean
            cum += c.count

        # Interpolate between last centroid and max
        last = self._centroids[-1]
        last_center = self._total_count - last.count / 2
        tail_span = self._total_count - last_center
        if tail_span > 0:
            return last.mean + (self._max - last.mean) * (target - last_center) / tail_span
        return self._max

    def merge(self, other: "TDigest") -> None:
        """Merge another t-digest into this one."""
        self._centroids.extend(other._centroids)
        self._total_count += other._total_count
        self._min = min(self._min, other._min)
        self._max = max(self._max, other._max)
        self._sorted = False
        self._compress()

    @property
    def num_centroids(self) -> int:
        return len(self._centroids)

    def cdf(self, value: float) -> float:
        """Estimate the CDF at ``value`` (fraction of data <= value)."""
        self._ensure_sorted()
        if value <= self._min:
            return 0.0
        if value >= self._max:
            return 1.0
        cum = 0.0
        for c in self._centroids:
            if c.mean < value:
                cum += c.count
            else:
                # Partial contribution
                cum += c.count * 0.5
                break
        return cum / self._total_count