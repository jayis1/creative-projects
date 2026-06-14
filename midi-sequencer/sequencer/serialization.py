"""Serialization: save and load songs/patterns to/from JSON."""

from __future__ import annotations
import json
from typing import Dict, Any, Optional
from sequencer.patterns import Song, Track, Pattern, Step


def step_to_dict(step: Step) -> Dict[str, Any]:
    """Convert a Step to a JSON-serializable dict."""
    return {
        "notes": step.notes,
        "velocity": step.velocity,
        "gate": step.gate,
        "probability": step.probability,
        "tie": step.tie,
    }


def dict_to_step(d: Dict[str, Any]) -> Step:
    """Create a Step from a dict."""
    return Step(
        notes=d.get("notes", []),
        velocity=d.get("velocity", 100),
        gate=d.get("gate", 0.8),
        probability=d.get("probability", 1.0),
        tie=d.get("tie", False),
    )


def pattern_to_dict(pattern: Pattern) -> Dict[str, Any]:
    """Convert a Pattern to a JSON-serializable dict."""
    return {
        "name": pattern.name,
        "length": pattern.length,
        "steps": [step_to_dict(s) for s in pattern.steps],
    }


def dict_to_pattern(d: Dict[str, Any]) -> Pattern:
    """Create a Pattern from a dict."""
    steps = [dict_to_step(s) for s in d.get("steps", [])]
    return Pattern(
        name=d.get("name", "untitled"),
        steps=steps,
        length=d.get("length", len(steps)),
    )


def track_to_dict(track: Track) -> Dict[str, Any]:
    """Convert a Track to a JSON-serializable dict."""
    return {
        "name": track.name,
        "pattern": pattern_to_dict(track.pattern),
        "channel": track.channel,
        "program": track.program,
        "volume": track.volume,
        "pan": track.pan,
        "mute": track.mute,
        "solo": track.solo,
        "humanize_velocity": track.humanize_velocity,
        "humanize_timing": track.humanize_timing,
        "octave_shift": track.octave_shift,
    }


def dict_to_track(d: Dict[str, Any]) -> Track:
    """Create a Track from a dict."""
    return Track(
        name=d.get("name", "track"),
        pattern=dict_to_pattern(d.get("pattern", {})),
        channel=d.get("channel", 0),
        program=d.get("program", 0),
        volume=d.get("volume", 100),
        pan=d.get("pan", 64),
        mute=d.get("mute", False),
        solo=d.get("solo", False),
        humanize_velocity=d.get("humanize_velocity", 0.0),
        humanize_timing=d.get("humanize_timing", 0.0),
        octave_shift=d.get("octave_shift", 0),
    )


def song_to_dict(song: Song) -> Dict[str, Any]:
    """Convert a Song to a JSON-serializable dict."""
    return {
        "name": song.name,
        "bpm": song.bpm,
        "ppqn": song.ppqn,
        "time_signature": list(song.time_signature),
        "swing": song.swing,
        "tracks": [track_to_dict(t) for t in song.tracks],
    }


def dict_to_song(d: Dict[str, Any]) -> Song:
    """Create a Song from a dict."""
    ts = d.get("time_signature", [4, 4])
    return Song(
        name=d.get("name", "untitled"),
        bpm=d.get("bpm", 120),
        ppqn=d.get("ppqn", 480),
        time_signature=(ts[0], ts[1]) if isinstance(ts, list) else tuple(ts),
        swing=d.get("swing", 0.0),
        tracks=[dict_to_track(t) for t in d.get("tracks", [])],
    )


def save_song(song: Song, filename: str) -> str:
    """Save a Song to a JSON file.

    Args:
        song: The Song to save
        filename: Path to the output JSON file

    Returns:
        The filename written
    """
    data = song_to_dict(song)
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    return filename


def load_song(filename: str) -> Song:
    """Load a Song from a JSON file.

    Args:
        filename: Path to the JSON file

    Returns:
        The loaded Song
    """
    with open(filename, "r") as f:
        data = json.load(f)
    return dict_to_song(data)


def save_pattern(pattern: Pattern, filename: str) -> str:
    """Save a Pattern to a JSON file."""
    data = pattern_to_dict(pattern)
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    return filename


def load_pattern(filename: str) -> Pattern:
    """Load a Pattern from a JSON file."""
    with open(filename, "r") as f:
        data = json.load(f)
    return dict_to_pattern(data)