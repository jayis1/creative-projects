"""Pattern and track definitions for the step sequencer."""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import random
import copy


@dataclass
class Step:
    """A single step in a pattern — can hold one or more notes."""
    notes: List[int] = field(default_factory=list)  # MIDI note numbers
    velocity: int = 100          # 0-127
    gate: float = 0.8            # 0.0-1.0, fraction of step length the note sounds
    probability: float = 1.0     # 0.0-1.0, chance of this step firing
    tie: bool = False            # If True, sustain into next step

    def should_fire(self) -> bool:
        """Determine if this step triggers based on its probability."""
        if self.probability >= 1.0:
            return True
        return random.random() < self.probability

    def active_notes(self) -> List[int]:
        """Return notes if this step fires, else empty list."""
        if self.should_fire() and self.velocity > 0:
            return list(self.notes)
        return []


@dataclass
class Pattern:
    """A sequence of steps forming a rhythmic/melodic pattern."""
    name: str = "untitled"
    steps: List[Step] = field(default_factory=list)
    length: int = 16           # Number of steps (quantized to power of 2 typically)

    def __post_init__(self):
        if len(self.steps) < self.length:
            self.steps.extend([Step() for _ in range(self.length - len(self.steps))])
        self.steps = self.steps[:self.length]

    def get_step(self, index: int) -> Step:
        """Get step at index, wrapping around for patterns shorter than requested."""
        return self.steps[index % self.length]

    def set_step(self, index: int, step: Step) -> None:
        """Set step at index, wrapping around."""
        self.steps[index % self.length] = step

    def rotate(self, amount: int) -> "Pattern":
        """Rotate the pattern by `amount` steps (positive = rightward shift)."""
        amount = amount % self.length
        new_steps = self.steps[-amount:] + self.steps[:-amount] if amount else list(self.steps)
        return Pattern(name=self.name, steps=new_steps, length=self.length)

    def reverse(self) -> "Pattern":
        """Reverse the pattern."""
        return Pattern(name=self.name, steps=list(reversed(self.steps)), length=self.length)

    def invert(self, semitones: int) -> "Pattern":
        """Transpose all notes by semitones."""
        new_steps = []
        for s in copy.deepcopy(self.steps):
            s.notes = [n + semitones for n in s.notes]
            new_steps.append(s)
        return Pattern(name=self.name, steps=new_steps, length=self.length)

    def mask(self, positions: List[int]) -> "Pattern":
        """Create a new pattern where only steps at given positions are kept (others muted)."""
        new_steps = []
        for i, s in enumerate(self.steps):
            if i in positions:
                new_steps.append(copy.deepcopy(s))
            else:
                new_steps.append(Step())
        return Pattern(name=self.name, steps=new_steps, length=self.length)


@dataclass
class Track:
    """A musical track containing a pattern, with instrument/voice settings."""
    name: str = "track"
    pattern: Pattern = field(default_factory=lambda: Pattern())
    channel: int = 0           # MIDI channel (0-15)
    program: int = 0           # GM program number (0-127)
    volume: int = 100          # Track volume (0-127)
    pan: int = 64              # Pan (0=left, 64=center, 127=right)
    mute: bool = False
    solo: bool = False
    humanize_velocity: float = 0.0   # Random velocity deviation amount
    humanize_timing: float = 0.0      # Random timing deviation in ticks
    octave_shift: int = 0              # Shift all notes by this many octaves (12 semitones each)

    def render_notes(self) -> List[Dict]:
        """Render the track's pattern into a list of note events.

        Returns list of dicts with keys: note, velocity, start_step, duration_steps, channel
        """
        if self.mute:
            return []

        events = []
        for i, step in enumerate(self.pattern.steps):
            if not step.should_fire():
                continue

            velocity = step.velocity
            if self.humanize_velocity > 0:
                deviation = int(random.gauss(0, self.humanize_velocity))
                velocity = max(1, min(127, velocity + deviation))

            # Calculate duration (in steps)
            if step.tie:
                # Find how many consecutive ties
                duration = 1
                j = i + 1
                while j < self.pattern.length and self.pattern.steps[j % self.pattern.length].tie:
                    duration += 1
                    j += 1
            else:
                duration = step.gate

            for note_num in step.notes:
                shifted_note = note_num + self.octave_shift * 12
                events.append({
                    "note": shifted_note,
                    "velocity": velocity,
                    "start_step": i,
                    "duration_steps": duration,
                    "channel": self.channel,
                    "timing_offset": random.gauss(0, self.humanize_timing) if self.humanize_timing > 0 else 0,
                })

        return events


@dataclass
class Song:
    """A collection of tracks with song-level settings."""
    name: str = "untitled"
    tracks: List[Track] = field(default_factory=list)
    bpm: int = 120
    ppqn: int = 480           # Pulses per quarter note (MIDI resolution)
    time_signature: Tuple[int, int] = (4, 4)  # beats per bar, beat unit
    swing: float = 0.0        # 0.0 = no swing, up to ~0.3

    def steps_per_beat(self) -> int:
        """Number of sequencer steps per beat."""
        return 4  # 16th note resolution

    def ticks_per_step(self) -> int:
        """Number of MIDI ticks per sequencer step."""
        return self.ppqn // self.steps_per_beat()

    def total_steps(self) -> int:
        """Total number of steps in the song (longest track pattern)."""
        if not self.tracks:
            return 16
        return max(t.pattern.length for t in self.tracks)

    def add_track(self, track: Track) -> None:
        self.tracks.append(track)

    def render(self) -> List[Dict]:
        """Render all tracks into a flat list of note events."""
        all_events = []
        any_solo = any(t.solo for t in self.tracks)

        for track in self.tracks:
            if track.mute:
                continue
            if any_solo and not track.solo:
                continue
            all_events.extend(track.render_notes())

        return sorted(all_events, key=lambda e: e["start_step"])