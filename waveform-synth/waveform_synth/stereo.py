"""
Stereo processing utilities.

Provides panning, stereo widening, and channel conversion
for richer spatial audio.
"""

import math
from typing import List, Tuple


def mono_to_stereo(samples: List[float], pan: float = 0.0) -> Tuple[List[float], List[float]]:
    """
    Convert mono samples to stereo with panning.

    Args:
        samples: Mono audio samples.
        pan: Panning from -1.0 (full left) to 1.0 (full right). 0.0 = center.

    Returns:
        Tuple of (left_channel, right_channel) sample lists.

    Raises:
        ValueError: If pan is out of range.
    """
    if not -1.0 <= pan <= 1.0:
        raise ValueError(f"Pan must be in [-1.0, 1.0], got {pan}")

    # Equal-power panning
    left_gain = math.cos((pan + 1.0) * math.pi / 4.0)
    right_gain = math.sin((pan + 1.0) * math.pi / 4.0)

    left = [s * left_gain for s in samples]
    right = [s * right_gain for s in samples]
    return left, right


def stereo_to_mono(left: List[float], right: List[float]) -> List[float]:
    """
    Mix stereo channels down to mono.

    Args:
        left: Left channel samples.
        right: Right channel samples (must be same length).

    Returns:
        Mono sample list.

    Raises:
        ValueError: If channel lengths don't match.
    """
    if len(left) != len(right):
        raise ValueError(f"Channel lengths don't match: {len(left)} vs {len(right)}")

    return [(l + r) / 2.0 for l, r in zip(left, right)]


def stereo_pan(left: List[float], right: List[float], pan: float) -> Tuple[List[float], List[float]]:
    """
    Apply panning to an existing stereo signal.

    Args:
        left: Left channel.
        right: Right channel.
        pan: Panning from -1.0 to 1.0.

    Returns:
        Panned (left, right) channels.
    """
    if not -1.0 <= pan <= 1.0:
        raise ValueError(f"Pan must be in [-1.0, 1.0], got {pan}")

    left_gain = math.cos((pan + 1.0) * math.pi / 4.0)
    right_gain = math.sin((pan + 1.0) * math.pi / 4.0)

    return [s * left_gain for s in left], [s * right_gain for s in right]


class StereoWidener:
    """
    Stereo widening effect using mid-side processing.

    Increases the perceived width of a stereo signal by boosting
    the side (difference) channel relative to the mid (sum) channel.

    Args:
        width: Width multiplier. 1.0 = no change, >1.0 = wider, <1.0 = narrower.
            Values >2.0 may cause phase issues.
    """

    def __init__(self, width: float = 1.5):
        if width < 0.0:
            raise ValueError(f"Width must be >= 0, got {width}")
        self.width = width

    def process(self, left: List[float], right: List[float]) -> Tuple[List[float], List[float]]:
        """
        Apply stereo widening.

        Args:
            left: Left channel samples.
            right: Right channel samples (must be same length).

        Returns:
            Widened (left, right) channels.
        """
        if len(left) != len(right):
            raise ValueError(f"Channel lengths don't match: {len(left)} vs {len(right)}")

        new_left = []
        new_right = []

        for l, r in zip(left, right):
            # Mid-side encoding
            mid = (l + r) / 2.0
            side = (l - r) / 2.0

            # Boost side channel
            side *= self.width

            # Decode back
            new_left.append(mid + side)
            new_right.append(mid - side)

        return new_left, new_right