"""
ASCII waveform visualization.

Renders audio waveforms as ASCII art for terminal display.
Supports multiple visualization modes: waveform, frequency bars,
and envelope display.
"""

import math
from typing import List, Optional


def ascii_waveform(
    samples: List[float],
    width: int = 80,
    height: int = 20,
    title: Optional[str] = None,
) -> str:
    """
    Render an audio waveform as ASCII art.

    Samples are downsampled to fit the width, and the amplitude is mapped
    to the vertical dimension of the display.

    Args:
        samples: Audio samples in [-1.0, 1.0] range (or any range).
        width: Display width in characters (must be > 0).
        height: Display height in lines (must be > 0).
        title: Optional title to display above the waveform.

    Returns:
        Multi-line string of ASCII art.

    Raises:
        ValueError: If samples is empty or dimensions are invalid.
    """
    if not samples:
        raise ValueError("Cannot visualize empty sample list")
    if width <= 0:
        raise ValueError(f"Width must be > 0, got {width}")
    if height <= 0:
        raise ValueError(f"Height must be > 0, got {height}")

    # Find amplitude range
    max_val = max(abs(s) for s in samples)
    if max_val == 0:
        max_val = 1.0  # Avoid division by zero for silence

    # Downsample: map width pixels to sample indices
    step = len(samples) / width
    downsampled = []
    for i in range(width):
        start_idx = int(i * step)
        end_idx = min(int((i + 1) * step), len(samples))
        if start_idx < end_idx:
            # Use the sample closest to the center of the bin
            mid_idx = (start_idx + end_idx) // 2
            downsampled.append(samples[mid_idx])
        else:
            downsampled.append(samples[start_idx] if start_idx < len(samples) else 0.0)

    # Build the ASCII display
    lines = []

    # Add title
    if title:
        if len(title) > width:
            title = title[:width - 3] + "..."
        lines.append(title.center(width))

    # Top border
    lines.append("┌" + "─" * width + "┐")

    # Render each row from top (positive) to bottom (negative)
    # Row 0 = max positive, row height-1 = max negative
    for row in range(height):
        # Map row to amplitude: top is +1, bottom is -1
        normalized_row = 1.0 - (row / (height - 1)) * 2.0  # +1 to -1

        line_chars = []
        for col_idx, s in enumerate(downsampled):
            normalized_s = s / max_val  # in [-1, 1]
            # Check if this sample falls in this row
            row_top = normalized_row + (1.0 / (height - 1))
            row_bottom = normalized_row - (1.0 / (height - 1))

            if row_bottom <= normalized_s <= row_top:
                line_chars.append("█")
            elif abs(normalized_s - normalized_row) < (2.0 / height):
                line_chars.append("▓")
            else:
                line_chars.append(" ")

        lines.append("│" + "".join(line_chars) + "│")

    # Bottom border
    lines.append("└" + "─" * width + "┘")

    # Scale markers
    lines.append(f" +{max_val:.2f}".rjust(width + 2))
    lines.append(f" -{max_val:.2f}".rjust(width + 2))

    return "\n".join(lines)


def ascii_frequency_bars(
    samples: List[float],
    num_bars: int = 32,
    sample_rate: int = 44100,
    title: Optional[str] = None,
    max_bar_height: int = 20,
) -> str:
    """
    Render a simple frequency spectrum visualization as ASCII bars.

    Uses a basic DFT over frequency bands (not FFT for simplicity).

    Args:
        samples: Audio samples.
        num_bars: Number of frequency bars to display.
        sample_rate: Sample rate for frequency calculation.
        title: Optional title.
        max_bar_height: Maximum bar height in characters.

    Returns:
        Multi-line string of ASCII bar chart.
    """
    if not samples:
        raise ValueError("Cannot visualize empty sample list")

    n = len(samples)
    bar_heights = []

    # Compute energy in each frequency band
    for bar in range(num_bars):
        # Frequency range for this bar
        low_freq = (bar / num_bars) * (sample_rate / 2)
        high_freq = ((bar + 1) / num_bars) * (sample_rate / 2)

        # Compute DFT magnitude for this band (average a few frequency bins)
        num_bins = max(1, n // num_bars)
        magnitude_sum = 0.0
        for k in range(num_bins):
            freq_idx = bar * num_bins + k
            if freq_idx >= n:
                break
            real = 0.0
            imag = 0.0
            for j in range(min(256, n)):  # Limit computation for performance
                angle = 2.0 * math.pi * freq_idx * j / n
                real += samples[j] * math.cos(angle)
                imag -= samples[j] * math.sin(angle)
            magnitude = math.sqrt(real * real + imag * imag)
            magnitude_sum += magnitude

        avg_magnitude = magnitude_sum / max(1, num_bins)
        bar_heights.append(avg_magnitude)

    # Normalize bar heights
    max_height = max(bar_heights) if bar_heights else 1.0
    if max_height == 0:
        max_height = 1.0

    lines = []
    if title:
        lines.append(title.center(num_bars))

    # Draw bars from top to bottom
    for row in range(max_bar_height, 0, -1):
        line = ""
        for h in bar_heights:
            normalized = h / max_height
            bar_h = int(normalized * max_bar_height)
            if bar_h >= row:
                line += "█"
            elif bar_h >= row - 0.5:
                line += "▓"
            else:
                line += " "
        lines.append(line)

    # Frequency labels
    lines.append(f"{0:>5}Hz{' ' * (num_bars - 10)}{sample_rate // 2}Hz")

    return "\n".join(lines)


def ascii_envelope(
    envelope: List[float],
    width: int = 60,
    height: int = 10,
    title: Optional[str] = None,
) -> str:
    """
    Render an ADSR envelope as ASCII art.

    Args:
        envelope: Envelope values in [0.0, 1.0] range.
        width: Display width.
        height: Display height.
        title: Optional title.

    Returns:
        Multi-line string.
    """
    if not envelope:
        raise ValueError("Cannot visualize empty envelope")

    max_val = max(abs(e) for e in envelope) or 1.0

    # Downsample
    step = len(envelope) / width
    downsampled = []
    for i in range(width):
        idx = min(int(i * step), len(envelope) - 1)
        downsampled.append(envelope[idx])

    lines = []
    if title:
        lines.append(title)

    lines.append("1.0 ┤")

    for row in range(height):
        normalized_row = 1.0 - (row / height)
        line = "    │"
        for val in downsampled:
            normalized_val = val / max_val
            if abs(normalized_val - normalized_row) < (1.0 / height):
                line += "█"
            else:
                line += " "
        lines.append(line)

    lines.append("0.0 ┤" + " " * width)
    lines.append("    └" + "─" * width)

    return "\n".join(lines)