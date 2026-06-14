"""MIDI analysis utilities — inspect, visualize, and analyze songs and patterns.

Provides tools for understanding the musical content of generated songs,
including pattern statistics, note distributions, and ASCII visualizations.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from sequencer.patterns import Song, Track, Pattern, Step


def pattern_stats(pattern: Pattern) -> Dict[str, object]:
    """Compute statistics about a pattern.

    Args:
        pattern: The pattern to analyze

    Returns:
        Dict with keys: active_steps, total_steps, density, note_range,
        velocity_min, velocity_max, velocity_mean, has_ties, has_probability
    """
    active_steps = [s for s in pattern.steps if s.notes]
    velocities = [s.velocity for s in active_steps]
    all_notes = [n for s in active_steps for n in s.notes]

    return {
        "active_steps": len(active_steps),
        "total_steps": pattern.length,
        "density": len(active_steps) / max(1, pattern.length),
        "note_count": len(all_notes),
        "note_range": (min(all_notes), max(all_notes)) if all_notes else (0, 0),
        "note_range_semitones": (max(all_notes) - min(all_notes)) if len(all_notes) >= 2 else 0,
        "velocity_min": min(velocities) if velocities else 0,
        "velocity_max": max(velocities) if velocities else 0,
        "velocity_mean": sum(velocities) / len(velocities) if velocities else 0,
        "has_ties": any(s.tie for s in pattern.steps),
        "has_probability": any(s.probability < 1.0 for s in pattern.steps),
        "polyphonic_steps": sum(1 for s in active_steps if len(s.notes) > 1),
    }


def track_stats(track: Track) -> Dict[str, object]:
    """Compute statistics about a track.

    Args:
        track: The track to analyze

    Returns:
        Dict with pattern stats plus track-level info
    """
    stats = pattern_stats(track.pattern)
    events = track.render_notes()
    stats.update({
        "track_name": track.name,
        "channel": track.channel,
        "program": track.program,
        "muted": track.mute,
        "solo": track.solo,
        "event_count": len(events),
        "octave_shift": track.octave_shift,
        "humanize_velocity": track.humanize_velocity,
        "humanize_timing": track.humanize_timing,
    })
    return stats


def song_stats(song: Song) -> Dict[str, object]:
    """Compute statistics about a song.

    Args:
        song: The song to analyze

    Returns:
        Dict with song-level and per-track statistics
    """
    track_analyses = []
    total_events = 0
    all_notes = []

    for track in song.tracks:
        ts = track_stats(track)
        track_analyses.append(ts)
        total_events += ts["event_count"]
        if isinstance(ts["note_range"], tuple) and ts["note_range"][0] != ts["note_range"][1]:
            all_notes.extend(track.pattern.steps[i].notes
                           for i in range(len(track.pattern.steps))
                           if track.pattern.steps[i].notes)

    return {
        "song_name": song.name,
        "bpm": song.bpm,
        "ppqn": song.ppqn,
        "time_signature": song.time_signature,
        "total_tracks": len(song.tracks),
        "total_steps": song.total_steps(),
        "total_events": total_events,
        "duration_beats": song.total_steps() / song.steps_per_beat(),
        "duration_seconds": (song.total_steps() / song.steps_per_beat()) * (60.0 / song.bpm),
        "tracks": track_analyses,
    }


def visualize_pattern(pattern: Pattern, width: int = 64, style: str = "block") -> str:
    """Create an ASCII visualization of a pattern.

    Args:
        pattern: The pattern to visualize
        width: Maximum width in characters
        style: Visualization style ('block', 'dot', 'piano')

    Returns:
        Multi-line ASCII visualization string
    """
    if style == "block":
        return _visualize_block(pattern, width)
    elif style == "dot":
        return _visualize_dot(pattern, width)
    elif style == "piano":
        return _visualize_piano(pattern, width)
    else:
        return _visualize_block(pattern, width)


def _visualize_block(pattern: Pattern, width: int) -> str:
    """Block-style visualization: each step shown as a filled/empty block."""
    lines = []
    header = f"Pattern: {pattern.name} ({pattern.length} steps)"
    lines.append(header)
    lines.append("─" * min(pattern.length * 2 + 4, width + 4))

    # Single-line compact view
    chars = []
    for step in pattern.steps:
        if not step.notes:
            chars.append("·")
        elif step.velocity > 100:
            chars.append("█")
        elif step.velocity > 60:
            chars.append("▓")
        else:
            chars.append("░")
    lines.append("│" + " ".join(chars) + "│")

    # Velocity bar
    vel_chars = []
    for step in pattern.steps:
        if not step.notes:
            vel_chars.append(" ")
        else:
            v = step.velocity
            if v > 110:
                vel_chars.append("↑")
            elif v > 80:
                vel_chars.append("─")
            elif v > 40:
                vel_chars.append("↓")
            else:
                vel_chars.append("_")
    lines.append("│" + " ".join(vel_chars) + "│  velocity")

    # Tie indicator
    tie_chars = []
    for step in pattern.steps:
        tie_chars.append("~" if step.tie else " ")
    lines.append("│" + " ".join(tie_chars) + "│  ties")

    # Step numbers (every 4th step)
    step_nums = []
    for i in range(pattern.length):
        if i % 4 == 0:
            step_nums.append(f"{i:2d}")
        else:
            step_nums.append("  ")
    lines.append(" " + " ".join(step_nums) + "   step#")

    return "\n".join(lines)


def _visualize_dot(pattern: Pattern, width: int) -> str:
    """Dot-style compact visualization."""
    vis = "".join("●" if s.notes else "○" for s in pattern.steps)
    return f"Pattern '{pattern.name}' [{vis}]"


def _visualize_piano(pattern: Pattern, width: int) -> str:
    """Piano-roll style visualization."""
    if not pattern.steps:
        return f"Pattern '{pattern.name}' (empty)"

    # Determine note range
    all_notes = [n for s in pattern.steps for n in s.notes]
    if not all_notes:
        return f"Pattern '{pattern.name}' (no notes)"

    min_note = min(all_notes)
    max_note = max(all_notes)
    note_range = max_note - min_note + 1

    lines = []
    lines.append(f"Pattern: {pattern.name}  Note range: {min_note}-{max_note}")

    # Build a grid
    num_steps = pattern.length
    grid = {}
    for i, step in enumerate(pattern.steps):
        for note in step.notes:
            grid[(note, i)] = step.velocity

    # Display (top = high notes, bottom = low notes)
    display_range = min(note_range, 24)  # Limit display height
    step_display = min(num_steps, width)

    for row_note in range(max_note, max(max_note - display_range, min_note - 1), -1):
        row = f"{row_note:3d}│"
        for col in range(step_display):
            vel = grid.get((row_note, col))
            if vel is None:
                row += "·"
            elif vel > 100:
                row += "█"
            elif vel > 60:
                row += "▓"
            else:
                row += "░"
        row += f"│"
        lines.append(row)

    # Bottom border with step markers
    bottom = "   └" + "─" * step_display + "┘"
    lines.append(bottom)

    return "\n".join(lines)


def song_summary(song: Song) -> str:
    """Generate a human-readable summary of a song.

    Args:
        song: The song to summarize

    Returns:
        Multi-line summary string
    """
    stats = song_stats(song)
    lines = []
    lines.append(f"╔══════════════════════════════════════════╗")
    lines.append(f"║  Song: {song.name:<33s}║")
    lines.append(f"║  BPM: {song.bpm}  Time: {song.time_signature[0]}/{song.time_signature[1]}  "
                 f"PPQN: {song.ppqn:<9d}║")
    lines.append(f"║  Tracks: {len(song.tracks):<3d}  Steps: {song.total_steps():<4d}  "
                 f"Duration: {stats['duration_seconds']:.1f}s    ║")
    lines.append(f"╠══════════════════════════════════════════╣")

    for track in song.tracks:
        ts = track_stats(track)
        density = ts["density"]
        # Density bar
        bar_len = 20
        filled = int(density * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(
            f"║  {track.name:<12s} ch={ts['channel']:2d} "
            f"prog={ts['program']:3d} [{bar}] {density:.0%}  ║"
        )

    lines.append(f"╚══════════════════════════════════════════╝")
    return "\n".join(lines)


def note_distribution(pattern: Pattern) -> Dict[int, int]:
    """Count how often each note appears in a pattern.

    Args:
        pattern: The pattern to analyze

    Returns:
        Dict mapping MIDI note number to occurrence count
    """
    counts: Dict[int, int] = {}
    for step in pattern.steps:
        for note in step.notes:
            counts[note] = counts.get(note, 0) + 1
    return dict(sorted(counts.items()))


def interval_distribution(pattern: Pattern) -> Dict[int, int]:
    """Analyze melodic intervals between consecutive notes in a pattern.

    Args:
        pattern: The pattern to analyze

    Returns:
        Dict mapping interval (semitones) to occurrence count
    """
    intervals: Dict[int, int] = {}
    prev_note = None
    for step in pattern.steps:
        if step.notes and len(step.notes) == 1:
            note = step.notes[0]
            if prev_note is not None:
                interval = note - prev_note
                intervals[interval] = intervals.get(interval, 0) + 1
            prev_note = note
    return dict(sorted(intervals.items()))