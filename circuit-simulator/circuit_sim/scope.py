"""Oscilloscope: waveform visualization and export for circuit simulation traces."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from .core import Signal


class Oscilloscope:
    """
    Captures and renders digital waveforms from simulation traces.
    
    Produces ASCII waveform diagrams and VCD (Value Change Dump) files
    for viewing in external tools like GTKWave.
    """

    def __init__(self):
        self._traces: Dict[str, List[Tuple[int, Signal]]] = {}
        self._time_scale: int = 1  # nanoseconds per unit

    def add_trace(self, name: str, history: List[Tuple[int, Signal]]) -> None:
        """Add a waveform trace for a named signal."""
        self._traces[name] = history

    def render_ascii(self, width: int = 60, time_range: Optional[Tuple[int, int]] = None) -> str:
        """
        Render all traces as an ASCII waveform diagram.
        
        Args:
            width: Character width of the waveform area.
            time_range: Optional (start_ns, end_ns) range. If None, uses full range.
        
        Returns:
            Multi-line string with ASCII waveforms.
        """
        if not self._traces:
            return "(no traces)"

        # Determine time range
        all_times = []
        for history in self._traces.values():
            all_times.extend(t for t, _ in history)
        
        if not all_times:
            return "(no data)"

        if time_range:
            t_start, t_end = time_range
        else:
            t_start = min(all_times)
            t_end = max(all_times)

        if t_start == t_end:
            t_end = t_start + 1

        duration = t_end - t_start
        lines = []

        # Header with time markers
        header = "Time(ns)"
        lines.append(f"{header:>16} {t_start:<8} {'':>{width-16}} {t_end}")

        for name, history in self._traces.items():
            waveform = self._render_wave(name, history, width, t_start, t_end)
            lines.append(waveform)

        return '\n'.join(lines)

    def _render_wave(self, name: str, history: List[Tuple[int, Signal]],
                     width: int, t_start: int, t_end: int) -> str:
        """Render a single waveform line."""
        if not history:
            return f"{name:>16} {'?' * width}"

        # Build a mapping of time -> signal
        duration = t_end - t_start
        chars = ['?'] * width
        prev_signal = Signal.UNDEFINED

        # Fill in the waveform
        for t, signal in history:
            if t < t_start:
                prev_signal = signal
                continue
            if t > t_end:
                break
            
            # Calculate position
            pos = int((t - t_start) / duration * (width - 1))
            pos = max(0, min(width - 1, pos))

            # Fill from previous signal to current position
            signal_char = self._signal_char(signal)
            for i in range(pos, width):
                chars[i] = signal_char

        # Draw transitions
        prev_signal = Signal.UNDEFINED
        prev_pos = 0
        for t, signal in history:
            if t < t_start or t > t_end:
                continue
            pos = int((t - t_start) / duration * (width - 1))
            pos = max(0, min(width - 1, pos))

            if signal != prev_signal and prev_signal != Signal.UNDEFINED:
                # Draw transition
                transition = self._transition_char(prev_signal, signal)
                if pos < width:
                    chars[pos] = transition
            prev_signal = signal
            prev_pos = pos

        return f"{name:>16} {''.join(chars)}"

    def _signal_char(self, signal: Signal) -> str:
        """Get the character representation of a signal."""
        if signal == Signal.HIGH:
            return '█'
        elif signal == Signal.LOW:
            return '▁'
        elif signal == Signal.HIGH_IMPEDANCE:
            return 'z'
        else:
            return '?'

    def _transition_char(self, from_sig: Signal, to_sig: Signal) -> str:
        """Get the character for a transition."""
        if from_sig == Signal.LOW and to_sig == Signal.HIGH:
            return '╱'
        elif from_sig == Signal.HIGH and to_sig == Signal.LOW:
            return '╲'
        else:
            return '│'

    def export_vcd(self, filename: str) -> None:
        """
        Export traces in VCD (Value Change Dump) format.
        Compatible with GTKWave and other waveform viewers.
        """
        lines = []
        lines.append("$date June 2026 $end")
        lines.append("$version circuit-simulator 1.0 $end")
        lines.append("$timescale 1ns $end")
        lines.append("$scope module circuit $end")

        # Assign VCD symbols
        var_map = {}
        for i, name in enumerate(self._traces):
            symbol = chr(ord('!') + i) if i < 94 else f"v{i}"
            var_map[name] = symbol
            lines.append(f"$var wire 1 {symbol} {name} $end")

        lines.append("$upscope $end")
        lines.append("$enddefinitions $end")
        lines.append("$dumpvars")

        # Initial values
        for name, history in self._traces.items():
            if history:
                initial = history[0][1]
                val = '1' if initial == Signal.HIGH else '0' if initial == Signal.LOW else 'x'
                lines.append(f"{val}{var_map[name]}")
        lines.append("$end")

        # Value changes
        events = []
        for name, history in self._traces.items():
            for time_ns, signal in history:
                val = '1' if signal == Signal.HIGH else '0' if signal == Signal.LOW else 'z' if signal == Signal.HIGH_IMPEDANCE else 'x'
                events.append((time_ns, val, var_map[name]))
        
        events.sort(key=lambda e: e[0])

        current_time = None
        for time_ns, val, symbol in events:
            if time_ns != current_time:
                current_time = time_ns
                lines.append(f"#{time_ns}")
            lines.append(f"{val}{symbol}")

        with open(filename, 'w') as f:
            f.write('\n'.join(lines) + '\n')

    def to_dict(self) -> Dict[str, List[Tuple[int, str]]]:
        """Export traces as a dictionary of name -> [(time, signal_name), ...]."""
        result = {}
        for name, history in self._traces.items():
            result[name] = [(t, s.name) for t, s in history]
        return result