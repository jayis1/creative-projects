"""
MIDI file export.

Generates standard MIDI files (Format 0) from composition data.
Supports note events with velocity, channel assignment, and tempo.
"""

import struct
from typing import List, Optional, Tuple


class MidiEvent:
    """A single MIDI event."""

    def __init__(self, delta_time: int, event_type: int, data: bytes):
        self.delta_time = delta_time
        self.event_type = event_type
        self.data = data

    def __repr__(self):
        return f"MidiEvent(delta={self.delta_time}, type=0x{self.event_type:02X}, data={self.data.hex()})"


class MidiTrack:
    """A track of MIDI events."""

    def __init__(self):
        self.events: List[MidiEvent] = []

    def add_note_on(self, delta_time: int, channel: int, note: int, velocity: int = 64):
        """Add a Note On event."""
        self.events.append(MidiEvent(
            delta_time, 0x90 | (channel & 0x0F),
            struct.pack('BB', note & 0x7F, velocity & 0x7F)
        ))

    def add_note_off(self, delta_time: int, channel: int, note: int, velocity: int = 0):
        """Add a Note Off event."""
        self.events.append(MidiEvent(
            delta_time, 0x80 | (channel & 0x0F),
            struct.pack('BB', note & 0x7F, velocity & 0x7F)
        ))

    def add_program_change(self, delta_time: int, channel: int, program: int):
        """Add a Program Change event."""
        self.events.append(MidiEvent(
            delta_time, 0xC0 | (channel & 0x0F),
            struct.pack('B', program & 0x7F)
        ))

    def add_control_change(self, delta_time: int, channel: int, controller: int, value: int):
        """Add a Control Change event."""
        self.events.append(MidiEvent(
            delta_time, 0xB0 | (channel & 0x0F),
            struct.pack('BB', controller & 0x7F, value & 0x7F)
        ))

    def add_meta_tempo(self, delta_time: int, microseconds_per_beat: int):
        """Add a Set Tempo meta event."""
        # Tempo meta event: FF 51 03 tt tt tt
        data = struct.pack('BBB',
                          (microseconds_per_beat >> 16) & 0xFF,
                          (microseconds_per_beat >> 8) & 0xFF,
                          microseconds_per_beat & 0xFF)
        self.events.append(MidiEvent(delta_time, 0xFF, b'\x51\x03' + data))

    def add_meta_end_of_track(self, delta_time: int = 0):
        """Add an End of Track meta event."""
        self.events.append(MidiEvent(delta_time, 0xFF, b'\x2F\x00'))

    def to_bytes(self) -> bytes:
        """Convert track to MIDI byte data."""
        data = bytearray()
        for event in self.events:
            # Variable-length delta time
            data.extend(_encode_varlen(event.delta_time))
            # Event type byte
            data.append(event.event_type)
            # Event data
            data.extend(event.data)

        return bytes(data)


def _encode_varlen(value: int) -> bytes:
    """Encode an integer as a MIDI variable-length quantity."""
    if value < 0:
        raise ValueError(f"Variable-length value must be >= 0, got {value}")

    result = bytearray()
    result.append(value & 0x7F)
    value >>= 7
    while value > 0:
        result.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(result)


class MidiWriter:
    """
    Write MIDI files (Format 0 — single track).

    Provides a high-level API for adding notes by name/frequency
    and automatically generates Note On/Off events with proper timing.

    Args:
        tempo_bpm: Tempo in beats per minute (default 120).
        ticks_per_quarter: MIDI ticks per quarter note (default 480).
        channel: MIDI channel (0-15, default 0).
        program: MIDI program (instrument) number (0-127, default 0).
    """

    def __init__(
        self,
        tempo_bpm: int = 120,
        ticks_per_quarter: int = 480,
        channel: int = 0,
        program: int = 0,
    ):
        if not (1 <= tempo_bpm <= 300):
            raise ValueError(f"Tempo must be 1-300 BPM, got {tempo_bpm}")
        if not (0 <= channel <= 15):
            raise ValueError(f"Channel must be 0-15, got {channel}")
        if not (0 <= program <= 127):
            raise ValueError(f"Program must be 0-127, got {program}")

        self.tempo_bpm = tempo_bpm
        self.ticks_per_quarter = ticks_per_quarter
        self.channel = channel
        self.program = program
        self.track = MidiTrack()
        self._current_tick = 0

        # Set tempo
        microseconds_per_beat = int(60_000_000 / tempo_bpm)
        self.track.add_meta_tempo(0, microseconds_per_beat)

        # Set program
        self.track.add_program_change(0, channel, program)

    def add_note(self, midi_note: int, duration_beats: float = 1.0, velocity: int = 64):
        """
        Add a note by MIDI note number.

        Args:
            midi_note: MIDI note number (0-127, 60 = C4).
            duration_beats: Duration in beats (1.0 = quarter note).
            velocity: Note velocity (1-127).
        """
        if not (0 <= midi_note <= 127):
            raise ValueError(f"MIDI note must be 0-127, got {midi_note}")
        if not (1 <= velocity <= 127):
            raise ValueError(f"Velocity must be 1-127, got {velocity}")

        duration_ticks = int(duration_beats * self.ticks_per_quarter)

        self.track.add_note_on(0, self.channel, midi_note, velocity)
        self.track.add_note_off(duration_ticks, self.channel, midi_note, velocity)

    def add_note_by_name(self, note_name: str, duration_beats: float = 1.0, velocity: int = 64):
        """
        Add a note by name (e.g. 'C4', 'F#5', 'Bb3').

        Args:
            note_name: Note name with octave.
            duration_beats: Duration in beats.
            velocity: Note velocity.
        """
        from .notes import note_to_midi
        midi_note = note_to_midi(note_name)
        self.add_note(midi_note, duration_beats, velocity)

    def add_rest(self, duration_beats: float = 1.0):
        """Add a rest (silence) for the given duration in beats."""
        # Just advance the current time; no events needed
        # We track this implicitly by adding a delta
        rest_ticks = int(duration_beats * self.ticks_per_quarter)
        # Add a silent meta event just to advance time
        self._current_tick += rest_ticks

    def write(self, filepath: str):
        """
        Write the MIDI file.

        Args:
            filepath: Output file path (should end in .mid or .midi).
        """
        # Add end-of-track
        self.track.add_meta_end_of_track()

        track_data = self.track.to_bytes()

        # MIDI file header: MThd
        header = struct.pack('>4sHHH',
                            b'MThd',
                            0,       # Format 0
                            1,       # 1 track
                            self.ticks_per_quarter)

        # Track chunk: MTrk + length + data
        track_chunk = b'MTrk' + struct.pack('>I', len(track_data)) + track_data

        with open(filepath, 'wb') as f:
            f.write(header)
            f.write(track_chunk)

    def write_from_composition(self, composition, filepath: str):
        """
        Convert a Composition object to MIDI and write it.

        Args:
            composition: A Composition object from the composition module.
            filepath: Output file path.
        """
        from .notes import note_to_midi

        for track in composition.tracks:
            current_tick = 0
            for note in track.notes:
                if note.frequency is not None:
                    # Calculate MIDI note from frequency
                    freq = note.frequency
                    import math
                    from .notes import A4_FREQ, A4_MIDI
                    midi_note = int(round(12 * math.log2(freq / A4_FREQ) + A4_MIDI))
                    midi_note = max(0, min(127, midi_note))

                    duration_beats = note.duration * (self.tempo_bpm / 60.0)
                    velocity = int(note.velocity * 127)

                    self.track.add_note_on(current_tick - self._current_tick, self.channel, midi_note, velocity)
                    self.track.add_note_off(int(duration_beats * self.ticks_per_quarter), self.channel, midi_note, velocity)
                    current_tick += int(duration_beats * self.ticks_per_quarter)
                    self._current_tick = current_tick

        self.write(filepath)


__all__ = ['MidiWriter', 'MidiTrack', 'MidiEvent']