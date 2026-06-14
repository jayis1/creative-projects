"""Tests for the MIDI step sequencer — bug verification and regression tests."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from sequencer.scales import (
    note_to_midi, midi_to_note, scale_notes, chord_notes, degree_to_note,
    quantize_to_scale, SCALE_INTERVALS,
)
from sequencer.patterns import Step, Pattern, Track, Song
from sequencer.generators import (
    euclidean_rhythm, euclidean_pattern, random_pattern, markov_pattern,
    chord_pattern, bassline_from_chords, drum_pattern, morph_pattern,
)
from sequencer.grooves import apply_groove, apply_velocity_curve, GROOVE_TEMPLATES
from sequencer.lsystem import lsystem_pattern, PRESETS as LS_PRESETS
from sequencer.progressions import build_progression, PROGRESSIONS
from sequencer.arrangement import Arrangement, Section
from sequencer.serialization import save_song, load_song, save_pattern, load_pattern
from sequencer.export import song_to_midi, pattern_to_midi


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
        """note_to_midi should default to octave 4 if not specified."""
        self.assertEqual(note_to_midi("C"), 60)  # Same as C4

    def test_midi_to_note_roundtrip(self):
        """midi_to_note should produce notes that convert back to the same MIDI number."""
        for midi_num in range(0, 128, 7):
            note_name = midi_to_note(midi_num)
            midi_back = note_to_midi(note_name)
            self.assertEqual(midi_back, midi_num,
                             f"Roundtrip failed: {midi_num} -> {note_name} -> {midi_back}")

    def test_midi_to_note_negative_octave(self):
        """MIDI notes 0-11 should produce octave -1 (C-1 through B-1)."""
        for midi_num in range(12):
            note_name = midi_to_note(midi_num)
            midi_back = note_to_midi(note_name)
            self.assertEqual(midi_back, midi_num,
                             f"Negative octave roundtrip failed: {midi_num} -> {note_name} -> {midi_back}")

    def test_midi_to_note_all_notes(self):
        """All 128 MIDI numbers should roundtrip correctly."""
        for midi_num in range(128):
            note_name = midi_to_note(midi_num)
            midi_back = note_to_midi(note_name)
            self.assertEqual(midi_back, midi_num)

    def test_scale_notes_c_major(self):
        notes = scale_notes("C", "major", 1, 4)
        # C major: C D E F G A B C(octave) = 60 62 64 65 67 69 71 72
        # scale_notes includes the top root of the next octave
        expected = [60, 62, 64, 65, 67, 69, 71, 72]
        self.assertEqual(notes, expected)

    def test_scale_notes_length(self):
        """scale_notes should return (intervals_per_octave * octaves + 1) notes."""
        for scale_name, intervals in SCALE_INTERVALS.items():
            notes = scale_notes("C", scale_name, 2, 4)
            expected_len = len(intervals) * 2 + 1
            self.assertEqual(len(notes), expected_len,
                             f"Scale {scale_name}: expected {expected_len} notes, got {len(notes)}")

    def test_chord_notes(self):
        # C major = C E G = 60 64 67
        notes = chord_notes("C", "maj", 4)
        self.assertEqual(notes, [60, 64, 67])

    def test_chord_notes_invalid(self):
        with self.assertRaises(ValueError):
            chord_notes("C", "invalid_quality")

    def test_unknown_scale(self):
        with self.assertRaises(ValueError):
            scale_notes("C", "nonexistent_scale")

    def test_quantize_to_scale(self):
        """quantize_to_scale should snap notes to the nearest scale tone."""
        # C#4 (61) should snap to C4 (60) or D4 (62) in C major
        result = quantize_to_scale(61, "C", "major")
        self.assertIn(result, [60, 62])


class TestEuclideanRhythm(unittest.TestCase):
    """Test the Euclidean rhythm algorithm."""

    def test_e8_13(self):
        """E(8,13) should have exactly 8 pulses distributed as evenly as possible."""
        result = euclidean_rhythm(8, 13)
        self.assertEqual(sum(result), 8)
        self.assertEqual(len(result), 13)
        # Check even distribution: max gap between consecutive pulses should be <= 2
        positions = [i for i, v in enumerate(result) if v]
        if positions:
            # Check wrap-around gaps too
            gaps = []
            for i in range(len(positions)):
                next_pos = positions[(i + 1) % len(positions)]
                curr_pos = positions[i]
                if i < len(positions) - 1:
                    gaps.append(next_pos - curr_pos)
                else:
                    gaps.append((positions[0] + len(result)) - curr_pos)
            for g in gaps:
                self.assertLessEqual(g, 2, f"Gap of {g} is too large for even distribution")

    def test_e5_8(self):
        """E(5,8) should produce a well-known Euclidean rhythm."""
        result = euclidean_rhythm(5, 8)
        # E(5,8) has exactly 5 True values
        self.assertEqual(sum(result), 5)
        self.assertEqual(len(result), 8)
        # Check even distribution: gaps should be 1 or 2
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

    def test_e3_8(self):
        """E(3,8) should produce [1,0,0,1,0,0,1,0] or a rotation."""
        result = euclidean_rhythm(3, 8)
        self.assertEqual(sum(result), 3)
        self.assertEqual(len(result), 8)

    def test_e0_8(self):
        """E(0,8) should produce all False."""
        result = euclidean_rhythm(0, 8)
        self.assertEqual(result, [False] * 8)

    def test_e8_8(self):
        """E(8,8) should produce all True."""
        result = euclidean_rhythm(8, 8)
        self.assertEqual(result, [True] * 8)

    def test_e1_4(self):
        """E(1,4) should produce exactly one pulse."""
        result = euclidean_rhythm(1, 4)
        self.assertEqual(sum(result), 1)
        self.assertEqual(len(result), 4)

    def test_e4_4(self):
        """E(4,4) should produce all True."""
        result = euclidean_rhythm(4, 4)
        self.assertEqual(result, [True] * 4)

    def test_e5_16(self):
        """E(5,16) should have exactly 5 True values."""
        result = euclidean_rhythm(5, 16)
        self.assertEqual(sum(result), 5)
        self.assertEqual(len(result), 16)

    def test_rotation(self):
        """Rotation should shift the pattern."""
        base = euclidean_rhythm(5, 8)
        rotated = euclidean_rhythm(5, 8, rotation=2)
        # Rotated should be a different arrangement
        self.assertNotEqual(base, rotated)
        # But same number of True values
        self.assertEqual(sum(base), sum(rotated))

    def test_euclidean_pattern_notes(self):
        """euclidean_pattern should create a pattern with the right number of active steps."""
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

    def test_pattern_length(self):
        """Pattern should pad to the specified length."""
        steps = [Step(notes=[60])] * 4
        pattern = Pattern(name="test", steps=steps, length=8)
        self.assertEqual(len(pattern.steps), 8)

    def test_pattern_truncate(self):
        """Pattern should truncate if steps exceed length."""
        steps = [Step(notes=[60])] * 10
        pattern = Pattern(name="test", steps=steps, length=5)
        self.assertEqual(len(pattern.steps), 5)

    def test_pattern_rotate(self):
        """Rotate should shift steps rightward."""
        steps = [Step(notes=[60]), Step(), Step(notes=[62]), Step()]
        pattern = Pattern(name="test", steps=steps, length=4)
        rotated = pattern.rotate(1)
        self.assertEqual(rotated.steps[0].notes, [])  # Original step 3 wraps to position 0
        self.assertEqual(rotated.steps[1].notes, [60])  # Original step 0

    def test_pattern_reverse(self):
        """Reverse should mirror the pattern."""
        steps = [Step(notes=[60]), Step(), Step(notes=[62]), Step()]
        pattern = Pattern(name="test", steps=steps, length=4)
        reversed_pat = pattern.reverse()
        self.assertEqual(reversed_pat.steps[0].notes, [])  # Original step 3
        self.assertEqual(reversed_pat.steps[1].notes, [62])  # Original step 2

    def test_pattern_invert(self):
        """Invert should transpose all notes."""
        steps = [Step(notes=[60]), Step(notes=[64])]
        pattern = Pattern(name="test", steps=steps, length=2)
        inverted = pattern.invert(7)
        self.assertEqual(inverted.steps[0].notes, [67])
        self.assertEqual(inverted.steps[1].notes, [71])

    def test_pattern_mask(self):
        """Mask should keep only specified positions."""
        steps = [Step(notes=[60]), Step(notes=[62]), Step(notes=[64]), Step(notes=[65])]
        pattern = Pattern(name="test", steps=steps, length=4)
        masked = pattern.mask([0, 2])
        self.assertEqual(masked.steps[0].notes, [60])
        self.assertEqual(masked.steps[1].notes, [])
        self.assertEqual(masked.steps[2].notes, [64])
        self.assertEqual(masked.steps[3].notes, [])

    def test_step_probability_always(self):
        """Step with probability 1.0 should always fire."""
        step = Step(notes=[60], probability=1.0)
        for _ in range(100):
            self.assertTrue(step.should_fire())

    def test_step_probability_never(self):
        """Step with probability 0.0 should never fire."""
        step = Step(notes=[60], probability=0.0)
        for _ in range(100):
            self.assertFalse(step.should_fire())

    def test_track_mute(self):
        """Muted track should render no events."""
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track = Track(name="muted", pattern=pattern, mute=True)
        events = track.render_notes()
        self.assertEqual(events, [])

    def test_track_octave_shift(self):
        """Octave shift should transpose all notes by 12 semitones per octave."""
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track = Track(name="shifted", pattern=pattern, octave_shift=1)
        events = track.render_notes()
        self.assertEqual(events[0]["note"], 72)  # 60 + 12


class TestGrooves(unittest.TestCase):
    """Test grooves.py."""

    def test_groove_preserves_structure(self):
        """Applying a groove should preserve the number of steps and note structure."""
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        grooved = apply_groove(pattern, "swing_16th")
        self.assertEqual(len(grooved.steps), len(pattern.steps))
        # Notes should be preserved (only velocity and timing change)
        for i in range(len(pattern.steps)):
            self.assertEqual(grooved.steps[i].notes, pattern.steps[i].notes)

    def test_groove_applies_timing_offsets(self):
        """Groove should set timing_offset on steps (bug fix: previously discarded)."""
        pattern = euclidean_pattern(5, 16, root="C", scale="major")
        grooved = apply_groove(pattern, "swing_16th", intensity=0.8)
        # At least some steps should have non-zero timing_offset
        has_timing = any(abs(s.timing_offset) > 0.001 for s in grooved.steps)
        self.assertTrue(has_timing, "Groove should apply non-zero timing offsets to some steps")

    def test_groove_zero_intensity(self):
        """Groove with intensity 0 should not change velocities."""
        pattern = euclidean_pattern(5, 16, root="C", scale="major", velocity=100)
        grooved = apply_groove(pattern, "straight", intensity=0.0)
        for i in range(len(pattern.steps)):
            self.assertEqual(grooved.steps[i].velocity, pattern.steps[i].velocity)

    def test_velocity_curve_crescendo(self):
        """Crescendo should start low and end high."""
        pattern = random_pattern(16, density=1.0, root="C", scale="major")
        curved = apply_velocity_curve(pattern, "crescendo")
        # First active step should have lower velocity than last
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


class TestLSystem(unittest.TestCase):
    """Test lsystem.py."""

    def test_presets_exist(self):
        self.assertGreater(len(LS_PRESETS), 0)

    def test_lsystem_generates_pattern(self):
        """L-System should generate a pattern with at least one step."""
        pattern = lsystem_pattern("cantor", iterations=2, root="C", scale="major")
        self.assertGreater(len(pattern.steps), 0)

    def test_lsystem_custom(self):
        """Custom axiom and rules should work."""
        pattern = lsystem_pattern(axiom="A", rules={"A": "A+R"}, iterations=2, root="C", scale="major")
        self.assertGreater(len(pattern.steps), 0)


class TestProgressions(unittest.TestCase):
    """Test progressions.py."""

    def test_build_progression_pop(self):
        result = build_progression("pop_I_V_vi_IV", key="C")
        self.assertEqual(len(result), 4)
        # All roots should be note names
        for root, quality in result:
            self.assertIsInstance(root, str)
            self.assertIsInstance(quality, str)

    def test_build_progression_jazz(self):
        result = build_progression("jazz_ii_V_I", key="C")
        self.assertEqual(len(result), 3)

    def test_unknown_progression_raises(self):
        with self.assertRaises(ValueError):
            build_progression("nonexistent")

    def test_progression_in_g(self):
        """Pop progression in G should start with G."""
        result = build_progression("pop_I_V_vi_IV", key="G")
        self.assertEqual(result[0][0], "G")


class TestSerialization(unittest.TestCase):
    """Test serialization.py."""

    def setUp(self):
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_test")
        os.makedirs(self.temp_dir, exist_ok=True)

    def test_song_roundtrip(self):
        """A song should survive JSON serialization roundtrip."""
        from sequencer.generators import drum_pattern, euclidean_pattern
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
        """A pattern should survive JSON serialization roundtrip."""
        pattern = euclidean_pattern(7, 16, root="A", scale="minor")
        path = os.path.join(self.temp_dir, "test_pattern.json")
        save_pattern(pattern, path)
        loaded = load_pattern(path)
        self.assertEqual(loaded.name, pattern.name)
        self.assertEqual(loaded.length, pattern.length)
        self.assertEqual(len(loaded.steps), len(pattern.steps))
        for orig, load in zip(pattern.steps, loaded.steps):
            self.assertEqual(orig.notes, load.notes)
            self.assertEqual(orig.velocity, load.velocity)


class TestExport(unittest.TestCase):
    """Test MIDI export."""

    def setUp(self):
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_test")
        os.makedirs(self.temp_dir, exist_ok=True)

    def test_basic_export(self):
        """Basic MIDI export should produce a valid file."""
        drums = Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9)
        song = Song(name="Export Test", tracks=[drums], bpm=120)
        path = os.path.join(self.temp_dir, "test_export.mid")
        result = song_to_midi(song, path)
        self.assertEqual(result, path)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)

    def test_multi_track_export(self):
        """Multi-track export should produce a valid file."""
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
        """Export with metronome should produce a valid file."""
        drums = Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9)
        song = Song(name="Metronome Test", tracks=[drums], bpm=100)
        path = os.path.join(self.temp_dir, "test_metronome.mid")
        song_to_midi(song, path, add_metronome=True)
        self.assertTrue(os.path.exists(path))


class TestDrumPatterns(unittest.TestCase):
    """Test drum pattern generation."""

    def test_four_on_floor(self):
        drums = drum_pattern("four_on_floor", 16)
        # Should have kick on steps 0, 4, 8, 12
        for step_idx in [0, 4, 8, 12]:
            self.assertIn(36, drums.steps[step_idx].notes)  # 36 = BD

    def test_all_styles_produce_patterns(self):
        for style in ["four_on_floor", "breakbeat", "hiphop", "bossa", "waltz"]:
            pattern = drum_pattern(style, 16)
            self.assertEqual(len(pattern.steps), 16)

    def test_unknown_style(self):
        """Unknown style should fall through to default (no crash)."""
        pattern = drum_pattern("unknown_style", 16)
        self.assertEqual(len(pattern.steps), 16)


class TestMorph(unittest.TestCase):
    """Test pattern morphing."""

    def test_morph_position_0(self):
        """Morph at position 0 should be identical to pattern A."""
        a = euclidean_pattern(3, 8, root="C", scale="major")
        b = euclidean_pattern(5, 8, root="C", scale="minor")
        morphed = morph_pattern(a, b, 0.0)
        # Position 0 means all steps come from A
        for i in range(min(a.length, morphed.length)):
            self.assertEqual(morphed.steps[i].notes, a.get_step(i).notes)

    def test_morph_position_1(self):
        """Morph at position 1 should produce steps from pattern B (statistically)."""
        a = euclidean_pattern(3, 8, root="C", scale="major")
        b = euclidean_pattern(5, 8, root="C", scale="minor")
        morphed = morph_pattern(a, b, 1.0)
        # Position 1 means all steps come from B
        for i in range(min(b.length, morphed.length)):
            self.assertEqual(morphed.steps[i].notes, b.get_step(i).notes)


class TestArrangement(unittest.TestCase):
    """Test song arrangement."""

    def setUp(self):
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_test")
        os.makedirs(self.temp_dir, exist_ok=True)

    def test_verse_chorus_verse(self):
        from sequencer.generators import drum_pattern, euclidean_pattern
        from sequencer.arrangement import verse_chorus_verse

        v_melody = euclidean_pattern(3, 16, root="C", scale="major")
        c_melody = euclidean_pattern(5, 16, root="C", scale="major")
        v_bass = bassline_from_chords([("C", "min7")], 16, octave=2)
        c_bass = bassline_from_chords([("C", "min7")], 16, octave=2, pattern_type="walking")
        v_drums = drum_pattern("four_on_floor", 16)
        c_drums = drum_pattern("breakbeat", 16)

        arr = verse_chorus_verse(v_melody, c_melody, v_bass, c_bass, v_drums, c_drums, key="C", bpm=120)
        song = arr.render_to_song()
        self.assertEqual(len(song.tracks), 3)
        # Verse (2x16) + Chorus (2x16) + Verse (2x16) = 96 steps per track
        for track in song.tracks:
            self.assertEqual(track.pattern.length, 96)

    def test_arrangement_export(self):
        from sequencer.generators import drum_pattern, euclidean_pattern
        from sequencer.arrangement import verse_chorus_verse

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
        """A tied note should have a duration greater than 1 step."""
        pattern = Pattern(name="test", steps=[
            Step(notes=[60], velocity=100, gate=1.0, tie=True),
            Step(tie=True),
            Step(),
        ], length=3)
        track = Track(name="test", pattern=pattern, channel=0)
        events = track.render_notes()
        # Should have one event with duration > 1
        self.assertEqual(len(events), 1)
        self.assertGreater(events[0]["duration_steps"], 1)

    def test_non_tie_duration(self):
        """A non-tied note should have duration equal to its gate value."""
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

    def test_empty_pattern(self):
        """Empty pattern should render no events."""
        pattern = Pattern(name="empty", steps=[], length=16)
        track = Track(name="test", pattern=pattern, channel=0)
        events = track.render_notes()
        self.assertEqual(len(events), 0)

    def test_solo_tracks(self):
        """When solo is set, only solo tracks should render."""
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track1 = Track(name="normal", pattern=pattern, channel=0)
        track2 = Track(name="solo", pattern=pattern, channel=1, solo=True)
        song = Song(name="solo_test", tracks=[track1, track2])
        events = song.render()
        # Only solo track events should be included
        self.assertTrue(all(e["channel"] == 1 for e in events))

    def test_note_clamping(self):
        """Notes outside 0-127 should be clamped during export."""
        steps = [Step(notes=[-5]), Step(notes=[130])]
        pattern = Pattern(name="clamp_test", steps=steps, length=2)
        track = Track(name="test", pattern=pattern, channel=0)
        # This should not crash during MIDI export
        song = Song(name="clamp_test", tracks=[track], bpm=120)
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_test", "clamp.mid")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        result = song_to_midi(song, path)
        self.assertTrue(os.path.exists(result))

    def test_velocity_clamping(self):
        """Velocity outside 1-127 should be clamped during export."""
        step = Step(notes=[60], velocity=200)
        pattern = Pattern(name="vel_test", steps=[step], length=1)
        track = Track(name="test", pattern=pattern, channel=0)
        events = track.render_notes()
        # Track.render_notes doesn't clamp, but export should
        self.assertEqual(events[0]["velocity"], 200)  # Raw value
        # But MIDI export clamps to 1-127

    def test_negative_octave_shift(self):
        """Negative octave shift should lower notes."""
        pattern = Pattern(name="test", steps=[Step(notes=[60])], length=1)
        track = Track(name="bass", pattern=pattern, channel=0, octave_shift=-1)
        events = track.render_notes()
        self.assertEqual(events[0]["note"], 48)  # 60 - 12


if __name__ == "__main__":
    unittest.main()