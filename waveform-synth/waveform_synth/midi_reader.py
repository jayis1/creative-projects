"""
MIDI file import (Standard MIDI File reader).

Parses Standard MIDI Files (SMF) Format 0 and Format 1, extracting
note events, tempo, time signature, and program changes.

The reader produces a sequence of :class:`MidiNote` objects with timing
in seconds, making it easy to feed into the composition engine or
analysis tools.
"""

import struct
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import IntEnum


class MidiMessageType(IntEnum):
    """MIDI message type codes."""
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLY_PRESSURE = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_PRESSURE = 0xD0
    PITCH_BEND = 0xE0
    META = 0xFF
    SYSEX = 0xF0
    ESCAPE = 0xF7


@dataclass
class MidiNote:
    """A single MIDI note event with timing in seconds."""
    midi_note: int
    start_time: float  # seconds
    duration: float    # seconds
    velocity: int
    channel: int

    @property
    def frequency(self) -> float:
        """Frequency in Hz."""
        return 440.0 * (2.0 ** ((self.midi_note - 69) / 12.0))

    @property
    def note_name(self) -> str:
        """Note name with octave (e.g. 'C4', 'A#3')."""
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (self.midi_note // 12) - 1
        return f"{names[self.midi_note % 12]}{octave}"

    def __repr__(self):
        return (f"MidiNote({self.note_name}, t={self.start_time:.3f}s, "
                f"dur={self.duration:.3f}s, vel={self.velocity}, ch={self.channel})")


@dataclass
class TempoEvent:
    """A tempo change event."""
    time: float  # seconds
    bpm: float


@dataclass
class ProgramChangeEvent:
    """A program (instrument) change event."""
    time: float
    channel: int
    program: int


class MidiFile:
    """
    Parsed MIDI file data.

    Attributes:
        format: MIDI file format (0, 1, or 2).
        num_tracks: Number of tracks.
        division: Ticks per quarter note (PPQ) or SMPTE frames.
        notes: All note events sorted by start time.
        tempo_events: Tempo change events.
        program_events: Program change events.
        duration: Total duration in seconds.
    """

    def __init__(self):
        self.format: int = 0
        self.num_tracks: int = 0
        self.division: int = 480  # PPQ (pulses per quarter note)
        self.notes: List[MidiNote] = []
        self.tempo_events: List[TempoEvent] = []
        self.program_events: List[ProgramChangeEvent] = []
        self.duration: float = 0.0

    def get_notes_in_range(self, start: float = 0.0, end: Optional[float] = None) -> List[MidiNote]:
        """Get notes within a time range."""
        if end is None:
            end = self.duration
        return [n for n in self.notes if n.start_time >= start and n.start_time < end]

    def get_notes_on_channel(self, channel: int) -> List[MidiNote]:
        """Get all notes on a specific MIDI channel."""
        return [n for n in self.notes if n.channel == channel]

    def to_frequencies(self) -> List[Tuple[float, float, float]]:
        """Return (start_time, frequency, duration) tuples for all notes."""
        return [(n.start_time, n.frequency, n.duration) for n in self.notes]

    def __repr__(self):
        return (f"MidiFile(format={self.format}, tracks={self.num_tracks}, "
                f"notes={len(self.notes)}, duration={self.duration:.2f}s)")


def _read_varlen(data: bytes, offset: int) -> Tuple[int, int]:
    """
    Read a MIDI variable-length quantity.

    Args:
        data: Byte data.
        offset: Starting offset.

    Returns:
        Tuple of (value, new_offset).
    """
    value = 0
    while True:
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            break
    return value, offset


def _ticks_to_seconds(ticks: int, tempo_map: List[Tuple[int, int, float]],
                      division: int) -> float:
    """
    Convert MIDI ticks to seconds using a tempo map.

    Args:
        ticks: Tick position.
        tempo_map: List of (tick_position, microseconds_per_beat, seconds_at_position).
        division: Ticks per quarter note.

    Returns:
        Time in seconds.
    """
    if not tempo_map:
        # Default tempo: 120 BPM = 500000 microseconds per beat
        return ticks * 500000 / (division * 1_000_000)

    seconds = 0.0
    last_tick = 0
    last_tempo = 500000  # default

    for map_tick, tempo, map_seconds in tempo_map:
        if map_tick <= ticks:
            seconds = map_seconds
            last_tick = map_tick
            last_tempo = tempo
        else:
            break

    # Add time from last tempo change to target tick
    delta_ticks = ticks - last_tick
    seconds += delta_ticks * last_tempo / (division * 1_000_000)
    return seconds


def read_midi_file(filepath: str) -> MidiFile:
    """
    Read and parse a Standard MIDI File.

    Supports Format 0 (single track) and Format 1 (multiple tracks).

    Args:
        filepath: Path to the .mid or .midi file.

    Returns:
        MidiFile object with parsed note and tempo data.

    Raises:
        ValueError: If the file is not a valid MIDI file.
        FileNotFoundError: If the file doesn't exist.
    """
    with open(filepath, 'rb') as f:
        data = f.read()

    result = MidiFile()
    offset = 0

    # Read header
    if data[:4] != b'MThd':
        raise ValueError(f"Not a MIDI file: expected 'MThd', got {data[:4]}")

    offset = 4
    header_size = struct.unpack('>I', data[offset:offset + 4])[0]
    offset += 4

    fmt = struct.unpack('>H', data[offset:offset + 2])[0]
    ntracks = struct.unpack('>H', data[offset + 2:offset + 4])[0]
    division = struct.unpack('>H', data[offset + 4:offset + 6])[0]

    result.format = fmt
    result.num_tracks = ntracks
    result.division = division

    offset += header_size

    # Tempo map: list of (tick, microseconds_per_beat, seconds_at_tick)
    tempo_map: List[Tuple[int, int, float]] = []
    current_tempo = 500000  # default 120 BPM

    # Process each track
    all_note_events: List[dict] = []

    for track_idx in range(ntracks):
        if offset >= len(data):
            break

        # Track header
        if data[offset:offset + 4] != b'MTrk':
            # Skip unknown chunk
            chunk_size = struct.unpack('>I', data[offset + 4:offset + 8])[0]
            offset += 8 + chunk_size
            continue

        offset += 4
        track_size = struct.unpack('>I', data[offset:offset + 4])[0]
        offset += 4
        track_end = offset + track_size

        tick = 0
        running_status = 0  # For running status
        pending_notes: Dict[Tuple[int, int], int] = {}  # (channel, note) -> start_tick

        while offset < track_end:
            # Read delta time
            delta, offset = _read_varlen(data, offset)
            tick += delta

            # Read status byte
            status = data[offset]
            if status < 0x80:
                # Running status: use previous status byte
                status = running_status
            else:
                offset += 1
                running_status = status

            msg_type = status & 0xF0
            channel = status & 0x0F

            if msg_type == MidiMessageType.NOTE_OFF:
                note = data[offset]
                velocity = data[offset + 1]
                offset += 2
                key = (channel, note)
                if key in pending_notes:
                    start_tick = pending_notes.pop(key)
                    dur_ticks = tick - start_tick
                    all_note_events.append({
                        'midi_note': note,
                        'start_tick': start_tick,
                        'dur_ticks': dur_ticks,
                        'velocity': velocity,
                        'channel': channel,
                    })

            elif msg_type == MidiMessageType.NOTE_ON:
                note = data[offset]
                velocity = data[offset + 1]
                offset += 2
                if velocity == 0:
                    # Note on with velocity 0 = note off
                    key = (channel, note)
                    if key in pending_notes:
                        start_tick = pending_notes.pop(key)
                        dur_ticks = tick - start_tick
                        all_note_events.append({
                            'midi_note': note,
                            'start_tick': start_tick,
                            'dur_ticks': dur_ticks,
                            'velocity': velocity,
                            'channel': channel,
                        })
                else:
                    pending_notes[(channel, note)] = tick

            elif msg_type == MidiMessageType.POLY_PRESSURE:
                offset += 2  # note, pressure

            elif msg_type == MidiMessageType.CONTROL_CHANGE:
                offset += 2  # controller, value

            elif msg_type == MidiMessageType.PROGRAM_CHANGE:
                program = data[offset]
                offset += 1
                result.program_events.append(ProgramChangeEvent(
                    time=0.0,  # filled in later
                    channel=channel,
                    program=program,
                ))

            elif msg_type == MidiMessageType.CHANNEL_PRESSURE:
                offset += 1

            elif msg_type == MidiMessageType.PITCH_BEND:
                offset += 2

            elif status == 0xFF:
                # Meta event
                meta_type = data[offset]
                offset += 1
                length, offset = _read_varlen(data, offset)
                meta_data = data[offset:offset + length]
                offset += length

                if meta_type == 0x51:  # Set Tempo
                    if len(meta_data) >= 3:
                        tempo = (meta_data[0] << 16) | (meta_data[1] << 8) | meta_data[2]
                        current_tempo = tempo
                        # Add to tempo map (seconds will be computed later)
                        tempo_map.append((tick, tempo, 0.0))

                elif meta_type == 0x2F:  # End of Track
                    break

            elif status == 0xF0 or status == 0xF7:
                # SysEx
                length, offset = _read_varlen(data, offset)
                offset += length

            else:
                # Unknown — skip one byte to avoid infinite loop
                offset += 1

        # Move to next track
        offset = track_end

    # Build tempo map with seconds
    tempo_map.sort(key=lambda x: x[0])
    prev_tick = 0
    prev_seconds = 0.0
    prev_tempo = 500000
    computed_tempo_map = []
    for t in tempo_map:
        tick, tempo, _ = t
        delta = tick - prev_tick
        seconds = prev_seconds + delta * prev_tempo / (division * 1_000_000)
        computed_tempo_map.append((tick, tempo, seconds))
        prev_tick = tick
        prev_seconds = seconds
        prev_tempo = tempo

    # Convert note events to seconds
    for event in all_note_events:
        start_time = _ticks_to_seconds(event['start_tick'], computed_tempo_map, division)
        dur_seconds = _ticks_to_seconds(event['dur_ticks'], computed_tempo_map, division)
        result.notes.append(MidiNote(
            midi_note=event['midi_note'],
            start_time=start_time,
            duration=dur_seconds,
            velocity=event['velocity'],
            channel=event['channel'],
        ))

    # Fill in program change times (use tempo map)
    for pc in result.program_events:
        # Simplified: all at start (proper impl would track tick per event)
        pc.time = 0.0

    # Fill in tempo event times
    for tick, tempo, seconds in computed_tempo_map:
        result.tempo_events.append(TempoEvent(time=seconds, bpm=60_000_000 / tempo))

    # Sort notes by start time
    result.notes.sort(key=lambda n: n.start_time)

    # Calculate total duration
    if result.notes:
        result.duration = max(n.start_time + n.duration for n in result.notes)
    elif computed_tempo_map:
        result.duration = computed_tempo_map[-1][2]

    return result


__all__ = ['read_midi_file', 'MidiFile', 'MidiNote', 'TempoEvent', 'ProgramChangeEvent', 'MidiMessageType']