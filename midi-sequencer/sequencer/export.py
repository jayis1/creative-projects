"""MIDI file export for rendered songs."""

from __future__ import annotations
from typing import List, Dict, Optional
from midiutil.MidiFile import MIDIFile
from sequencer.patterns import Song, Track, Pattern


def song_to_midi(song: Song, filename: str, add_metronome: bool = False) -> str:
    """Export a Song object to a MIDI file.

    Args:
        song: The Song to export
        filename: Output filename (should end in .mid)
        add_metronome: Add a click track on channel 9

    Returns:
        The filename written
    """
    num_tracks = len(song.tracks) + (1 if add_metronome else 0)
    mf = MIDIFile(numTracks=num_tracks, removeDuplicates=True, deinterleave=False)

    time_offset = 0  # In beats
    ticks_per_step = song.ticks_per_step()
    steps_per_beat = song.steps_per_beat()

    for track_idx, track in enumerate(song.tracks):
        mf.addTrackName(track_idx, time_offset, track.name)
        mf.addTempo(track_idx, time_offset, song.bpm)
        mf.addProgramChange(track_idx, track.channel, time_offset, track.program)

        # Volume controller (CC7)
        mf.addControllerEvent(track_idx, track.channel, time_offset, 7, track.volume)
        # Pan controller (CC10)
        mf.addControllerEvent(track_idx, track.channel, time_offset, 10, track.pan)

        events = track.render_notes()
        for event in events:
            note = event["note"]
            velocity = max(1, min(127, event["velocity"]))
            start_beat = time_offset + event["start_step"] / steps_per_beat
            duration_beats = event["duration_steps"] / steps_per_beat

            # Apply timing offset (humanize)
            timing_offset_beats = event.get("timing_offset", 0) / song.ppqn
            start_beat += timing_offset_beats

            # Ensure duration is at least a small value
            duration_beats = max(0.05, duration_beats)

            # Clamp note to valid MIDI range
            note = max(0, min(127, note))

            mf.addNote(
                track_idx,
                event["channel"],
                note,
                start_beat,
                duration_beats,
                velocity,
            )

    if add_metronome:
        met_track = len(song.tracks)
        mf.addTrackName(met_track, time_offset, "Metronome")
        mf.addTempo(met_track, time_offset, song.bpm)
        mf.addProgramChange(met_track, 9, time_offset, 0)  # Channel 10 = drums

        total_steps = song.total_steps()
        for i in range(total_steps):
            if i % steps_per_beat == 0:
                # Downbeat — high click
                mf.addNote(met_track, 9, 76, time_offset + i / steps_per_beat, 0.1, 100)
            elif i % (steps_per_beat // 2) == 0:
                # Offbeat — low click
                mf.addNote(met_track, 9, 77, time_offset + i / steps_per_beat, 0.1, 70)

    # Apply swing if set
    if song.swing > 0:
        _apply_swing(mf, song, num_tracks)

    with open(filename, "wb") as f:
        mf.writeFile(f)

    return filename


def _apply_swing(mf: MIDIFile, song: Song, num_tracks: int) -> None:
    """Apply swing timing by shifting offbeat notes.

    This modifies the MIDIFile in-place by shifting notes on even 16th positions
    slightly later.
    """
    # Swing is applied by delaying every other 16th note
    # This is a simplification — in practice you'd need to modify the raw MIDI events
    # For now, swing is handled during rendering via the step timing
    pass


def pattern_to_midi(
    pattern: Pattern,
    filename: str,
    bpm: int = 120,
    channel: int = 0,
    program: int = 0,
) -> str:
    """Convenience function to export a single Pattern to MIDI."""
    track = Track(
        name=pattern.name,
        pattern=pattern,
        channel=channel,
        program=program,
    )
    song = Song(name=pattern.name, tracks=[track], bpm=bpm)
    return song_to_midi(song, filename)