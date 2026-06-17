"""Waveform comparison and analysis utilities."""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple
from .core import Signal

logger = logging.getLogger(__name__)


def compare_traces(
    trace_a: List[Tuple[int, Signal]],
    trace_b: List[Tuple[int, Signal]],
    name_a: str = "A",
    name_b: str = "B",
) -> Dict:
    """Compare two waveform traces and report differences.

    Args:
        trace_a: First trace as list of (time_ns, Signal) tuples.
        trace_b: Second trace as list of (time_ns, Signal) tuples.
        name_a: Name for the first trace.
        name_b: Name for the second trace.

    Returns:
        Dictionary with comparison results: match (bool), differences (list),
        total_transitions (tuple), signal_at_end (tuple).
    """
    # Build signal maps
    def build_signal_map(trace: List[Tuple[int, Signal]]) -> Dict[int, Signal]:
        result = {}
        for t, sig in trace:
            result[t] = sig
        return result

    map_a = build_signal_map(trace_a)
    map_b = build_signal_map(trace_b)

    # Get all time points
    all_times = sorted(set(map_a.keys()) | set(map_b.keys()))
    if not all_times:
        return {
            "match": True,
            "differences": [],
            "total_transitions": (0, 0),
            "signal_at_end": (Signal.UNDEFINED, Signal.UNDEFINED),
        }

    # Sample both signals at each time point
    current_a = Signal.UNDEFINED
    current_b = Signal.UNDEFINED
    differences = []
    transitions_a = 0
    transitions_b = 0

    for t in all_times:
        if t in map_a:
            if map_a[t] != current_a:
                transitions_a += 1
                current_a = map_a[t]
        if t in map_b:
            if map_b[t] != current_b:
                transitions_b += 1
                current_b = map_b[t]

        if current_a != current_b:
            differences.append({
                "time_ns": t,
                name_a: current_a.name,
                name_b: current_b.name,
            })

    return {
        "match": len(differences) == 0,
        "differences": differences,
        "total_transitions": (transitions_a, transitions_b),
        "signal_at_end": (current_a, current_b),
    }


def analyze_trace(trace: List[Tuple[int, Signal]], name: str = "signal") -> Dict:
    """Analyze a waveform trace and return statistics.

    Args:
        trace: Waveform trace as list of (time_ns, Signal) tuples.
        name: Name of the signal.

    Returns:
        Dictionary with analysis results including transitions, duty cycle,
        frequency, etc.
    """
    if not trace:
        return {
            "name": name,
            "transitions": 0,
            "duration_ns": 0,
            "time_high_ns": 0,
            "time_low_ns": 0,
            "duty_cycle": 0.0,
            "frequency_mhz": 0.0,
            "start_signal": None,
            "end_signal": None,
        }

    transitions = 0
    time_high_ns = 0
    time_low_ns = 0
    rising_edges = []
    falling_edges = []
    prev_signal = trace[0][1]
    prev_time = trace[0][0]

    for i in range(1, len(trace)):
        t, sig = trace[i]
        if sig != prev_signal:
            transitions += 1
            duration = t - prev_time
            if prev_signal == Signal.HIGH:
                time_high_ns += duration
            elif prev_signal == Signal.LOW:
                time_low_ns += duration
            if prev_signal == Signal.LOW and sig == Signal.HIGH:
                rising_edges.append(t)
            elif prev_signal == Signal.HIGH and sig == Signal.LOW:
                falling_edges.append(t)
            prev_signal = sig
            prev_time = t

    # Add time from last transition to end
    total_duration = trace[-1][0] - trace[0][0] if len(trace) > 1 else 0
    remaining = total_duration - time_high_ns - time_low_ns
    if prev_signal == Signal.HIGH:
        time_high_ns += remaining
    elif prev_signal == Signal.LOW:
        time_low_ns += remaining

    duty_cycle = time_high_ns / total_duration if total_duration > 0 else 0.0

    # Calculate frequency from rising edges
    frequency_mhz = 0.0
    if len(rising_edges) >= 2:
        # Average period from rising edges
        periods = [rising_edges[i+1] - rising_edges[i] for i in range(len(rising_edges) - 1)]
        avg_period_ns = sum(periods) / len(periods)
        if avg_period_ns > 0:
            frequency_mhz = 1000.0 / avg_period_ns  # ns to MHz

    return {
        "name": name,
        "transitions": transitions,
        "duration_ns": total_duration,
        "time_high_ns": time_high_ns,
        "time_low_ns": time_low_ns,
        "duty_cycle": duty_cycle,
        "rising_edges": len(rising_edges),
        "falling_edges": len(falling_edges),
        "frequency_mhz": round(frequency_mhz, 4),
        "start_signal": trace[0][1].name,
        "end_signal": trace[-1][1].name,
    }


def format_trace_analysis(analysis: Dict) -> str:
    """Format a trace analysis as a human-readable string.

    Args:
        analysis: Analysis dictionary from analyze_trace().

    Returns:
        Formatted string.
    """
    lines = [
        f"Trace Analysis: {analysis['name']}",
        f"  Duration: {analysis['duration_ns']} ns",
        f"  Transitions: {analysis['transitions']}",
        f"  Time HIGH: {analysis['time_high_ns']} ns",
        f"  Time LOW: {analysis['time_low_ns']} ns",
        f"  Duty Cycle: {analysis['duty_cycle']:.1%}",
        f"  Rising Edges: {analysis['rising_edges']}",
        f"  Falling Edges: {analysis['falling_edges']}",
        f"  Frequency: {analysis['frequency_mhz']:.4f} MHz",
        f"  Start: {analysis['start_signal']}",
        f"  End: {analysis['end_signal']}",
    ]
    return "\n".join(lines)