"""
Wavelet Packet Transform (WPT) — full binary tree decomposition.

Unlike the standard DWT which only decomposes the approximation, the WPT
decomposes *both* the approximation and detail at each level, producing a
full binary tree of 2^level subbands.  This allows adaptive subband selection
(e.g. best basis via entropy cost).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .dwt import DWT
from .wavelets import Wavelet


@dataclass
class PacketNode:
    """A node in the wavelet packet tree."""

    coeffs: List[float] = field(default_factory=list)
    level: int = 0
    path: str = ""  # e.g. "LLH" — sequence of L (low) / H (high) at each split


class WaveletPacket:
    """Full binary tree wavelet packet decomposition with best-basis selection."""

    def __init__(self, wavelet: Wavelet | str) -> None:
        if isinstance(wavelet, str):
            from .wavelets import wavelet as _w
            wavelet = _w(wavelet)
        self.wavelet = wavelet
        self.dwt = DWT(wavelet)

    def decompose(self, signal: list[float], level: int | None = None) -> dict:
        """Full wavelet packet decomposition to ``level`` levels.

        Returns a dict mapping path strings ('', 'L', 'H', 'LL', 'LH', ...)
        to coefficient lists.
        """
        n = len(signal)
        if n < self.wavelet.filter_length:
            raise ValueError(f"Signal length {n} < filter length {self.wavelet.filter_length}")
        max_level = self.dwt.max_level(n)
        if level is None:
            level = max_level
        if level > max_level:
            raise ValueError(f"Level {level} exceeds max level {max_level}")

        packets: dict[str, list[float]] = {"": list(signal)}
        for lv in range(1, level + 1):
            new_packets = {}
            for path, coeffs in packets.items():
                if len(path) == lv - 1:
                    a, d = self.dwt.decompose1(coeffs)
                    new_packets[path + "L"] = a
                    new_packets[path + "H"] = d
            packets.update(new_packets)
        return {"packets": packets, "level": level, "wavelet": self.wavelet.name,
                "input_length": n}

    def reconstruct(self, packets: dict) -> list[float]:
        """Reconstruct signal from wavelet packet coefficients.

        ``packets`` is the dict returned by decompose().
        """
        p = packets["packets"]
        level = packets["level"]
        # Reconstruct from bottom up
        current = dict(p)
        for lv in reversed(range(level)):
            new_current = {}
            for path in list(current.keys()):
                if len(path) == lv + 1:
                    parent = path[:-1]
                    sibling = path[:-1] + ("L" if path[-1] == "H" else "H")
                    if parent in new_current:
                        continue
                    low_path = parent + "L"
                    high_path = parent + "H"
                    if low_path in current and high_path in current:
                        out_len = 2 * len(current[low_path])
                        recon = self.dwt.reconstruct1(
                            current[low_path], current[high_path], out_len=out_len)
                        new_current[parent] = recon
            current.update(new_current)
        return current[""]

    def best_basis(self, packets: dict, cost_func=None) -> list[str]:
        """Select best basis using a cost function (default: Shannon entropy).

        Returns a list of path strings representing the selected nodes.
        """
        if cost_func is None:
            cost_func = shannon_entropy_cost

        level = packets["level"]
        p = packets["packets"]

        # Compute cost for each node
        costs: dict[str, float] = {}
        for path, coeffs in p.items():
            costs[path] = cost_func(coeffs)

        # Dynamic programming from leaves up
        selected: list[str] = []
        # Work from the bottom level up
        for lv in reversed(range(level + 1)):
            nodes_at_lv = [path for path in p if len(path) == lv]
            for path in nodes_at_lv:
                if lv == level:
                    # leaf: always a candidate
                    continue
                # Compare cost of this node vs sum of children's costs
                children_cost = 0.0
                children_ok = True
                for child in [path + "L", path + "H"]:
                    if child in costs:
                        children_cost += costs.get(child, float("inf"))
                    else:
                        children_ok = False
                        break
                if children_ok and costs[path] <= children_cost:
                    # This node is cheaper than its children — select it
                    # and remove children from selection
                    selected.append(path)
                    # Remove all descendants from consideration
                    for child in [path + "L", path + "H"]:
                        if child in costs:
                            costs[child] = float("inf")  # effectively deselect
        # Also include leaves that weren't superseded
        for path in p:
            if len(path) == level and costs.get(path, float("inf")) != float("inf"):
                # Check no ancestor is already selected
                ancestor_selected = False
                for s in selected:
                    if path.startswith(s) and path != s:
                        ancestor_selected = True
                        break
                if not ancestor_selected:
                    selected.append(path)
        return sorted(selected)


def shannon_entropy_cost(coeffs: list[float]) -> float:
    """Shannon entropy cost of a coefficient sequence (normalized)."""
    if not coeffs:
        return 0.0
    s = sum(abs(c) ** 2 for c in coeffs)
    if s == 0:
        return 0.0
    ent = 0.0
    for c in coeffs:
        p = (c ** 2) / s
        if p > 0:
            ent -= p * math.log2(p)
    return ent


# Import at bottom to avoid circular imports (math used in shannon_entropy_cost)
import math  # noqa: E402