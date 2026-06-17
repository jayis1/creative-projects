"""Tests for the MIDI module."""

import os
import tempfile
import pytest

from waveform_synth.midi import MidiWriter, MidiTrack, MidiEvent, _encode_varlen


class TestMidiWriter:
    def test_encode_varlen_small(self):
        """Small values should encode as single byte."""
        result = _encode_varlen(0)
        assert result == b'\x00'
        result = _encode_varlen(127)
        assert result == b'\x7f'

    def test_encode_varlen_large(self):
        """Large values should use multiple bytes."""
        result = _encode_varlen(128)
        assert result == b'\x81\x00'
        result = _encode_varlen(480)  # 480 ticks = 1 beat at 480 tpq
        assert len(result) == 2

    def test_encode_varlen_zero(self):
        """Zero should encode as single byte."""
        assert _encode_varlen(0) == b'\x00'

    def test_encode_varlen_negative(self):
        """Negative values should raise ValueError."""
        with pytest.raises(ValueError):
            _encode_varlen(-1)

    def test_add_note(self):
        """Adding a note should work."""
        midi = MidiWriter(tempo_bpm=120)
        midi.add_note(60, duration_beats=1.0, velocity=100)
        # Should have tempo meta-event, program change, note on, note off
        assert len(midi.track.events) >= 4

    def test_add_note_by_name(self):
        """Adding a note by name should work."""
        midi = MidiWriter()
        midi.add_note_by_name('C4', duration_beats=1.0)
        assert len(midi.track.events) >= 3

    def test_add_note_invalid_midi(self):
        """Invalid MIDI note should raise ValueError."""
        midi = MidiWriter()
        with pytest.raises(ValueError):
            midi.add_note(128)  # MIDI notes are 0-127
        with pytest.raises(ValueError):
            midi.add_note(-1)

    def test_add_note_invalid_velocity(self):
        """Invalid velocity should raise ValueError."""
        midi = MidiWriter()
        with pytest.raises(ValueError):
            midi.add_note(60, velocity=0)
        with pytest.raises(ValueError):
            midi.add_note(60, velocity=200)

    def test_write_midi_file(self):
        """Should write a valid MIDI file."""
        midi = MidiWriter(tempo_bpm=120, channel=0, program=0)
        midi.add_note_by_name('C4', duration_beats=1.0)
        midi.add_note_by_name('E4', duration_beats=1.0)
        midi.add_note_by_name('G4', duration_beats=1.0)

        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name

        try:
            midi.write(filepath)
            assert os.path.exists(filepath)
            # MIDI file should be at least 50 bytes (header + track data)
            assert os.path.getsize(filepath) > 50
        finally:
            os.unlink(filepath)

    def test_tempo_bpm_validation(self):
        """Invalid tempo should raise ValueError."""
        with pytest.raises(ValueError):
            MidiWriter(tempo_bpm=0)
        with pytest.raises(ValueError):
            MidiWriter(tempo_bpm=500)

    def test_channel_validation(self):
        """Invalid channel should raise ValueError."""
        with pytest.raises(ValueError):
            MidiWriter(channel=-1)
        with pytest.raises(ValueError):
            MidiWriter(channel=16)

    def test_program_validation(self):
        """Invalid program should raise ValueError."""
        with pytest.raises(ValueError):
            MidiWriter(program=-1)
        with pytest.raises(ValueError):
            MidiWriter(program=128)

    def test_c_major_scale_midi(self):
        """Should write a C major scale."""
        midi = MidiWriter(tempo_bpm=100)
        for note in ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']:
            midi.add_note_by_name(note, duration_beats=0.5)

        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name

        try:
            midi.write(filepath)
            assert os.path.exists(filepath)
            size = os.path.getsize(filepath)
            assert size > 100  # Should have meaningful content
        finally:
            os.unlink(filepath)


class TestMidiTrack:
    def test_add_note_on(self):
        """NoteOn event should be added correctly."""
        track = MidiTrack()
        track.add_note_on(0, channel=0, note=60, velocity=100)
        assert len(track.events) == 1

    def test_add_note_off(self):
        """NoteOff event should be added correctly."""
        track = MidiTrack()
        track.add_note_off(480, channel=0, note=60)
        assert len(track.events) == 1

    def test_to_bytes(self):
        """Track should serialize to bytes."""
        track = MidiTrack()
        track.add_note_on(0, channel=0, note=60, velocity=100)
        track.add_note_off(480, channel=0, note=60)
        data = track.to_bytes()
        assert len(data) > 0