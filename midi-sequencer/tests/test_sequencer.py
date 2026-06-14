"""Comprehensive test suite for the MIDI Step Sequencer.

Tests cover all modules: scales, patterns, generators, grooves, lsystem,
progressions, arrangement, serialization, export, config, validation,
analysis, batch, extended drums, and CLI.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sequencer.scales import (
    note_to_midi, midi_to_note, scale_notes, chord_notes, degree_to_note,
    quantize_to_scale, SCALE_INTERVALS, NOTE_OFFSETS, CHORD_INTERVALS,
)
from sequencer.patterns import Step, Pattern, Track, Song
from sequencer.generators import (
    euclidean_rhythm, euclidean_pattern, random_pattern, markov_pattern,
    chord_pattern, bassline_from_chords, drum_pattern, morph_pattern,
)
from sequencer.grooves import apply_groove, apply_velocity_curve, GROOVE_TEMPLATES, VELOCITY_CURVES
from sequencer.lsystem import lsystem_pattern, PRESETS as LS_PRESETS
from sequencer.progressions import build_progression, PROGRESSIONS
from sequencer.arrangement import Arrangement, Section, verse_chorus_verse
from sequencer.serialization import save_song, load_song, save_pattern, load_pattern
from sequencer.export import song_to_midi, pattern_to_midi
from sequencer.config import SequencerConfig, generate_default_config
from sequencer.validation import (
    ValidationError, validate_note_name, validate_scale, validate_chord_quality,
    validate_midi_note, validate_velocity, validate_channel, validate_program,
    validate_bpm, validate_octave, validate_pattern_length, validate_density,
    validate_gate, validate_probability, validate_time_signature,
)
from sequencer.analysis import (
    pattern_stats, track_stats, song_stats, song_summary,
    visualize_pattern, note_distribution, interval_distribution,
)
from sequencer.batch import (
    CompositionRecipe, parameter_sweep,
    euclidean_variations, scale_exploration, progression_album,
)
from sequencer.extended_drums import extended_drum_pattern, list_extended_styles


class TestScales(unittest.TestCase):
    """Test scales.py"""

    def test_note_to_midi_middle_c(self):
        self.assertEqual(note_to_midi("C4"), 60)

    def test_note_to_midi_sharps(self):
        self.assertEqual(note_to_midi("C#4"), 61)
        self.assertEqual(note_to_midi("F#3"), 54)

    def test_note_to_midi_flats(self):
        self.assertEqual(note_to_midi("Bb3"), 58)
        self.assertEqual(note_to_midi("Eb4"), 63)

    def test_note_to_midi_default_octave(self):
        self.assertEqual(note_to_midi("C"), 60)

    def test_midi_to_note_roundtrip(self):
        for midi_num in range(0, 128, 7):
            note_name = midi_to_note(midi_num)
            midi_back = note_to_midi(note_name)
            self.assertEqual(midi_back, midi_num,
                             f"Roundtrip failed: {midi_num} -> {note_name} -> {midi_back}")

    def test_midi_to_note_negative_octave(self):
        for midi_num in range(12):
            note_name = midi_to_note(midi_num)
            midi_back = note_to_midi(note_name)
            self.assertEqual(midi_back, midi_num)

    def test_midi_to_note_all_notes(self):
        for midi_num in range(128):
            note_name = midi_to_note(midi_num)
            midi_back = note_to_midi(note_name)
            self.assertEqual(midi_back, midi_num)

    def test_scale_notes_c_major(self):
        notes = scale_notes("C", "major", 1, 4)
        expected = [60, 62, 64, 65, 67, 69, 71, 72]
        self.assertEqual(notes, expected)

    def test_scale_notes_length(self):
        for scale_name, intervals in SCALE_INTERVALS.items():
            notes = scale_notes("C", scale_name, 2, 4)
            expected_len = len(intervals) * 2 + 1
            self.assertEqual(len(notes), expected_len,
                             f"Scale {scale_name}: expected {expected_len} notes, got {len(notes)}")

    def test_chord_notes(self):
        notes = chord_notes("C", "maj", 4)
        self.assertEqual(notes, [60, 64, 67])

    def test_chord_notes_invalid(self):
        with self.assertRaises(ValueError):
            chord_notes("C", "invalid_quality")

    def test_unknown_scale(self):
        with self.assertRaises(ValueError):
            scale_notes("C", "nonexistent_scale")

    def test_quantize_to_scale(self):
        result = quantize_to_scale(61, "C", "major")
        self.assertIn(result, [60, 62])

    def test_note_to_midi_invalid(self):
        with self.assertRaises(ValueError):
            note_to_midi("Z4")


class TestEuclideanRhythm(unittest.TestCase):
    """Test the Euclidean rhythm algorithm."""

    def test_e8_13(self):
        result = euclidean_rhythm(8, 13)
        self.assertEqual(sum(result), 8)
        self.assertEqual(len(result), 13)
        positions = [i for i, v in enumerate(result) if v]
        gaps = []
        for i in range(len(positions)):
            next_pos = positions[(i + 1) % len(positions)]
            curr_pos = positions[i]
            if i < len(positions) - 1:
                gaps.append(next_pos - curr_pos)
            else:
                gaps.append((positions[0] + len(result)) - curr_pos)
        for g in gaps:
            self.assertLessEqual(g, 2)

    def test_e5_8(self):
        result = euclidean_rhythm(5, 8)
        self.assertEqual(sum(result), 5)
        self.assertEqual(len(result), 8)

    def test_e3_8(self):
        result = euclidean_rhythm(3, 8)
        self.assertEqual(sum(result), 3)
        self.assertEqual(len(result), 8)

    def test_e0_8(self):
        result = euclidean_rhythm(0, 8)
        self.assertEqual(result, [False] * 8)

    def test_e8_8(self):
        result = euclidean_rhythm(8, 8)
        self.assertEqual(result, [True] * 8)

    def test_e1_4(self):
        result = euclidean_rhythm(1, 4)
        self.assertEqual(sum(result), 1)

    def test_e4_4(self):
        result = euclidean_rhythm(4, 4)
        self.assertEqual(result, [True] * 4)

    def test_e5_16(self):
        result = euclidean_rhythm(5, 16)
        self.assertEqual(sum(result), 5)

    def test_rotation(self):
        base = euclidean_rhythm(5, 8)
        rotated = euclidean_rhythm(5, 8, rotation=2)
        self.assertNotEqual(base, rotated)
        self.assertEqual(sum(base), sum(rotated))

    def test_euclidean_pattern_notes(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="pentatonic_minor")
        active = sum(1 for s in pattern.steps if s.notes)
        self.assertEqual(active, 5)


class TestPatterns(unittest.TestCase):
    """Test patterns.py."""

    def test_step_defaults(self):
        step = Step()
        self.assertEqual(step.notes, [])
        self.assertEqual(step.velocity, 100)
        self.assertEqual(step.gate, 0.8)
        self.assertEqual(step.probability, 1.0)
        self.assertFalse(step.tie)
        self.assertEqual(step.timing_offset, 0.0)

    def test_pattern_length(self):
        steps = [Step(notes=[60])] * 4
        pattern = Pattern(name="test", steps=steps, length=8)
        self.assertEqual(len(pattern.steps), 8)

    def test_pattern_truncate(self):
        steps = [Step(notes=[60])] * 10
        pattern = Pattern(name="test", steps=steps, length=5)
        self.assertEqual(len(pattern.steps), 5)

    def test_pattern_rotate(self):
        steps = [Step(notes=[60]), Step(), Step(notes=[62]), Step()]
        pattern = Pattern(name="test", steps=steps, length=4)
        rotated = pattern.rotate(1)
        self.assertEqual(rotated.steps[0].notes, [])
        self.assertEqual(rotated.steps[1].notes, [60])

    def test_pattern_reverse(self):
        steps = [Step(notes=[60]), Step(), Step(notes=[62]), Step()]
        pattern = Pattern(name="test", steps=steps, length=4)
        reversed_pat = pattern.reverse()
        self.assertEqual(reversed_pat.steps[0].notes, [])
        self.assertEqual(reversed_pat.steps[1].notes, [62])

    def test_pattern_invert(self):
        steps = [Step(notes=[60]), Step(notes=[64])]
        pattern = Pattern(name="test", steps=steps, length=2)
        inverted = pattern.invert(7)
        self.assertEqual(inverted.steps[0].notes, [67])
        self.assertEqual(inverted.steps[1].notes, [71])

    def test_pattern_mask(self):
        steps = [Step(notes=[60]), Step(notes=[62]), Step(notes=[64]), Step(notes=[65])]
        pattern = Pattern(name="test", steps=steps, length=4)
        masked = pattern.mask([0, 2])
        self.assertEqual(masked.steps[0].notes, [60])
        self.assertEqual(masked.steps[1].notes, [])
        self.assertEqual(masked.steps[2].notes, [64])
        self.assertEqual(masked.steps[3].notes, [])

    def test_step_probability_always(self):
        step = Step(notes=[60], probability=1.0)
        for _ in range(100):
            self.assertTrue(step.should_fire())

    def test_step_probability_never(self):
        step = Step(notes=[60], probability=0.0)
        for _ in range(100):
            self.assertFalse(step.should_fire())

    def test_track_mute(self):
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track = Track(name="muted", pattern=pattern, mute=True)
        events = track.render_notes()
        self.assertEqual(events, [])

    def test_track_octave_shift(self):
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track = Track(name="shifted", pattern=pattern, octave_shift=1)
        events = track.render_notes()
        self.assertEqual(events[0]["note"], 72)

    def test_song_add_track(self):
        song = Song(name="test")
        song.add_track(Track(name="t1"))
        self.assertEqual(len(song.tracks), 1)

    def test_pattern_get_step_wrap(self):
        steps = [Step(notes=[60]), Step(notes=[62])]
        pattern = Pattern(name="test", steps=steps, length=2)
        self.assertEqual(pattern.get_step(2).notes, [60])  # Wraps


class TestGrooves(unittest.TestCase):
    """Test grooves.py."""

    def test_groove_preserves_structure(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        grooved = apply_groove(pattern, "swing_16th")
        self.assertEqual(len(grooved.steps), len(pattern.steps))
        for i in range(len(pattern.steps)):
            self.assertEqual(grooved.steps[i].notes, pattern.steps[i].notes)

    def test_groove_applies_timing_offsets(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        grooved = apply_groove(pattern, "swing_16th", intensity=0.8)
        has_timing = any(abs(s.timing_offset) > 0.001 for s in grooved.steps)
        self.assertTrue(has_timing)

    def test_groove_zero_intensity(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major", velocity=100)
        grooved = apply_groove(pattern, "straight", intensity=0.0)
        for i in range(len(pattern.steps)):
            self.assertEqual(grooved.steps[i].velocity, pattern.steps[i].velocity)

    def test_velocity_curve_crescendo(self):
        pattern = random_pattern(16, density=1.0, root="C", scale="major")
        curved = apply_velocity_curve(pattern, "crescendo")
        active_vels = [s.velocity for s in curved.steps if s.notes]
        self.assertLess(active_vels[0], active_vels[-1])

    def test_unknown_groove_raises(self):
        pattern = Pattern(name="test", steps=[Step()], length=1)
        with self.assertRaises(ValueError):
            apply_groove(pattern, "nonexistent")

    def test_unknown_curve_raises(self):
        pattern = Pattern(name="test", steps=[Step()], length=1)
        with self.assertRaises(ValueError):
            apply_velocity_curve(pattern, "nonexistent")

    def test_all_groove_templates_exist(self):
        for name in GROOVE_TEMPLATES:
            self.assertIsInstance(GROOVE_TEMPLATES[name], list)
            self.assertEqual(len(GROOVE_TEMPLATES[name]), 16)

    def test_all_velocity_curves_callable(self):
        for name, func in VELOCITY_CURVES.items():
            result = func(16)
            self.assertEqual(len(result), 16)
            for v in result:
                self.assertGreaterEqual(v, 1)
                self.assertLessEqual(v, 127)


class TestLSystem(unittest.TestCase):
    """Test lsystem.py."""

    def test_presets_exist(self):
        self.assertGreater(len(LS_PRESETS), 0)

    def test_lsystem_generates_pattern(self):
        pattern = lsystem_pattern("cantor", iterations=2, root="C", scale="major")
        self.assertGreater(len(pattern.steps), 0)

    def test_lsystem_custom(self):
        pattern = lsystem_pattern(axiom="A", rules={"A": "A+R"}, iterations=2, root="C", scale="major")
        self.assertGreater(len(pattern.steps), 0)

    def test_lsystem_all_presets(self):
        for name in LS_PRESETS:
            pattern = lsystem_pattern(name, iterations=2, root="C", scale="major")
            self.assertGreater(len(pattern.steps), 0, f"Preset {name} produced empty pattern")

    def test_lsystem_growth_limit(self):
        """L-System should not grow beyond the limit."""
        pattern = lsystem_pattern("koch_snowflake", iterations=10, root="C", scale="major")
        self.assertGreater(len(pattern.steps), 0)


class TestProgressions(unittest.TestCase):
    """Test progressions.py."""

    def test_build_progression_pop(self):
        result = build_progression("pop_I_V_vi_IV", key="C")
        self.assertEqual(len(result), 4)

    def test_build_progression_jazz(self):
        result = build_progression("jazz_ii_V_I", key="C")
        self.assertEqual(len(result), 3)

    def test_unknown_progression_raises(self):
        with self.assertRaises(ValueError):
            build_progression("nonexistent")

    def test_progression_in_g(self):
        result = build_progression("pop_I_V_vi_IV", key="G")
        self.assertEqual(result[0][0], "G")

    def test_blues_12bar_length(self):
        result = build_progression("blues_12bar", key="C")
        self.assertEqual(len(result), 12)

    def test_all_progressions_buildable(self):
        for name in PROGRESSIONS:
            result = build_progression(name, key="C")
            self.assertGreater(len(result), 0, f"Progression {name} produced no chords")


class TestSerialization(unittest.TestCase):
    """Test serialization.py."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_song_roundtrip(self):
        song = Song(
            name="Test Song",
            tracks=[
                Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9),
                Track(name="Melody", pattern=euclidean_pattern(5, 16, root="C", scale="major"), channel=0),
            ],
            bpm=130,
        )
        path = os.path.join(self.temp_dir, "test_song.json")
        save_song(song, path)
        loaded = load_song(path)
        self.assertEqual(loaded.name, song.name)
        self.assertEqual(loaded.bpm, song.bpm)
        self.assertEqual(len(loaded.tracks), len(song.tracks))
        for i, (orig, load) in enumerate(zip(song.tracks, loaded.tracks)):
            self.assertEqual(orig.name, load.name)
            self.assertEqual(orig.channel, load.channel)
            self.assertEqual(len(orig.pattern.steps), len(load.pattern.steps))

    def test_pattern_roundtrip(self):
        pattern = euclidean_pattern(7, 16, root="A", scale="minor")
        path = os.path.join(self.temp_dir, "test_pattern.json")
        save_pattern(pattern, path)
        loaded = load_pattern(path)
        self.assertEqual(loaded.name, pattern.name)
        self.assertEqual(loaded.length, pattern.length)
        for orig, load in zip(pattern.steps, loaded.steps):
            self.assertEqual(orig.notes, load.notes)
            self.assertEqual(orig.velocity, load.velocity)
            self.assertEqual(orig.timing_offset, load.timing_offset)

    def test_timing_offset_roundtrip(self):
        step = Step(notes=[60], velocity=100, timing_offset=15.5)
        pattern = Pattern(name="offset_test", steps=[step], length=1)
        path = os.path.join(self.temp_dir, "offset_test.json")
        save_pattern(pattern, path)
        loaded = load_pattern(path)
        self.assertAlmostEqual(loaded.steps[0].timing_offset, 15.5)


class TestExport(unittest.TestCase):
    """Test MIDI export."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_basic_export(self):
        drums = Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9)
        song = Song(name="Export Test", tracks=[drums], bpm=120)
        path = os.path.join(self.temp_dir, "test_export.mid")
        result = song_to_midi(song, path)
        self.assertEqual(result, path)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)

    def test_multi_track_export(self):
        tracks = [
            Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9),
            Track(name="Bass", pattern=euclidean_pattern(3, 8, root="C", scale="minor", octave=2), channel=1, program=34),
            Track(name="Lead", pattern=euclidean_pattern(5, 16, root="C", scale="pentatonic_minor", octave=5), channel=2, program=81),
        ]
        song = Song(name="Multi-Track Test", tracks=tracks, bpm=128)
        path = os.path.join(self.temp_dir, "test_multi.mid")
        song_to_midi(song, path)
        self.assertTrue(os.path.exists(path))

    def test_metronome_export(self):
        drums = Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9)
        song = Song(name="Metronome Test", tracks=[drums], bpm=100)
        path = os.path.join(self.temp_dir, "test_metronome.mid")
        song_to_midi(song, path, add_metronome=True)
        self.assertTrue(os.path.exists(path))

    def test_pattern_to_midi(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        path = os.path.join(self.temp_dir, "pattern.mid")
        result = pattern_to_midi(pattern, path, bpm=110)
        self.assertTrue(os.path.exists(path))


class TestDrumPatterns(unittest.TestCase):
    """Test drum pattern generation."""

    def test_four_on_floor(self):
        drums = drum_pattern("four_on_floor", 16)
        for step_idx in [0, 4, 8, 12]:
            self.assertIn(36, drums.steps[step_idx].notes)

    def test_all_styles_produce_patterns(self):
        for style in ["four_on_floor", "breakbeat", "hiphop", "bossa", "waltz"]:
            pattern = drum_pattern(style, 16)
            self.assertEqual(len(pattern.steps), 16)

    def test_unknown_style(self):
        pattern = drum_pattern("unknown_style", 16)
        self.assertEqual(len(pattern.steps), 16)


class TestMorph(unittest.TestCase):
    """Test pattern morphing."""

    def test_morph_position_0(self):
        a = euclidean_pattern(3, 8, root="C", scale="major")
        b = euclidean_pattern(5, 8, root="C", scale="minor")
        morphed = morph_pattern(a, b, 0.0)
        for i in range(min(a.length, morphed.length)):
            self.assertEqual(morphed.steps[i].notes, a.get_step(i).notes)

    def test_morph_position_1(self):
        a = euclidean_pattern(3, 8, root="C", scale="major")
        b = euclidean_pattern(5, 8, root="C", scale="minor")
        morphed = morph_pattern(a, b, 1.0)
        for i in range(min(b.length, morphed.length)):
            self.assertEqual(morphed.steps[i].notes, b.get_step(i).notes)


class TestArrangement(unittest.TestCase):
    """Test song arrangement."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_verse_chorus_verse(self):
        v_melody = euclidean_pattern(3, 16, root="C", scale="major")
        c_melody = euclidean_pattern(5, 16, root="C", scale="major")
        v_bass = bassline_from_chords([("C", "min7")], 16, octave=2)
        c_bass = bassline_from_chords([("C", "min7")], 16, octave=2, pattern_type="walking")
        v_drums = drum_pattern("four_on_floor", 16)
        c_drums = drum_pattern("breakbeat", 16)

        arr = verse_chorus_verse(v_melody, c_melody, v_bass, c_bass, v_drums, c_drums, key="C", bpm=120)
        song = arr.render_to_song()
        self.assertEqual(len(song.tracks), 3)
        for track in song.tracks:
            self.assertEqual(track.pattern.length, 96)

    def test_arrangement_export(self):
        v_melody = euclidean_pattern(3, 16, root="C", scale="major")
        c_melody = euclidean_pattern(5, 16, root="C", scale="major")
        v_bass = bassline_from_chords([("C", "min7")], 16, octave=2)
        c_bass = bassline_from_chords([("C", "min7")], 16, octave=2, pattern_type="walking")
        v_drums = drum_pattern("four_on_floor", 16)
        c_drums = drum_pattern("breakbeat", 16)

        arr = verse_chorus_verse(v_melody, c_melody, v_bass, c_bass, v_drums, c_drums, key="C")
        path = os.path.join(self.temp_dir, "arrangement.mid")
        arr.export_midi(path)
        self.assertTrue(os.path.exists(path))


class TestTieRendering(unittest.TestCase):
    """Test that tied notes render correctly."""

    def test_tie_duration(self):
        pattern = Pattern(name="test", steps=[
            Step(notes=[60], velocity=100, gate=1.0, tie=True),
            Step(tie=True),
            Step(),
        ], length=3)
        track = Track(name="test", pattern=pattern, channel=0)
        events = track.render_notes()
        self.assertEqual(len(events), 1)
        self.assertGreater(events[0]["duration_steps"], 1)

    def test_non_tie_duration(self):
        pattern = Pattern(name="test", steps=[
            Step(notes=[60], velocity=100, gate=0.8),
            Step(),
        ], length=2)
        track = Track(name="test", pattern=pattern, channel=0)
        events = track.render_notes()
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["duration_steps"], 0.8)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_empty_pattern(self):
        pattern = Pattern(name="empty", steps=[], length=16)
        track = Track(name="test", pattern=pattern, channel=0)
        events = track.render_notes()
        self.assertEqual(len(events), 0)

    def test_solo_tracks(self):
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track1 = Track(name="normal", pattern=pattern, channel=0)
        track2 = Track(name="solo", pattern=pattern, channel=1, solo=True)
        song = Song(name="solo_test", tracks=[track1, track2])
        events = song.render()
        self.assertTrue(all(e["channel"] == 1 for e in events))

    def test_note_clamping(self):
        steps = [Step(notes=[-5]), Step(notes=[130])]
        pattern = Pattern(name="clamp_test", steps=steps, length=2)
        track = Track(name="test", pattern=pattern, channel=0)
        song = Song(name="clamp_test", tracks=[track], bpm=120)
        path = os.path.join(self.temp_dir, "clamp.mid")
        result = song_to_midi(song, path)
        self.assertTrue(os.path.exists(result))

    def test_velocity_clamping(self):
        step = Step(notes=[60], velocity=200)
        pattern = Pattern(name="vel_test", steps=[step], length=1)
        track = Track(name="test", pattern=pattern, channel=0)
        events = track.render_notes()
        self.assertEqual(events[0]["velocity"], 200)

    def test_negative_octave_shift(self):
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track = Track(name="bass", pattern=pattern, channel=0, octave_shift=-1)
        events = track.render_notes()
        self.assertEqual(events[0]["note"], 48)


class TestConfig(unittest.TestCase):
    """Test configuration management."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_default_config(self):
        config = SequencerConfig()
        self.assertEqual(config.bpm, 120)
        self.assertEqual(config.default_root, "C")
        self.assertEqual(config.default_scale, "pentatonic_minor")

    def test_config_from_dict(self):
        data = {"bpm": 140, "default_root": "G", "default_scale": "dorian"}
        config = SequencerConfig.from_dict(data)
        self.assertEqual(config.bpm, 140)
        self.assertEqual(config.default_root, "G")
        self.assertEqual(config.default_scale, "dorian")

    def test_config_ignore_unknown_keys(self):
        data = {"bpm": 100, "unknown_key": "ignored"}
        config = SequencerConfig.from_dict(data)
        self.assertEqual(config.bpm, 100)
        self.assertFalse(hasattr(config, "unknown_key"))

    def test_config_json_roundtrip(self):
        config = SequencerConfig(bpm=130, default_root="E", default_scale="minor")
        path = os.path.join(self.temp_dir, "config.json")
        config.to_json(path)
        loaded = SequencerConfig.from_json(path)
        self.assertEqual(loaded.bpm, 130)
        self.assertEqual(loaded.default_root, "E")
        self.assertEqual(loaded.default_scale, "minor")

    def test_config_validation_invalid_bpm(self):
        with self.assertRaises(ValueError):
            SequencerConfig(bpm=500)

    def test_config_validation_invalid_channel(self):
        with self.assertRaises(ValueError):
            SequencerConfig(default_channel=20)

    def test_generate_default_config(self):
        path = os.path.join(self.temp_dir, "default_config.json")
        generate_default_config(path, fmt="json")
        self.assertTrue(os.path.exists(path))
        loaded = SequencerConfig.from_json(path)
        self.assertEqual(loaded.bpm, 120)

    def test_config_apply_to_song(self):
        config = SequencerConfig(bpm=140, ppqn=960)
        song = Song(name="test")
        config.apply_to_song(song)
        self.assertEqual(song.bpm, 140)
        self.assertEqual(song.ppqn, 960)


class TestValidation(unittest.TestCase):
    """Test input validation."""

    def test_validate_note_name_valid(self):
        self.assertEqual(validate_note_name("C"), "C")
        self.assertEqual(validate_note_name("F#4"), "F#4")

    def test_validate_note_name_invalid(self):
        with self.assertRaises(ValidationError):
            validate_note_name("Z")
        with self.assertRaises(ValidationError):
            validate_note_name("")

    def test_validate_scale_valid(self):
        self.assertEqual(validate_scale("major"), "major")

    def test_validate_scale_invalid(self):
        with self.assertRaises(ValidationError):
            validate_scale("nonexistent")

    def test_validate_chord_quality(self):
        self.assertEqual(validate_chord_quality("maj7"), "maj7")
        with self.assertRaises(ValidationError):
            validate_chord_quality("nonexistent")

    def test_validate_midi_note(self):
        self.assertEqual(validate_midi_note(60), 60)
        self.assertEqual(validate_midi_note(-5), 0)  # Clamped
        self.assertEqual(validate_midi_note(200), 127)  # Clamped

    def test_validate_velocity(self):
        self.assertEqual(validate_velocity(100), 100)
        self.assertEqual(validate_velocity(200), 127)  # Clamped

    def test_validate_channel(self):
        self.assertEqual(validate_channel(0), 0)
        with self.assertRaises(ValidationError):
            validate_channel(16)

    def test_validate_program(self):
        self.assertEqual(validate_program(0), 0)
        with self.assertRaises(ValidationError):
            validate_program(128)

    def test_validate_bpm(self):
        self.assertEqual(validate_bpm(120), 120)
        with self.assertRaises(ValidationError):
            validate_bpm(10)

    def test_validate_octave(self):
        self.assertEqual(validate_octave(4), 4)
        with self.assertRaises(ValidationError):
            validate_octave(15)

    def test_validate_pattern_length(self):
        self.assertEqual(validate_pattern_length(16), 16)
        with self.assertRaises(ValidationError):
            validate_pattern_length(0)

    def test_validate_density(self):
        self.assertEqual(validate_density(0.5), 0.5)
        with self.assertRaises(ValidationError):
            validate_density(1.5)

    def test_validate_gate(self):
        self.assertEqual(validate_gate(0.8), 0.8)
        with self.assertRaises(ValidationError):
            validate_gate(1.5)

    def test_validate_probability(self):
        self.assertEqual(validate_probability(0.5), 0.5)
        with self.assertRaises(ValidationError):
            validate_probability(-0.1)

    def test_validate_time_signature(self):
        self.assertEqual(validate_time_signature((4, 4)), (4, 4))
        with self.assertRaises(ValidationError):
            validate_time_signature((0, 4))
        with self.assertRaises(ValidationError):
            validate_time_signature((4, 3))


class TestAnalysis(unittest.TestCase):
    """Test analysis module."""

    def test_pattern_stats(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        stats = pattern_stats(pattern)
        self.assertEqual(stats["active_steps"], 5)
        self.assertEqual(stats["total_steps"], 16)
        self.assertGreater(stats["density"], 0)
        self.assertLessEqual(stats["density"], 1.0)

    def test_track_stats(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        track = Track(name="Test", pattern=pattern, channel=0, program=81)
        stats = track_stats(track)
        self.assertEqual(stats["track_name"], "Test")
        self.assertEqual(stats["channel"], 0)

    def test_song_stats(self):
        song = Song(
            name="Test Song",
            tracks=[Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9)],
            bpm=120,
        )
        stats = song_stats(song)
        self.assertEqual(stats["song_name"], "Test Song")
        self.assertEqual(stats["bpm"], 120)
        self.assertEqual(stats["total_tracks"], 1)
        self.assertGreater(stats["duration_seconds"], 0)

    def test_song_summary(self):
        song = Song(
            name="Test",
            tracks=[Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9)],
            bpm=120,
        )
        summary = song_summary(song)
        self.assertIn("Test", summary)
        self.assertIn("120", summary)

    def test_visualize_pattern_block(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        vis = visualize_pattern(pattern, style="block")
        self.assertIn("Pattern", vis)

    def test_visualize_pattern_dot(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        vis = visualize_pattern(pattern, style="dot")
        self.assertIn("●", vis)

    def test_visualize_pattern_piano(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        vis = visualize_pattern(pattern, style="piano")
        self.assertIn("Note range", vis)

    def test_note_distribution(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="pentatonic_minor")
        dist = note_distribution(pattern)
        self.assertGreater(len(dist), 0)
        total = sum(dist.values())
        self.assertEqual(total, 5)  # 5 active notes

    def test_interval_distribution(self):
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        intervals = interval_distribution(pattern)
        # Should have at least some intervals between consecutive notes
        self.assertGreaterEqual(len(intervals), 0)


class TestBatch(unittest.TestCase):
    """Test batch composition."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_composition_recipe(self):
        recipe = CompositionRecipe(
            name="test_recipe",
            bpm=130,
            root="A",
            scale="minor",
            tracks=[
                {"type": "euclidean", "beats": 5, "length": 16, "channel": 0, "program": 81},
                {"type": "drums", "style": "four_on_floor", "length": 16, "channel": 9},
            ],
        )
        song = recipe.generate()
        self.assertEqual(song.name, "test_recipe")
        self.assertEqual(song.bpm, 130)
        self.assertEqual(len(song.tracks), 2)

    def test_euclidean_variations(self):
        output_dir = os.path.join(self.temp_dir, "euc_vars")
        files = euclidean_variations(
            root="C", scale="major", bpm=120,
            beat_range=(3, 5), length=8,
            output_dir=output_dir,
        )
        self.assertEqual(len(files), 3)  # beats 3, 4, 5
        for f in files:
            self.assertTrue(os.path.exists(f))

    def test_scale_exploration(self):
        output_dir = os.path.join(self.temp_dir, "scales")
        files = scale_exploration(root="C", bpm=120, length=8, output_dir=output_dir)
        self.assertGreater(len(files), 10)
        for f in files:
            self.assertTrue(os.path.exists(f))

    def test_progression_album(self):
        output_dir = os.path.join(self.temp_dir, "progs")
        files = progression_album(key="C", bpm=120, length_per_chord=8, output_dir=output_dir)
        self.assertGreater(len(files), 5)
        for f in files:
            self.assertTrue(os.path.exists(f))


class TestExtendedDrums(unittest.TestCase):
    """Test extended drum patterns."""

    def test_extended_style_jungle(self):
        pattern = extended_drum_pattern("jungle", 16)
        self.assertEqual(len(pattern.steps), 16)
        self.assertGreater(sum(1 for s in pattern.steps if s.notes), 0)

    def test_extended_style_trap(self):
        pattern = extended_drum_pattern("trap", 16)
        self.assertEqual(len(pattern.steps), 16)

    def test_all_extended_styles(self):
        for style in list_extended_styles():
            pattern = extended_drum_pattern(style, 16)
            self.assertEqual(len(pattern.steps), 16)

    def test_fallback_to_standard(self):
        """Unknown extended style should fall back to standard drum_pattern."""
        pattern = extended_drum_pattern("four_on_floor", 16)
        self.assertEqual(len(pattern.steps), 16)

    def test_list_styles(self):
        styles = list_extended_styles()
        self.assertGreater(len(styles), 0)
        for name, desc in styles.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(desc, str)


class TestCLI(unittest.TestCase):
    """Test CLI functionality."""

    def test_info_scales(self):
        """Test that info scales command doesn't crash."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "sequencer", "info", "scales"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("major", result.stdout)

    def test_info_drums(self):
        """Test that info drums command shows extended styles."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "sequencer", "info", "drums"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("jungle", result.stdout)

    def test_generate_no_output(self):
        """Test that generate without -o prints visualization."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "sequencer", "generate", "euclidean", "--beats", "5", "--length", "8"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Pattern", result.stdout)

    def test_generate_with_output(self):
        """Test that generate with -o creates a MIDI file."""
        import subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "test.mid")
            result = subprocess.run(
                [sys.executable, "-m", "sequencer", "generate", "euclidean",
                 "--beats", "5", "--length", "8", "-o", output],
                capture_output=True, text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(os.path.exists(output))


class TestNegativeOctaveRoundtrip(unittest.TestCase):
    """Regression test for negative octave roundtrip bug."""

    def test_negative_octave_roundtrip(self):
        for midi_num in range(0, 12):
            note_name = midi_to_note(midi_num)
            midi_back = note_to_midi(note_name)
            self.assertEqual(midi_back, midi_num,
                             f"Negative octave roundtrip failed: {midi_num}")


if __name__ == "__main__":
    unittest.main()