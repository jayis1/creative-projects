"""Batch composition — generate multiple variations and song sets at once.

Useful for generating albums, exploring parameter spaces, or creating
large sets of variations for a given composition recipe.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from sequencer.patterns import Song, Track, Pattern, Step
from sequencer.generators import (
    euclidean_pattern, random_pattern, markov_pattern,
    chord_pattern, bassline_from_chords, drum_pattern,
)
from sequencer.grooves import apply_groove, apply_velocity_curve
from sequencer.progressions import build_progression
from sequencer.lsystem import lsystem_pattern
from sequencer.export import song_to_midi
from sequencer.analysis import song_stats

logger = logging.getLogger(__name__)


@dataclass
class CompositionRecipe:
    """A recipe for generating a song variation.

    Encapsulates all parameters needed to generate a song, making it easy
    to create parameter sweeps and systematic explorations.
    """
    name: str = "variation"
    bpm: int = 120
    root: str = "C"
    scale: str = "pentatonic_minor"
    tracks: List[Dict[str, object]] = field(default_factory=list)
    groove: Optional[str] = None
    velocity_curve: Optional[str] = None

    def generate(self) -> Song:
        """Generate the song from this recipe.

        Returns:
            A Song object
        """
        tracks = []
        for track_spec in self.tracks:
            track_type = track_spec.get("type", "euclidean")
            track_obj = _build_track(track_type, track_spec, self.root, self.scale)
            tracks.append(track_obj)

        song = Song(name=self.name, tracks=tracks, bpm=self.bpm)

        return song


def _build_track(track_type: str, spec: Dict[str, object], default_root: str, default_scale: str) -> Track:
    """Build a Track from a specification dict."""
    root = spec.get("root", default_root)
    scale = spec.get("scale", default_scale)
    octave = spec.get("octave", 4)
    channel = spec.get("channel", 0)
    program = spec.get("program", 0)
    name = spec.get("name", track_type)

    if track_type == "euclidean":
        beats = spec.get("beats", 5)
        length = spec.get("length", 16)
        pattern = euclidean_pattern(beats, length, root=root, scale=scale, octave=octave)
    elif track_type == "random":
        length = spec.get("length", 16)
        density = spec.get("density", 0.5)
        pattern = random_pattern(length, density=density, root=root, scale=scale, octave=octave)
    elif track_type == "markov":
        length = spec.get("length", 16)
        pattern = markov_pattern(length, root=root, scale=scale, octave=octave)
    elif track_type == "drums":
        style = spec.get("style", "four_on_floor")
        length = spec.get("length", 16)
        pattern = drum_pattern(style=style, length=length)
    elif track_type == "lsystem":
        preset = spec.get("preset", "cantor")
        iterations = spec.get("iterations", 3)
        pattern = lsystem_pattern(preset=preset, iterations=iterations, root=root, scale=scale, octave=octave)
    elif track_type == "bass":
        quality = spec.get("quality", "min7")
        length = spec.get("length", 16)
        bass_octave = spec.get("octave", 2)
        style = spec.get("bass_style", "steady")
        pattern = bassline_from_chords([(root, quality)], length, octave=bass_octave, pattern_type=style)
    elif track_type == "progression":
        prog_name = spec.get("progression", "pop_I_V_vi_IV")
        length = spec.get("length", 16)
        chords = build_progression(prog_name, key=root, scale=scale)
        pattern = chord_pattern(chords, length_per_chord=length, octave=octave, arpeggiate=spec.get("arpeggiate", True))
    else:
        # Fallback: simple Euclidean
        pattern = euclidean_pattern(5, 16, root=root, scale=scale, octave=octave)

    # Apply groove if specified at track level
    groove = spec.get("groove")
    if groove:
        pattern = apply_groove(pattern, groove)

    vcurve = spec.get("velocity_curve")
    if vcurve:
        pattern = apply_velocity_curve(pattern, vcurve)

    return Track(name=name, pattern=pattern, channel=channel, program=program)


def parameter_sweep(
    base_recipe: CompositionRecipe,
    parameter: str,
    values: List[object],
    output_dir: str = ".",
    naming: str = "{name}_{param}_{value}",
) -> List[str]:
    """Generate multiple variations by sweeping a single parameter.

    Args:
        base_recipe: Base recipe to modify
        parameter: Parameter name to sweep (e.g. 'bpm', 'root', 'scale')
        values: List of values to try
        output_dir: Directory for output files
        naming: Filename template with {name}, {param}, {value} placeholders

    Returns:
        List of output file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    output_files = []

    for value in values:
        recipe = _modify_recipe(base_recipe, parameter, value)
        song = recipe.generate()
        filename = naming.format(name=recipe.name, param=parameter, value=str(value))
        filepath = os.path.join(output_dir, f"{filename}.mid")
        song_to_midi(song, filepath)
        output_files.append(filepath)
        logger.info(f"Generated variation: {filepath}")

    return output_files


def euclidean_variations(
    root: str = "C",
    scale: str = "pentatonic_minor",
    bpm: int = 120,
    beat_range: Tuple[int, int] = (3, 9),
    length: int = 16,
    output_dir: str = ".",
) -> List[str]:
    """Generate a set of Euclidean rhythm variations.

    Creates one MIDI file per Euclidean rhythm E(k,n) for k in beat_range.

    Args:
        root: Root note
        scale: Scale name
        bpm: Tempo
        beat_range: (min_beats, max_beats) inclusive
        length: Pattern length
        output_dir: Output directory

    Returns:
        List of output file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    files = []

    for beats in range(beat_range[0], beat_range[1] + 1):
        pattern = euclidean_pattern(beats, length, root=root, scale=scale, octave=5)
        track = Track(name=f"E({beats},{length})", pattern=pattern, channel=0, program=81)
        song = Song(name=f"Euclidean E({beats},{length})", tracks=[track], bpm=bpm)

        filepath = os.path.join(output_dir, f"euc_{beats}_{length}.mid")
        song_to_midi(song, filepath)
        files.append(filepath)

    return files


def scale_exploration(
    root: str = "C",
    bpm: int = 120,
    length: int = 16,
    output_dir: str = ".",
) -> List[str]:
    """Generate a MIDI file for each available scale.

    Useful for exploring the tonal character of different scales.

    Args:
        root: Root note
        bpm: Tempo
        length: Pattern length
        output_dir: Output directory

    Returns:
        List of output file paths
    """
    from sequencer.scales import SCALE_INTERVALS

    os.makedirs(output_dir, exist_ok=True)
    files = []

    for scale_name in sorted(SCALE_INTERVALS.keys()):
        pattern = euclidean_pattern(5, length, root=root, scale=scale_name, octave=4)
        track = Track(name=scale_name, pattern=pattern, channel=0, program=0)
        song = Song(name=f"{root} {scale_name}", tracks=[track], bpm=bpm)

        filepath = os.path.join(output_dir, f"{root}_{scale_name}.mid")
        song_to_midi(song, filepath)
        files.append(filepath)

    return files


def progression_album(
    key: str = "C",
    bpm: int = 120,
    length_per_chord: int = 16,
    output_dir: str = ".",
) -> List[str]:
    """Generate an "album" of MIDI files, one per chord progression.

    Args:
        key: Root key
        bpm: Tempo
        length_per_chord: Steps per chord
        output_dir: Output directory

    Returns:
        List of output file paths
    """
    from sequencer.progressions import PROGRESSIONS

    os.makedirs(output_dir, exist_ok=True)
    files = []

    for prog_name in sorted(PROGRESSIONS.keys()):
        chords = build_progression(prog_name, key=key)

        lead = euclidean_pattern(5, length_per_chord, root=key, scale="major", octave=5)
        bass = bassline_from_chords(chords, length_per_chord, octave=2, pattern_type="walking")
        chords_pat = chord_pattern(chords, length_per_chord, octave=3, arpeggiate=True)
        drums = drum_pattern("four_on_floor", length_per_chord * len(chords))

        tracks = [
            Track(name="Lead", pattern=lead, channel=0, program=81),
            Track(name="Chords", pattern=chords_pat, channel=1, program=4),
            Track(name="Bass", pattern=bass, channel=2, program=34),
            Track(name="Drums", pattern=drums, channel=9),
        ]
        song = Song(name=f"{prog_name} in {key}", tracks=tracks, bpm=bpm)

        filepath = os.path.join(output_dir, f"{key}_{prog_name}.mid")
        song_to_midi(song, filepath)
        files.append(filepath)

    return files


def _modify_recipe(recipe: CompositionRecipe, parameter: str, value: object) -> CompositionRecipe:
    """Create a modified copy of a recipe with one parameter changed."""
    import copy
    new_recipe = copy.deepcopy(recipe)

    if parameter == "bpm":
        new_recipe.bpm = int(value)
    elif parameter == "root":
        new_recipe.root = str(value)
    elif parameter == "scale":
        new_recipe.scale = str(value)
    elif parameter == "groove":
        new_recipe.groove = str(value) if value else None
    elif parameter == "velocity_curve":
        new_recipe.velocity_curve = str(value) if value else None
    elif parameter.startswith("tracks["):
        # Modify a specific track parameter, e.g. "tracks[0].beats"
        import re
        match = re.match(r"tracks\[(\d+)\]\.(\w+)", parameter)
        if match:
            idx, key = int(match.group(1)), match.group(2)
            if idx < len(new_recipe.tracks):
                new_recipe.tracks[idx][key] = value
    else:
        # Try setting as attribute
        if hasattr(new_recipe, parameter):
            setattr(new_recipe, parameter, value)

    return new_recipe